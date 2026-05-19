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
