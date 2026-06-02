"""Constants for the Codex Token Pool integration.

We deliberately depend on `homeassistant.components.openai_conversation` so that
upstream improvements (new event types, new request fields, bug fixes in the
Responses API streaming layer) flow through to this integration automatically.

Anything we override or add lives in this module; anything we re-use comes from
the upstream module via lazy imports inside the call sites.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Final

# ---------------------------------------------------------------------------
# Integration identity
# ---------------------------------------------------------------------------

DOMAIN: Final = "codex_proxy"

# ---------------------------------------------------------------------------
# Config entry data keys
# ---------------------------------------------------------------------------

CONF_API_KEY: Final = "api_key"
CONF_BASE_URL: Final = "base_url"
CONF_INSTALLATION_ID: Final = "codex_installation_id"

# ---------------------------------------------------------------------------
# Subentry types
# ---------------------------------------------------------------------------

SUBENTRY_TYPE_CONVERSATION: Final = "conversation"
SUBENTRY_TYPE_AI_TASK: Final = "ai_task_data"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# We deliberately do NOT ship a default base_url — every user must enter
# their own proxy address (or paste their Codex CLI config.toml).
DEFAULT_BASE_URL: Final = ""
DEFAULT_MODEL: Final = "gpt-5.5"
DEFAULT_REASONING_EFFORT: Final = "xhigh"
DEFAULT_STORE: Final = False
DEFAULT_CONTEXT_WINDOW: Final = 1_000_000
DEFAULT_PROMPT: Final = ""

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

REASONING_EFFORTS: Final[tuple[str, ...]] = ("none", "medium", "high", "xhigh")

# ---------------------------------------------------------------------------
# Timing / network
# ---------------------------------------------------------------------------

MODEL_REFRESH_INTERVAL: Final = timedelta(hours=6)
PROBE_TIMEOUT_S: Final[float] = 10.0
MODELS_FETCH_TIMEOUT_S: Final[float] = 15.0

# ---------------------------------------------------------------------------
# Runtime data keys (stored in hass.data[DOMAIN][entry_id])
# ---------------------------------------------------------------------------

DATA_COORDINATOR: Final = "coordinator"
DATA_INSTALLATION_ID: Final = "installation_id"

# ---------------------------------------------------------------------------
# Codex-CLI–flavored HTTP headers
#
# Token-pool reverse proxies routinely gate on these headers to distinguish
# Codex traffic from generic OpenAI SDK traffic.
# ---------------------------------------------------------------------------

CODEX_USER_AGENT: Final = "codex_cli_rs/0.21.0 (HomeAssistant; codex_proxy)"
CODEX_OPENAI_BETA: Final = "responses=experimental"
CODEX_ORIGINATOR: Final = "codex_cli_rs"
