"""Config flow for the Codex Token Pool integration.

Three flows live here:

* `CodexConfigFlow` — handles initial setup. Either fill the form (api_key +
  base_url + model) or paste your existing Codex CLI `config.toml` and we'll
  parse it. Creates one `conversation` and one `ai_task_data` subentry on
  success.
* `ConversationSubentryFlowHandler` — adds or edits conversation subentries
  post-install, exposing the Codex-flavored knobs (model, reasoning effort,
  store, system prompt). Multiple subentries let you wire several conversation
  agents (e.g. one with `xhigh` reasoning, one with `medium` for low latency).
* `AITaskSubentryFlowHandler` — same knobs as conversation but for AI Task
  data-generation / image-generation subentries.
"""

from __future__ import annotations

import logging
import tomllib
from typing import Any, NamedTuple

import openai
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from ._pure_helpers import parse_codex_toml as _parse_codex_toml_impl
from ._pure_helpers import validate_base_url as _validate_base_url_impl
from .const import (
    CODEX_OPENAI_BETA,
    CODEX_ORIGINATOR,
    CODEX_USER_AGENT,
    CONF_API_KEY,
    CONF_BASE_URL,
    DATA_COORDINATOR,
    DEFAULT_MODEL,
    DEFAULT_PROMPT,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_STORE,
    DOMAIN,
    PROBE_TIMEOUT_S,
    REASONING_EFFORTS,
    SUBENTRY_TYPE_AI_TASK,
    SUBENTRY_TYPE_CONVERSATION,
)

CONF_TOML_CONFIG = "toml_config"

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cached upstream key imports
# ---------------------------------------------------------------------------

_UPSTREAM_KEYS_CACHE: dict[str, str] | None = None


def _upstream_keys() -> dict[str, str]:
    """Late-import upstream conf keys, with literal fallbacks.

    Result is cached at module level — the upstream const module never changes
    within a HA session, so repeated dynamic imports are unnecessary.
    """
    global _UPSTREAM_KEYS_CACHE
    if _UPSTREAM_KEYS_CACHE is not None:
        return _UPSTREAM_KEYS_CACHE
    try:
        from homeassistant.components.openai_conversation.const import (
            CONF_CHAT_MODEL,
            CONF_PROMPT,
            CONF_REASONING_EFFORT,
            CONF_SERVICE_TIER,
            CONF_STORE_RESPONSES,
        )

        _UPSTREAM_KEYS_CACHE = {
            "chat_model": CONF_CHAT_MODEL,
            "prompt": CONF_PROMPT,
            "reasoning_effort": CONF_REASONING_EFFORT,
            "store_responses": CONF_STORE_RESPONSES,
            "service_tier": CONF_SERVICE_TIER,
        }
    except ImportError:  # pragma: no cover
        _UPSTREAM_KEYS_CACHE = {
            "chat_model": "chat_model",
            "prompt": "prompt",
            "reasoning_effort": "reasoning_effort",
            "store_responses": "store_responses",
            "service_tier": "service_tier",
        }
    return _UPSTREAM_KEYS_CACHE


# ---------------------------------------------------------------------------
# Pure-Python wrappers (implementations live in _pure_helpers.py so tests
# can import and exercise them without the HA runtime)
# ---------------------------------------------------------------------------


def _parse_codex_toml(text: str) -> dict[str, Any]:
    """Pull the values we care about out of a Codex CLI config.toml."""
    return _parse_codex_toml_impl(text)


def _validate_base_url(url: str) -> str | None:
    """Return an error key if *url* is not a valid http/https base URL."""
    return _validate_base_url_impl(url)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_BASE_URL, default=""): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
        vol.Optional("model", default=DEFAULT_MODEL): str,
        vol.Optional(CONF_TOML_CONFIG, default=""): TextSelector(
            TextSelectorConfig(multiline=True)
        ),
    }
)


async def _probe_proxy(
    hass: HomeAssistant,
    api_key: str,
    base_url: str,
    model: str,
) -> dict[str, str]:
    """Send a minimal request to the proxy and return an errors dict.

    Returns an empty dict on success, or a dict with a ``"base"`` error key
    matching one of the ``config.error.*`` strings defined in strings.json.

    Do NOT call ``client.close()`` after the probe — the http_client is HA's
    shared httpx client; closing it would tear down all HA network I/O.
    """
    _LOGGER.debug("Probing proxy at %s with model %s", base_url, model)
    errors: dict[str, str] = {}
    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=get_async_client(hass),
        default_headers={
            "User-Agent": CODEX_USER_AGENT,
            "OpenAI-Beta": CODEX_OPENAI_BETA,
            "originator": CODEX_ORIGINATOR,
        },
    )
    try:
        await client.with_options(timeout=PROBE_TIMEOUT_S).responses.create(
            model=model,
            input="ping",
            max_output_tokens=16,
            store=False,
        )
    except openai.AuthenticationError:
        errors["base"] = "invalid_auth"
    except openai.PermissionDeniedError:
        errors["base"] = "invalid_auth"
    except openai.NotFoundError:
        errors["base"] = "unknown_model"
    except openai.BadRequestError as err:
        errors["base"] = "unknown_model" if "model" in str(err).lower() else "unknown"
    except openai.UnprocessableEntityError as err:
        errors["base"] = "unknown_model" if "model" in str(err).lower() else "unknown"
    except openai.RateLimitError:
        errors["base"] = "rate_limited"
    except openai.InternalServerError:
        errors["base"] = "cannot_connect"
    except openai.APIConnectionError:
        errors["base"] = "cannot_connect"
    except (TimeoutError, OSError) as err:
        _LOGGER.warning("Unexpected error during proxy probe: %s", err)
        errors["base"] = "cannot_connect"
    return errors


def _enrich_subentry_data(
    user_input: dict[str, Any], base: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Merge form input with the keys upstream needs but our form doesn't
    expose. Critically pins ``service_tier=None`` so the proxy doesn't 502
    on the upstream default of "auto"."""
    keys = _upstream_keys()
    out: dict[str, Any] = dict(base) if base else {}
    out.update(user_input)
    out[keys["service_tier"]] = None
    out.setdefault(CONF_LLM_HASS_API, [])
    return out


def _model_select_options(coordinator: Any, current: str | None) -> list[SelectOptionDict]:
    """Build the model dropdown — proxy-discovered models first, current model
    always present even if the proxy hasn't seen it."""
    seen: set[str] = set()
    out: list[SelectOptionDict] = []

    if coordinator is not None:
        for m in coordinator.chat_models:
            mid = m["id"]
            if mid in seen:
                continue
            seen.add(mid)
            label = m.get("display_name") or mid
            out.append(SelectOptionDict(value=mid, label=label))

    if current and current not in seen:
        out.insert(0, SelectOptionDict(value=current, label=current))

    if not out:
        out.append(SelectOptionDict(value=DEFAULT_MODEL, label=DEFAULT_MODEL))

    return out


# ---------------------------------------------------------------------------
# Main config flow
# ---------------------------------------------------------------------------


class CodexConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup flow for creating a new Codex Token Pool config entry.

    Handles the top-level integration setup (API key + proxy URL).  After a
    successful setup it creates two default subentries — one for conversation
    agents and one for AI Task data generation — so the integration is
    immediately usable with the Home Assistant Assist pipeline.

    To modify credentials after initial setup use the ``reconfigure`` step
    (:meth:`async_step_reconfigure`), which updates the connection without
    destroying any subentries the user may have customised.
    """

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial 'add integration' step.

        Two phases:

        1. **Show form** — when ``user_input`` is ``None`` (HA's first call),
           returns the user-facing form with fields for API key, proxy URL,
           optional default model, and an optional paste-your-``config.toml``
           shortcut.

        2. **Process submit** — when ``user_input`` is provided:
           a. TOML is parsed and merged (if pasted) via :func:`_parse_toml_and_validate`.
           b. A live probe request is sent to the proxy via :func:`_probe_proxy`
              to validate the credentials before storing them.
           c. On success the config entry is created with two default subentries
              (``conversation`` and ``ai_task_data``), each pre-populated with
              ``service_tier=None`` to prevent proxy 502 errors.

        Any validation or probe error re-displays the form with an inline
        error message.
        """
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA)

        parsed = _parse_toml_and_validate(user_input)
        if parsed.errors:
            return self.async_show_form(
                step_id="user",
                data_schema=self.add_suggested_values_to_schema(STEP_USER_SCHEMA, user_input),
                errors=parsed.errors,
            )

        probe_errors = await _probe_proxy(self.hass, parsed.api_key, parsed.base_url, parsed.model)
        if probe_errors:
            return self.async_show_form(
                step_id="user",
                data_schema=self.add_suggested_values_to_schema(STEP_USER_SCHEMA, user_input),
                errors=probe_errors,
            )

        await self.async_set_unique_id(parsed.base_url)
        self._abort_if_unique_id_configured()

        keys = _upstream_keys()
        # Build initial subentry data via the shared helper so service_tier=None
        # and llm_hass_api=[] are applied centrally — the same way the subentry
        # reconfigure flow applies them.  Codex reverse-proxies routinely return
        # 502 for any non-null service_tier value.
        common_data = _enrich_subentry_data(
            {
                keys["chat_model"]: parsed.model,
                keys["prompt"]: DEFAULT_PROMPT,
                keys["reasoning_effort"]: parsed.reasoning_effort,
                keys["store_responses"]: parsed.store_responses,
            }
        )
        return self.async_create_entry(
            title=f"Codex 号池 ({parsed.base_url.split('//', 1)[-1]})",
            data={
                CONF_API_KEY: parsed.api_key,
                CONF_BASE_URL: parsed.base_url,
            },
            subentries=[
                {
                    "subentry_type": SUBENTRY_TYPE_CONVERSATION,
                    "title": "Codex 号池对话",
                    "unique_id": None,
                    "data": dict(common_data),
                },
                {
                    "subentry_type": SUBENTRY_TYPE_AI_TASK,
                    "title": "Codex 号池 AI Task",
                    "unique_id": None,
                    "data": dict(common_data),
                },
            ],
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow changing the API key or proxy URL without losing subentries."""
        entry = self._get_reconfigure_entry()
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_USER_SCHEMA,
                    {
                        CONF_API_KEY: entry.data.get(CONF_API_KEY, ""),
                        CONF_BASE_URL: entry.data.get(CONF_BASE_URL, ""),
                    },
                ),
            )

        # Only api_key and base_url are updated by reconfigure; reasoning_effort
        # and store_responses from TOML are intentionally ignored here — LLM
        # settings are managed per-subentry via the subentry reconfigure flow.
        parsed = _parse_toml_and_validate(user_input)
        if parsed.errors:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self.add_suggested_values_to_schema(STEP_USER_SCHEMA, user_input),
                errors=parsed.errors,
            )

        probe_errors = await _probe_proxy(self.hass, parsed.api_key, parsed.base_url, parsed.model)
        if probe_errors:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self.add_suggested_values_to_schema(STEP_USER_SCHEMA, user_input),
                errors=probe_errors,
            )

        await self.async_set_unique_id(parsed.base_url)
        self._abort_if_unique_id_mismatch()
        return self.async_update_reload_and_abort(
            entry,
            # Merge with existing data to preserve CONF_INSTALLATION_ID and any
            # future fields that may have been added since initial setup.
            data={**entry.data, CONF_API_KEY: parsed.api_key, CONF_BASE_URL: parsed.base_url},
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {
            SUBENTRY_TYPE_CONVERSATION: ConversationSubentryFlowHandler,
            SUBENTRY_TYPE_AI_TASK: AITaskSubentryFlowHandler,
        }


# ---------------------------------------------------------------------------
# Subentry flows
# ---------------------------------------------------------------------------


class _LLMSubentryFlowHandlerBase(ConfigSubentryFlow):
    """Shared logic for conversation and AI-task subentry flows.

    Subclasses override ``_default_title`` and set ``_subentry_type`` so the
    two concrete handlers are just one-liner declarations.
    """

    _default_title: str = "Codex 号池代理"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle the 'add new subentry' step.

        Shows the model-and-settings form on the first call (``user_input``
        is ``None``); creates a new subentry on submit.  The submitted data is
        passed through :func:`_enrich_subentry_data` to pin ``service_tier``
        and ``llm_hass_api`` before storage.
        """
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=self._build_schema(None))
        return self.async_create_entry(
            title=self._default_title,
            data=_enrich_subentry_data(user_input),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle the 'edit existing subentry' step.

        Pre-fills the form with the current subentry data on the first call
        (``user_input`` is ``None``); merges changes into the existing data on
        submit, preserving any fields not exposed in the form (e.g. future
        keys added after initial setup).  The merged dict is passed through
        :func:`_enrich_subentry_data` to re-pin ``service_tier`` and
        ``llm_hass_api``.
        """
        subentry = self._get_reconfigure_subentry()
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self._build_schema(dict(subentry.data)),
            )
        return self.async_update_and_abort(
            self._get_entry(),
            subentry,
            data=_enrich_subentry_data(user_input, base=dict(subentry.data)),
        )

    def _build_schema(self, defaults: dict[str, Any] | None) -> vol.Schema:
        """Build the voluptuous schema for the LLM-settings form.

        Fetches available models from the coordinator (if already running) to
        populate the model dropdown with live choices.  ``defaults`` is
        ``None`` for a fresh *add* flow or a snapshot of the existing subentry
        data for a *reconfigure* flow; either way the current selection is
        preserved as the pre-selected dropdown value.
        """
        keys = _upstream_keys()
        existing = defaults or {}
        entry = self._get_entry()
        coordinator = self.hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get(DATA_COORDINATOR)
        model_choices = _model_select_options(coordinator, existing.get(keys["chat_model"]))

        return vol.Schema(
            {
                vol.Required(
                    keys["chat_model"],
                    default=existing.get(keys["chat_model"], DEFAULT_MODEL),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=model_choices,
                        custom_value=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    keys["reasoning_effort"],
                    default=existing.get(keys["reasoning_effort"], DEFAULT_REASONING_EFFORT),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[SelectOptionDict(value=v, label=v) for v in REASONING_EFFORTS],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    keys["store_responses"],
                    default=bool(existing.get(keys["store_responses"], DEFAULT_STORE)),
                ): BooleanSelector(),
                vol.Optional(
                    keys["prompt"],
                    default=existing.get(keys["prompt"], DEFAULT_PROMPT),
                ): TemplateSelector(),
            }
        )


class ConversationSubentryFlowHandler(_LLMSubentryFlowHandlerBase):
    """Add or reconfigure a conversation subentry.

    The two paths use distinct step ids so HA's flow framework routes the
    submit back to the right handler — re-using ``step_id="user"`` for both
    add and reconfigure caused HA to call ``async_step_user`` on submit even
    when ``self.source == "reconfigure"``, raising ``Source is reconfigure,
    expected user``.
    """

    _default_title = "Codex 号池对话"


class AITaskSubentryFlowHandler(_LLMSubentryFlowHandlerBase):
    """Add or reconfigure an AI Task data-generation subentry."""

    _default_title = "Codex 号池 AI Task"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


class _ParseResult(NamedTuple):
    """Structured result from :func:`_parse_toml_and_validate`.

    Using a ``NamedTuple`` instead of a bare 6-tuple makes the return value
    self-documenting and allows future callers to use named field access
    (``result.api_key``) instead of memorising positional indices.  Existing
    callers that use positional unpacking continue to work unchanged because
    ``NamedTuple`` is a subclass of ``tuple``.
    """

    errors: dict[str, str]
    api_key: str
    base_url: str
    model: str
    reasoning_effort: str
    store_responses: bool


def _parse_toml_and_validate(
    user_input: dict[str, Any],
) -> _ParseResult:
    """Extract, TOML-merge, and validate fields from form input.

    Returns a :class:`_ParseResult`.  If ``errors`` is non-empty the caller
    should re-show the form without attempting a probe.  All string fields are
    stripped of leading/trailing whitespace before validation so that a user
    who accidentally pastes their API key or URL with surrounding spaces does
    not receive a misleading authentication or URL-scheme error.
    """
    errors: dict[str, str] = {}
    # Strip api_key so a pasted key with surrounding whitespace doesn't produce
    # a cryptic "invalid_auth" error — the same defensive stripping applied to
    # base_url and model below.
    api_key: str = (user_input.get(CONF_API_KEY) or "").strip()
    base_url: str = (user_input.get(CONF_BASE_URL) or "").strip().rstrip("/")
    model: str = (user_input.get("model") or "").strip() or DEFAULT_MODEL
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    store_responses: bool = DEFAULT_STORE

    toml_text = (user_input.get(CONF_TOML_CONFIG) or "").strip()
    if toml_text:
        try:
            parsed = _parse_codex_toml(toml_text)
        except tomllib.TOMLDecodeError as err:
            _LOGGER.warning("Bad TOML in config flow: %s", err)
            errors["base"] = "bad_toml"
        else:
            if "base_url" in parsed:
                base_url = parsed["base_url"]
            if "model" in parsed:
                model = parsed["model"]
            if "reasoning_effort" in parsed:
                if parsed["reasoning_effort"] in REASONING_EFFORTS:
                    reasoning_effort = parsed["reasoning_effort"]
                else:
                    _LOGGER.warning(
                        "TOML model_reasoning_effort '%s' is not a valid value "
                        "(%s); using default '%s'",
                        parsed["reasoning_effort"],
                        ", ".join(REASONING_EFFORTS),
                        DEFAULT_REASONING_EFFORT,
                    )
            if "store_responses" in parsed:
                store_responses = parsed["store_responses"]
            if not base_url:
                errors["base"] = "toml_no_base_url"

    if not errors and not base_url:
        errors[CONF_BASE_URL] = "required"

    if not errors:
        url_err = _validate_base_url(base_url)
        if url_err:
            errors[CONF_BASE_URL] = url_err

    return _ParseResult(
        errors=errors,
        api_key=api_key,
        base_url=base_url,
        model=model,
        reasoning_effort=reasoning_effort,
        store_responses=store_responses,
    )
