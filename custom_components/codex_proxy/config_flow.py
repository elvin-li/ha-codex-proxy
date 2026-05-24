"""Config flow for the Codex Token Pool integration.

Three flows live here:

* :class:`CodexConfigFlow` — initial setup. Either fill the form
  (api_key + base_url + model) or paste an existing Codex CLI ``config.toml``
  and we'll parse it. On success we create one ``conversation`` and one
  ``ai_task_data`` subentry.
* :class:`CodexConfigFlow.async_step_reconfigure` — lets users rotate the
  API key or change the proxy base URL on an existing entry without losing
  the conversation/AI Task subentries hanging off it.
* :class:`ConversationSubentryFlowHandler` — adds or edits conversation
  subentries post-install, exposing the Codex-flavored knobs (model,
  reasoning effort, store, system prompt, attached HA LLM APIs). Multiple
  subentries let you wire several conversation agents (e.g. one with
  ``xhigh`` reasoning, one with ``medium`` for low latency).
"""
from __future__ import annotations

import logging
import tomllib
import uuid
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
from homeassistant.helpers import llm
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
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_INSTALLATION_ID,
    DEFAULT_MODEL,
    DEFAULT_PROMPT,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_STORE,
    DOMAIN,
    PROBE_INPUT,
    PROBE_MAX_OUTPUT_TOKENS,
    PROBE_TIMEOUT_S,
    REASONING_EFFORTS,
    SUBENTRY_TYPE_AI_TASK,
    SUBENTRY_TYPE_CONVERSATION,
    build_codex_headers,
)

CONF_TOML_CONFIG = "toml_config"
_FORM_FIELD_MODEL = "model"

_LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _upstream_keys() -> dict[str, str]:
    """Resolve upstream openai_conversation conf-key constants once.

    Cached at module level — these are static strings frozen by HA Core's
    release. The literal fallbacks exist purely so unit-importing this
    module without HA installed (e.g. linters) doesn't crash; in any real
    HA install the import succeeds and we use the upstream constants.
    """
    try:
        from homeassistant.components.openai_conversation.const import (
            CONF_CHAT_MODEL,
            CONF_PROMPT,
            CONF_REASONING_EFFORT,
            CONF_SERVICE_TIER,
            CONF_STORE_RESPONSES,
        )
    except ImportError:  # pragma: no cover — only triggered outside HA
        return {
            "chat_model": "chat_model",
            "prompt": "prompt",
            "reasoning_effort": "reasoning_effort",
            "store_responses": "store_responses",
            "service_tier": "service_tier",
        }
    return {
        "chat_model": CONF_CHAT_MODEL,
        "prompt": CONF_PROMPT,
        "reasoning_effort": CONF_REASONING_EFFORT,
        "store_responses": CONF_STORE_RESPONSES,
        "service_tier": CONF_SERVICE_TIER,
    }


def _parse_codex_toml(text: str) -> dict[str, Any]:
    """Pull the values we care about out of a Codex CLI ``config.toml``.

    Looks at top-level ``model``, ``model_reasoning_effort``,
    ``disable_response_storage``, and the first ``[model_providers.*]``
    table that has a ``base_url``. Returns a dict containing only keys
    that were successfully extracted.
    """
    cfg = tomllib.loads(text)
    out: dict[str, Any] = {}
    if isinstance(cfg.get("model"), str):
        out[_FORM_FIELD_MODEL] = cfg["model"].strip()
    if isinstance(cfg.get("model_reasoning_effort"), str):
        out["reasoning_effort"] = cfg["model_reasoning_effort"].strip()
    if "disable_response_storage" in cfg:
        # Codex CLI's `disable_response_storage = true` ↔ store_responses=False
        out["store_responses"] = not bool(cfg["disable_response_storage"])
    providers = cfg.get("model_providers")
    if isinstance(providers, dict):
        for provider in providers.values():
            if isinstance(provider, dict) and provider.get("base_url"):
                out[CONF_BASE_URL] = str(provider["base_url"]).rstrip("/")
                break
    return out


STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_BASE_URL, default=""): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
        vol.Optional(_FORM_FIELD_MODEL, default=DEFAULT_MODEL): str,
        vol.Optional(CONF_TOML_CONFIG, default=""): TextSelector(
            TextSelectorConfig(multiline=True)
        ),
    }
)

STEP_RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_BASE_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
    }
)


async def _async_probe_proxy(
    hass: Any,
    *,
    api_key: str,
    base_url: str,
    model: str,
    installation_id: str,
) -> str | None:
    """Hit the proxy's ``/v1/responses`` once. Return an error key or None.

    All possible return values map 1:1 to keys in ``strings.json`` so the UI
    can render localized text.
    """
    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=get_async_client(hass),
        default_headers=build_codex_headers(installation_id),
    )
    try:
        await client.with_options(timeout=PROBE_TIMEOUT_S).responses.create(
            model=model,
            input=PROBE_INPUT,
            max_output_tokens=PROBE_MAX_OUTPUT_TOKENS,
            store=False,
        )
    except openai.AuthenticationError:
        return "invalid_auth"
    except openai.NotFoundError:
        return "unknown_model"
    except openai.BadRequestError as err:
        if "model" in str(err).lower():
            return "unknown_model"
        return "unknown"
    except openai.APIConnectionError:
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Unexpected error during proxy probe")
        return "unknown"
    # Do NOT call client.close() — http_client is HA's shared httpx client;
    # closing it would tear down all HA network I/O.
    return None


class CodexConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup, plus reconfigure for an existing entry."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_SCHEMA
            )

        api_key = user_input[CONF_API_KEY]
        base_url = (user_input.get(CONF_BASE_URL) or "").strip().rstrip("/")
        model = (user_input.get(_FORM_FIELD_MODEL) or "").strip() or DEFAULT_MODEL
        reasoning_effort = DEFAULT_REASONING_EFFORT
        store_responses = DEFAULT_STORE
        errors: dict[str, str] = {}

        toml_text = (user_input.get(CONF_TOML_CONFIG) or "").strip()
        if toml_text:
            try:
                parsed = _parse_codex_toml(toml_text)
            except tomllib.TOMLDecodeError as err:
                _LOGGER.warning("Bad TOML in config flow: %s", err)
                errors["base"] = "bad_toml"
            else:
                # TOML wins for fields it provides — that's the user's intent
                # when they paste a config: "use these values."
                if CONF_BASE_URL in parsed:
                    base_url = parsed[CONF_BASE_URL]
                if _FORM_FIELD_MODEL in parsed:
                    model = parsed[_FORM_FIELD_MODEL]
                if "reasoning_effort" in parsed:
                    reasoning_effort = parsed["reasoning_effort"]
                if "store_responses" in parsed:
                    store_responses = parsed["store_responses"]

        if not errors and not base_url:
            errors[CONF_BASE_URL] = "required"

        if errors:
            return self.async_show_form(
                step_id="user",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_USER_SCHEMA, user_input
                ),
                errors=errors,
            )

        # Generate the installation id up-front so the very first /v1/responses
        # round trip carries the same fingerprint the entry will use forever
        # after. Some token-pool reverse proxies first-write the id into a
        # rate-limit table on probe; if probe and steady-state used different
        # ids the user would see a phantom limit dip on first real request.
        installation_id = str(uuid.uuid4())
        if err_key := await _async_probe_proxy(
            self.hass,
            api_key=api_key,
            base_url=base_url,
            model=model,
            installation_id=installation_id,
        ):
            return self.async_show_form(
                step_id="user",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_USER_SCHEMA, user_input
                ),
                errors={"base": err_key},
            )

        await self.async_set_unique_id(base_url)
        self._abort_if_unique_id_configured()

        common_data = _build_subentry_data(
            form={
                _upstream_keys()["chat_model"]: model,
                _upstream_keys()["reasoning_effort"]: reasoning_effort,
                _upstream_keys()["store_responses"]: store_responses,
                _upstream_keys()["prompt"]: DEFAULT_PROMPT,
            }
        )
        return self.async_create_entry(
            title=f"Codex 号池 ({base_url.split('//', 1)[-1]})",
            data={
                CONF_API_KEY: api_key,
                CONF_BASE_URL: base_url,
                CONF_INSTALLATION_ID: installation_id,
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
        """Let the user rotate the API key or move to a different proxy URL."""
        entry = self._get_reconfigure_entry()
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_RECONFIGURE_SCHEMA,
                    {
                        CONF_API_KEY: entry.data.get(CONF_API_KEY, ""),
                        CONF_BASE_URL: entry.data.get(CONF_BASE_URL, ""),
                    },
                ),
            )

        api_key = user_input[CONF_API_KEY]
        base_url = user_input[CONF_BASE_URL].strip().rstrip("/")
        installation_id = entry.data.get(
            CONF_INSTALLATION_ID, str(uuid.uuid4())
        )

        # Use any existing conversation subentry's model so we probe with a
        # model the user has actually been running, not the global default.
        probe_model = next(
            (
                sub.data.get(_upstream_keys()["chat_model"])
                for sub in entry.subentries.values()
                if sub.data.get(_upstream_keys()["chat_model"])
            ),
            DEFAULT_MODEL,
        )

        if err_key := await _async_probe_proxy(
            self.hass,
            api_key=api_key,
            base_url=base_url,
            model=probe_model,
            installation_id=installation_id,
        ):
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_RECONFIGURE_SCHEMA, user_input
                ),
                errors={"base": err_key},
            )

        return self.async_update_reload_and_abort(
            entry,
            data_updates={
                CONF_API_KEY: api_key,
                CONF_BASE_URL: base_url,
                CONF_INSTALLATION_ID: installation_id,
            },
            unique_id=base_url,
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_TYPE_CONVERSATION: ConversationSubentryFlowHandler}


class ConversationSubentryFlowHandler(ConfigSubentryFlow):
    """Add or reconfigure a conversation subentry.

    The two paths use distinct step ids so HA's flow framework routes the
    submit back to the right handler — re-using ``step_id="user"`` for both
    add and reconfigure caused HA to call ``async_step_user`` on submit even
    when ``self.source == "reconfigure"``, and ``async_create_entry`` then
    raised ``Source is reconfigure, expected user``.
    """

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=self._build_schema(None)
            )
        return self.async_create_entry(
            title="Codex 号池对话",
            data=_build_subentry_data(form=user_input),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        subentry = self._get_reconfigure_subentry()
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self._build_schema(dict(subentry.data)),
            )
        return self.async_update_and_abort(
            self._get_entry(),
            subentry,
            data=_build_subentry_data(form=user_input, base=dict(subentry.data)),
        )

    def _build_schema(self, defaults: dict[str, Any] | None) -> vol.Schema:
        keys = _upstream_keys()
        existing = defaults or {}
        entry = self._get_entry()
        coordinator = getattr(entry.runtime_data, "coordinator", None)
        model_choices = _model_select_options(
            coordinator, existing.get(keys["chat_model"])
        )
        hass_api_options = [
            SelectOptionDict(value=api.id, label=api.name)
            for api in llm.async_get_apis(self.hass)
        ]

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
                    CONF_LLM_HASS_API,
                    default=_clamp_llm_apis(
                        existing.get(CONF_LLM_HASS_API, []), hass_api_options
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=hass_api_options,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    keys["prompt"],
                    default=existing.get(keys["prompt"], DEFAULT_PROMPT),
                ): TemplateSelector(),
            }
        )


def _clamp_llm_apis(
    raw: Any, options: list[SelectOptionDict]
) -> list[str]:
    """Drop any persisted llm-api ids that are no longer registered."""
    valid = {opt["value"] for opt in options}
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [v for v in raw if v in valid]


def _build_subentry_data(
    *,
    form: dict[str, Any],
    base: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct the subentry data dict, hard-pinning ``service_tier=None``.

    Codex reverse-proxies routinely return 502 for any non-null
    ``service_tier`` value (including upstream's ``"auto"`` default). We pin
    it to ``None`` so upstream's ``options.get(CONF_SERVICE_TIER, "auto")``
    resolves to None and the SDK omits the field from the payload.

    ``form`` is the raw mapping submitted by the schema; we merge it on top
    of ``base`` (the existing subentry data, when reconfiguring) so users
    keep any upstream-only options they may have set out of band.
    """
    keys = _upstream_keys()
    out: dict[str, Any] = dict(base) if base else {}
    out.update(form)
    out[keys["service_tier"]] = None
    out.setdefault(CONF_LLM_HASS_API, [])
    return out


def _model_select_options(
    coordinator: Any, current: str | None
) -> list[SelectOptionDict]:
    """Build the model dropdown — proxy-discovered models first, current
    model always present even if the proxy hasn't seen it."""
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
