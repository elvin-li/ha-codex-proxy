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

# Subentry types that carry an LLM model config (used by select + update entities)
LLM_BEARING_SUBENTRY_TYPES: tuple[str, ...] = (
    SUBENTRY_TYPE_CONVERSATION,
    SUBENTRY_TYPE_AI_TASK,
)

# We deliberately do NOT ship a default base_url — every user must enter
# their own proxy address (or paste their Codex CLI config.toml).
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_REASONING_EFFORT = "xhigh"
DEFAULT_STORE = False
DEFAULT_PROMPT = ""

REASONING_EFFORTS: tuple[str, ...] = ("none", "medium", "high", "xhigh")

MODEL_REFRESH_INTERVAL = timedelta(hours=6)
PROBE_TIMEOUT_S = 10.0
COORDINATOR_TIMEOUT_S = 15.0
COORDINATOR_MAX_RETRIES = 3
# COORDINATOR_RETRY_DELAYS must have exactly COORDINATOR_MAX_RETRIES - 1 entries:
# one sleep per inter-attempt gap (no sleep after the final attempt).
# The retry loop uses min(attempt, len-1) to index into the table, which would
# silently reuse the last delay if the two constants drift.  The assertion below
# surfaces any mismatch immediately at import time rather than hiding it.
COORDINATOR_RETRY_DELAYS: tuple[int, ...] = (5, 30)

# Enforce the invariant at import time: the retry loop in coordinator.py
# directly indexes COORDINATOR_RETRY_DELAYS by `attempt` (0 .. MAX_RETRIES-2),
# so the tuple must have exactly MAX_RETRIES-1 entries.  Any mismatch is caught
# here rather than silently producing an IndexError at runtime.
assert len(COORDINATOR_RETRY_DELAYS) == COORDINATOR_MAX_RETRIES - 1, (
    f"COORDINATOR_RETRY_DELAYS must have exactly {COORDINATOR_MAX_RETRIES - 1} "
    f"element(s) (one per inter-attempt sleep), but has {len(COORDINATOR_RETRY_DELAYS)}. "
    "Update COORDINATOR_RETRY_DELAYS or COORDINATOR_MAX_RETRIES to keep them in sync."
)

# Model IDs starting with any of these prefixes are image-only and excluded
# from the chat-model list surfaced in conversation-agent dropdowns.
IMAGE_MODEL_ID_PREFIXES: tuple[str, ...] = ("gpt-image", "dall-e", "image-")

DATA_COORDINATOR = "coordinator"

CODEX_USER_AGENT = "codex_cli_rs/0.21.0 (HomeAssistant; codex_proxy)"
CODEX_OPENAI_BETA = "responses=experimental"
CODEX_ORIGINATOR = "codex_cli_rs"
