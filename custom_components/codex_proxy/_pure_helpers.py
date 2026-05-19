"""Pure-Python helpers with no Home Assistant dependencies.

Isolated here so unit tests can import and exercise them without needing
a full HA runtime installed.
"""

from __future__ import annotations

import tomllib
from typing import Any
from urllib.parse import urlparse


def parse_codex_toml(text: str) -> dict[str, Any]:
    """Pull the values we care about out of a Codex CLI config.toml.

    Looks at top-level ``model``, ``model_reasoning_effort``,
    ``disable_response_storage``, and the first ``[model_providers.*]`` table
    that has a ``base_url``. Returns a dict with the keys we use; missing
    values are omitted.
    """
    cfg = tomllib.loads(text)
    out: dict[str, Any] = {}
    if isinstance(cfg.get("model"), str):
        out["model"] = cfg["model"].strip()
    if isinstance(cfg.get("model_reasoning_effort"), str):
        out["reasoning_effort"] = cfg["model_reasoning_effort"].strip()
    if "disable_response_storage" in cfg:
        # Codex CLI's disable_response_storage = true ↔ store_responses=False
        out["store_responses"] = not bool(cfg["disable_response_storage"])
    providers = cfg.get("model_providers")
    if isinstance(providers, dict):
        for provider in providers.values():
            if isinstance(provider, dict) and provider.get("base_url"):
                out["base_url"] = str(provider["base_url"]).strip().rstrip("/")
                break
    return out


def validate_base_url(url: str) -> str | None:
    """Return an error key if *url* is not a valid http/https base URL."""
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return "invalid_url_scheme"
    if not p.netloc:
        return "invalid_url"
    return None


def normalize_base_url(url: str) -> str:
    """Return *url* normalised to the OpenAI-compatible form (ends with ``/v1``).

    The OpenAI Python SDK treats ``base_url`` as the "OpenAI-compatible base"
    and appends path components like ``/responses``, ``/chat/completions``, and
    ``/models`` directly to it.  For OpenAI proper, ``base_url`` is
    ``https://api.openai.com/v1`` — note the trailing ``/v1``.

    Codex-style reverse proxies follow the same convention, but users
    frequently paste the bare host (``https://proxy.example.com``) into the
    config flow because the proxy's own UI shows the host without ``/v1``.
    Some lenient proxies silently accept both forms; stricter ones (e.g.
    ``tokenclub.top``) require the ``/v1`` and respond to ``/responses`` with
    the proxy's HTML landing page, producing the cryptic
    ``Last content in chat log is not an AssistantContent`` error in HA.

    This helper makes the two forms interchangeable from the user's
    perspective:

    * ``https://proxy.example.com``        → ``https://proxy.example.com/v1``
    * ``https://proxy.example.com/``       → ``https://proxy.example.com/v1``
    * ``https://proxy.example.com/v1``     → ``https://proxy.example.com/v1``
    * ``https://proxy.example.com/v1/``    → ``https://proxy.example.com/v1``
    * ``https://proxy.example.com/api/v1`` → ``https://proxy.example.com/api/v1``
      (already has ``/v1`` at the end of the path — left alone so vendor-
      specific prefixes like ``/api/v1`` continue to work)

    The caller still owns scheme/netloc validation — call ``validate_base_url``
    first.  This function does not raise; it always returns a string.
    """
    trimmed = url.rstrip("/")
    # Treat the URL as already-normalised if the last path segment is "v1".
    # Using rsplit avoids a false match on a path containing "v1" elsewhere
    # (e.g. "https://proxy.example.com/v1beta/responses" would not match).
    if trimmed.rsplit("/", 1)[-1] == "v1":
        return trimmed
    return f"{trimmed}/v1"
