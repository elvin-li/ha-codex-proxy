"""Constants for the Codex Token Pool integration.

We deliberately depend on `homeassistant.components.openai_conversation` so that
upstream improvements (new event types, new request fields, bug fixes in the
Responses API streaming layer) flow through to this integration automatically.

Anything we override or add lives in this module; anything we re-use comes from
the upstream module via lazy imports inside the call sites.
"""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "codex_proxy"

CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_INSTALLATION_ID = "codex_installation_id"

SUBENTRY_TYPE_CONVERSATION = "conversation"
SUBENTRY_TYPE_AI_TASK = "ai_task_data"

# We deliberately do NOT ship a default base_url — every user must enter
# their own proxy address (or paste their Codex CLI config.toml).
DEFAULT_BASE_URL = ""
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_REASONING_EFFORT = "xhigh"
DEFAULT_STORE = False
DEFAULT_CONTEXT_WINDOW = 1_000_000
DEFAULT_PROMPT = ""

REASONING_EFFORTS: tuple[str, ...] = ("none", "medium", "high", "xhigh")

MODEL_REFRESH_INTERVAL = timedelta(hours=6)
PROBE_TIMEOUT_S = 10.0

DATA_COORDINATOR = "coordinator"
DATA_INSTALLATION_ID = "installation_id"

CODEX_USER_AGENT = "codex_cli_rs/0.21.0 (HomeAssistant; codex_proxy)"
CODEX_OPENAI_BETA = "responses=experimental"
CODEX_ORIGINATOR = "codex_cli_rs"
