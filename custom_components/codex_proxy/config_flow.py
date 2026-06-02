"""Config flow for the Codex Token Pool integration.

Two flows live here:

* `CodexConfigFlow` — handles initial setup. Either fill the form (api_key +
  base_url + model) or paste your existing Codex CLI `config.toml` and we'll
  parse it. Creates one `conversation` and one `ai_task_data` subentry on
  success.
* `ConversationSubentryFlowHandler` — adds or edits conversation subentries
  post-install, exposing the Codex-flavored knobs (model, reasoning effort,
  store, system prompt). Multiple subentries let you wire several conversation
  agents (e.g. one with `xhigh` reasoning, one with `medium` for low latency).
"""

from __future__ import annotations

import logging
import tomllib
from functools import lru_cache
from typing import Any

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
from homeassistant.core import callback
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
# Upstream key resolution (cached — import only happens once per process)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _upstream_keys() -> dict[str, str]:
    """Late-import upstream conf keys, with literal fallbacks.

    Cached so the import cost is paid only once per HA process lifetime.
    """
    try:
        from homeassistant.components.openai_conversation.const import (  # noqa: WPS433
            CONF_CHAT_MODEL,
            CONF_PROMPT,
            CONF_REASONING_EFFORT,
            CONF_SERVICE_TIER,
            CONF_STORE_RESPONSES,
        )

        return {
            "chat_model": CONF_CHAT_MODEL,
            "prompt": CONF_PROMPT,
            "reasoning_effort": CONF_REASONING_EFFORT,
            "store_responses": CONF_STORE_RESPONSES,
            "service_tier": CONF_SERVICE_TIER,
        }
    except ImportError:  # pragma: no cover
        return {
            "chat_model": "chat_model",
            "prompt": "prompt",
            "reasoning_effort": "reasoning_effort",
            "store_responses": "store_responses",
            "service_tier": "service_tier",
        }


# ---------------------------------------------------------------------------
# TOML parser for Codex CLI config
# ---------------------------------------------------------------------------


def _parse_codex_toml(text: str) -> dict[str, Any]:
    """Pull the values we care about out of a Codex CLI config.toml.

    Looks at top-level `model`, `model_reasoning_effort`,
    `disable_response_storage`, and the first `[model_providers.*]` table that
    has a `base_url`. Returns a dict with the keys we use; missing values are
    omitted.
    """
    cfg = tomllib.loads(text)
    out: dict[str, Any] = {}

    if isinstance(cfg.get("model"), str):
        out["model"] = cfg["model"].strip()

    if isinstance(cfg.get("model_reasoning_effort"), str):
        out["reasoning_effort"] = cfg["model_reasoning_effort"].strip()

    if "disable_response_storage" in cfg:
        # Codex CLI's `disable_response_storage = true` ↔ store_responses=False
        out["store_responses"] = not bool(cfg["disable_response_storage"])

    providers = cfg.get("model_providers")
    if isinstance(providers, dict):
        for provider in providers.values():
            if isinstance(provider, dict) and provider.get("base_url"):
                out["base_url"] = str(provider["base_url"]).rstrip("/")
                break

    return out


# ---------------------------------------------------------------------------
# Schema
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


# ---------------------------------------------------------------------------
# Main config flow
# ---------------------------------------------------------------------------


class CodexConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_SCHEMA
            )

        errors: dict[str, str] = {}

        api_key = user_input[CONF_API_KEY]
        base_url = (user_input.get(CONF_BASE_URL) or "").strip().rstrip("/")
        model = (user_input.get("model") or "").strip() or DEFAULT_MODEL
        reasoning_effort = DEFAULT_REASONING_EFFORT
        store_responses = DEFAULT_STORE

        # --- Parse optional TOML ---
        toml_text = (user_input.get(CONF_TOML_CONFIG) or "").strip()
        if toml_text:
            try:
                parsed = _parse_codex_toml(toml_text)
            except tomllib.TOMLDecodeError as err:
                _LOGGER.debug("Bad TOML in config flow: %s", err)
                errors["base"] = "bad_toml"
            else:
                # TOML wins for fields it provides
                base_url = parsed.get("base_url", base_url)
                model = parsed.get("model", model)
                reasoning_effort = parsed.get("reasoning_effort", reasoning_effort)
                store_responses = parsed.get("store_responses", store_responses)

        # --- Validate required fields ---
        if not errors and not base_url:
            errors[CONF_BASE_URL] = "required"

        if errors:
            return self._show_form_with_errors(user_input, errors)

        # --- Probe the proxy ---
        errors = await self._probe_proxy(api_key, base_url, model)
        if errors:
            return self._show_form_with_errors(user_input, errors)

        # --- Create entry ---
        await self.async_set_unique_id(base_url)
        self._abort_if_unique_id_configured()

        return self._create_config_entry(
            api_key=api_key,
            base_url=base_url,
            model=model,
            reasoning_effort=reasoning_effort,
            store_responses=store_responses,
        )

    # --- Helpers ---

    def _show_form_with_errors(
        self, user_input: dict[str, Any], errors: dict[str, str]
    ) -> ConfigFlowResult:
        """Re-display the form preserving user input."""
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def _probe_proxy(
        self, api_key: str, base_url: str, model: str
    ) -> dict[str, str]:
        """Send a lightweight /v1/responses call to verify connectivity.

        Returns an errors dict (empty on success).
        """
        errors: dict[str, str] = {}
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=get_async_client(self.hass),
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
        except openai.NotFoundError:
            errors["base"] = "unknown_model"
        except openai.BadRequestError as err:
            if "model" in str(err).lower():
                errors["base"] = "unknown_model"
            else:
                _LOGGER.debug("Proxy returned BadRequest: %s", err)
                errors["base"] = "unknown"
        except openai.APIConnectionError:
            errors["base"] = "cannot_connect"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error during proxy probe")
            errors["base"] = "unknown"
        # Do NOT close the client — http_client is HA's shared httpx client.
        return errors

    def _create_config_entry(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        reasoning_effort: str,
        store_responses: bool,
    ) -> ConfigFlowResult:
        """Build the config entry with default subentries."""
        keys = _upstream_keys()

        # Codex reverse-proxies routinely return 502 for any non-null
        # `service_tier` value. Pin to None so upstream omits the field.
        common_data: dict[str, Any] = {
            keys["chat_model"]: model,
            keys["prompt"]: DEFAULT_PROMPT,
            keys["reasoning_effort"]: reasoning_effort,
            keys["store_responses"]: store_responses,
            keys["service_tier"]: None,
            CONF_LLM_HASS_API: [],
        }

        title = f"Codex 号池 ({base_url.split('//', 1)[-1]})"

        return self.async_create_entry(
            title=title,
            data={
                CONF_API_KEY: api_key,
                CONF_BASE_URL: base_url,
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

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Expose conversation subentry type for post-install additions."""
        return {SUBENTRY_TYPE_CONVERSATION: ConversationSubentryFlowHandler}


# ---------------------------------------------------------------------------
# Conversation subentry flow
# ---------------------------------------------------------------------------


class ConversationSubentryFlowHandler(ConfigSubentryFlow):
    """Add or reconfigure a conversation subentry.

    The two paths use distinct step ids so HA's flow framework routes the
    submit back to the right handler — re-using `step_id="user"` for both
    add and reconfigure caused HA to call `async_step_user` on submit even
    when `self.source == "reconfigure"`, and `async_create_entry` then
    raised `Source is reconfigure, expected user`.
    """

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle adding a new conversation subentry."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=self._build_schema(None)
            )
        return self.async_create_entry(
            title="Codex 号池对话", data=_enrich_subentry_data(user_input)
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle reconfiguring an existing conversation subentry."""
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
        """Build the voluptuous schema for the subentry form."""
        keys = _upstream_keys()
        existing = defaults or {}
        entry = self._get_entry()

        coordinator = (
            self.hass.data.get(DOMAIN, {})
            .get(entry.entry_id, {})
            .get(DATA_COORDINATOR)
        )
        model_choices = _model_select_options(
            coordinator, existing.get(keys["chat_model"])
        )

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
                    default=existing.get(
                        keys["reasoning_effort"], DEFAULT_REASONING_EFFORT
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=v, label=v)
                            for v in REASONING_EFFORTS
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    keys["store_responses"],
                    default=bool(
                        existing.get(keys["store_responses"], DEFAULT_STORE)
                    ),
                ): BooleanSelector(),
                vol.Optional(
                    keys["prompt"],
                    default=existing.get(keys["prompt"], DEFAULT_PROMPT),
                ): TemplateSelector(),
            }
        )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _enrich_subentry_data(
    user_input: dict[str, Any], base: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Merge form input with the keys upstream needs but our form doesn't expose.

    Critically pins `service_tier=None` so the proxy doesn't 502 on the
    upstream default of "auto".
    """
    keys = _upstream_keys()
    out: dict[str, Any] = dict(base) if base else {}
    out.update(user_input)
    out[keys["service_tier"]] = None
    out.setdefault(CONF_LLM_HASS_API, [])
    return out


def _model_select_options(
    coordinator: Any, current: str | None
) -> list[SelectOptionDict]:
    """Build the model dropdown.

    Proxy-discovered models come first; the current model is always present
    even if the proxy hasn't advertised it yet.
    """
    seen: set[str] = set()
    out: list[SelectOptionDict] = []

    if coordinator is not None:
        for m in coordinator.chat_models:
            mid: str = m["id"]
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
