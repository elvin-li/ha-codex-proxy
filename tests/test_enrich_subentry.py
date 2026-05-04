"""Tests for _enrich_subentry_data in config_flow.py.

Exercises that service_tier=None is always pinned, llm_hass_api defaults to
[]), and that an existing base dict is preserved but overridden by new
user_input values.
"""
from __future__ import annotations

import sys
import os
import types
from typing import Any
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Bootstrap HA stubs before any codex_proxy import.
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

_HA_MODULES = [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.openai_conversation",
    "homeassistant.components.openai_conversation.const",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.selector",
    "homeassistant.helpers.httpx_client",
    "homeassistant.helpers.update_coordinator",
]
for _mod in _HA_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Patch upstream const keys used by _enrich_subentry_data / _upstream_keys().
sys.modules[
    "homeassistant.components.openai_conversation.const"
].CONF_CHAT_MODEL = "chat_model"
sys.modules[
    "homeassistant.components.openai_conversation.const"
].CONF_PROMPT = "prompt"
sys.modules[
    "homeassistant.components.openai_conversation.const"
].CONF_REASONING_EFFORT = "reasoning_effort"
sys.modules[
    "homeassistant.components.openai_conversation.const"
].CONF_STORE_RESPONSES = "store_responses"
sys.modules[
    "homeassistant.components.openai_conversation.const"
].CONF_SERVICE_TIER = "service_tier"
sys.modules["homeassistant.const"].CONF_LLM_HASS_API = "llm_hass_api"

# Stub openai and voluptuous so config_flow can be imported.
for _mod in ["openai", "voluptuous"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Reset upstream key cache in case another test module already set it.
import importlib
if "custom_components.codex_proxy.config_flow" in sys.modules:
    sys.modules["custom_components.codex_proxy.config_flow"]._UPSTREAM_KEYS_CACHE = None

from custom_components.codex_proxy.config_flow import _enrich_subentry_data  # noqa: E402


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEnrichSubentryData:
    def test_service_tier_always_none(self) -> None:
        result = _enrich_subentry_data({"chat_model": "gpt-5.5"})
        assert result["service_tier"] is None

    def test_service_tier_overrides_caller_supplied_value(self) -> None:
        result = _enrich_subentry_data({"service_tier": "flex"})
        assert result["service_tier"] is None

    def test_llm_hass_api_defaults_to_empty_list(self) -> None:
        result = _enrich_subentry_data({"chat_model": "gpt-5.5"})
        assert result["llm_hass_api"] == []

    def test_existing_llm_hass_api_preserved(self) -> None:
        result = _enrich_subentry_data({"llm_hass_api": ["assist"]})
        assert result["llm_hass_api"] == ["assist"]

    def test_user_input_merged_into_base(self) -> None:
        base = {"chat_model": "gpt-5.5", "reasoning_effort": "medium"}
        new_input = {"reasoning_effort": "xhigh"}
        result = _enrich_subentry_data(new_input, base=base)
        assert result["chat_model"] == "gpt-5.5"
        assert result["reasoning_effort"] == "xhigh"

    def test_base_none_returns_clean_dict(self) -> None:
        result = _enrich_subentry_data({"chat_model": "gpt-5.5"}, base=None)
        assert "chat_model" in result
        assert "service_tier" in result

    def test_user_input_overrides_base_chat_model(self) -> None:
        base = {"chat_model": "gpt-5.5"}
        result = _enrich_subentry_data({"chat_model": "gpt-5.6"}, base=base)
        assert result["chat_model"] == "gpt-5.6"
