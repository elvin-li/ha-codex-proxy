"""Constants and small shared helpers for the Codex Token Pool integration.

We deliberately depend on `homeassistant.components.openai_conversation` so that
upstream improvements (new event types, new request fields, bug fixes in the
Responses API streaming layer) flow through to this integration automatically.

Anything we override or add lives in this module; anything we re-use comes from
the upstream module via lazy imports inside the call sites.
"""
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers import device_registry as dr

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry

DOMAIN = "codex_proxy"

CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_INSTALLATION_ID = "codex_installation_id"

SUBENTRY_TYPE_CONVERSATION = "conversation"
SUBENTRY_TYPE_AI_TASK = "ai_task_data"
# Subentry types that carry an LLM model selection (and therefore deserve
# their own update entity tracking the latest proxy-advertised model).
LLM_BEARING_SUBENTRY_TYPES: tuple[str, ...] = (
    SUBENTRY_TYPE_CONVERSATION,
    SUBENTRY_TYPE_AI_TASK,
)

# We deliberately do NOT ship a default base_url — every user must enter
# their own proxy address (or paste their Codex CLI config.toml).
DEFAULT_BASE_URL = ""
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_REASONING_EFFORT = "xhigh"
DEFAULT_STORE = False
DEFAULT_PROMPT = ""

REASONING_EFFORTS: tuple[str, ...] = ("none", "medium", "high", "xhigh")

# Model-id prefixes that are not chat models. Used to filter the dropdown
# offered to users and the "latest model" computation in the update entity.
NON_CHAT_MODEL_PREFIXES: tuple[str, ...] = (
    "gpt-image",
    "dall-e",
    "whisper",
    "tts",
    "text-embedding",
    "omni-moderation",
    "moderation",
)

MODEL_REFRESH_INTERVAL = timedelta(hours=6)
MODEL_REFRESH_TIMEOUT_S = 15.0
PROBE_TIMEOUT_S = 10.0
PROBE_INPUT = "ping"
PROBE_MAX_OUTPUT_TOKENS = 16

CODEX_USER_AGENT = "codex_cli_rs/0.21.0 (HomeAssistant; codex_proxy)"
CODEX_OPENAI_BETA = "responses=experimental"
CODEX_ORIGINATOR = "codex_cli_rs"

BRAND_MANUFACTURER = "OpenAI Codex Token Pool"


def build_codex_headers(
    installation_id: str | None = None,
    *,
    api_key: str | None = None,
) -> dict[str, str]:
    """Build the HTTP headers that mimic a real Codex CLI request.

    Token-pool reverse proxies routinely gate on these headers to distinguish
    Codex traffic from generic OpenAI SDK traffic. Sending them defensively
    costs nothing if the proxy doesn't check them.

    Pass ``api_key`` only when the caller is hand-rolling the request via raw
    httpx (the openai SDK injects its own ``Authorization`` header). Pass
    ``installation_id`` whenever it is known; during the very first config-flow
    probe we may not have one yet, in which case we omit the header rather
    than send a placeholder.
    """
    headers: dict[str, str] = {
        "User-Agent": CODEX_USER_AGENT,
        "OpenAI-Beta": CODEX_OPENAI_BETA,
        "originator": CODEX_ORIGINATOR,
    }
    if installation_id:
        headers["x-codex-installation-id"] = installation_id
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers.setdefault("Accept", "application/json")
    return headers


def build_codex_device_info(
    subentry: "ConfigSubentry", *, model: str | None = None
) -> dr.DeviceInfo:
    """Build the DeviceInfo block that anchors entities under our DOMAIN.

    ``model`` is the chat-model id currently bound to the subentry; pass
    ``None`` for entities whose device row should reuse the existing device
    record without owning the displayed model attribute (e.g. the update
    entity, which only references the device).
    """
    info = dr.DeviceInfo(
        identifiers={(DOMAIN, subentry.subentry_id)},
        name=subentry.title,
        manufacturer=BRAND_MANUFACTURER,
        entry_type=dr.DeviceEntryType.SERVICE,
    )
    if model:
        info["model"] = model
    return info


def is_chat_model(model: dict[str, Any] | str) -> bool:
    """Heuristic: return True when a /v1/models entry looks like a chat model.

    Accepts either the raw model id or the dict shape stored by the
    coordinator. Filters by id-prefix blacklist rather than whitelist so newly
    released chat-capable model families show up automatically.
    """
    mid = model if isinstance(model, str) else str(model.get("id") or "")
    if not mid:
        return False
    return not any(mid.startswith(p) for p in NON_CHAT_MODEL_PREFIXES)
