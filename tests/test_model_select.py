"""Tests for _model_select_options in config_flow.py.

Exercises the dropdown building logic: coordinator models, custom values,
deduplication, and fallback when coordinator has no data.
"""
from __future__ import annotations

import sys
import os
from typing import Any
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Bootstrap HA stubs
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
    "homeassistant.helpers.httpx_client",
    "homeassistant.helpers.selector",
    "homeassistant.helpers.update_coordinator",
]
for _mod in _HA_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

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

for _mod in ["openai", "voluptuous"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from unittest.mock import patch  # noqa: E402

from custom_components.codex_proxy.config_flow import _model_select_options  # noqa: E402


# SelectOptionDict is a TypedDict — replace its binding inside config_flow so
# opts[0]["value"] / opts[0]["label"] return real strings, not MagicMock.
def _SelectOptionDict(**kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
    return dict(kwargs)


_PATCH_SELECT_OPTION = patch(
    "custom_components.codex_proxy.config_flow.SelectOptionDict",
    side_effect=_SelectOptionDict,
)
from custom_components.codex_proxy.const import DEFAULT_MODEL  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coord(models: list[dict[str, Any]]) -> MagicMock:
    c = MagicMock()
    c.chat_models = models
    return c


def _m(mid: str, display: str | None = None) -> dict[str, Any]:
    return {"id": mid, "created": 0, "owned_by": "", "display_name": display or mid}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestModelSelectOptions:
    def test_none_coordinator_returns_default(self) -> None:
        with _PATCH_SELECT_OPTION:
            opts = _model_select_options(None, None)
        assert len(opts) == 1
        assert opts[0]["value"] == DEFAULT_MODEL

    def test_empty_coordinator_returns_default(self) -> None:
        with _PATCH_SELECT_OPTION:
            opts = _model_select_options(_coord([]), None)
        assert len(opts) == 1
        assert opts[0]["value"] == DEFAULT_MODEL

    def test_coordinator_models_listed(self) -> None:
        with _PATCH_SELECT_OPTION:
            opts = _model_select_options(_coord([_m("gpt-5.5"), _m("gpt-5.4")]), None)
        values = [o["value"] for o in opts]
        assert "gpt-5.5" in values
        assert "gpt-5.4" in values

    def test_current_model_prepended_if_not_in_coordinator(self) -> None:
        with _PATCH_SELECT_OPTION:
            opts = _model_select_options(_coord([_m("gpt-5.5")]), "gpt-5.3-turbo")
        assert opts[0]["value"] == "gpt-5.3-turbo"

    def test_current_model_not_duplicated_if_already_present(self) -> None:
        with _PATCH_SELECT_OPTION:
            opts = _model_select_options(_coord([_m("gpt-5.5"), _m("gpt-5.4")]), "gpt-5.5")
        values = [o["value"] for o in opts]
        assert values.count("gpt-5.5") == 1

    def test_display_name_used_as_label(self) -> None:
        with _PATCH_SELECT_OPTION:
            opts = _model_select_options(_coord([_m("gpt-5.5", "GPT-5.5 Preview")]), None)
        gpt55 = next(o for o in opts if o["value"] == "gpt-5.5")
        assert gpt55["label"] == "GPT-5.5 Preview"

    def test_id_used_as_label_when_no_display_name(self) -> None:
        with _PATCH_SELECT_OPTION:
            opts = _model_select_options(_coord([_m("gpt-5.5")]), None)
        assert opts[0]["label"] == "gpt-5.5"

    def test_deduplication_by_id(self) -> None:
        # Two entries with same id — should only appear once
        with _PATCH_SELECT_OPTION:
            opts = _model_select_options(
                _coord([_m("gpt-5.5"), _m("gpt-5.5")]), None
            )
        values = [o["value"] for o in opts]
        assert values.count("gpt-5.5") == 1

    def test_none_current_model_no_prepend(self) -> None:
        with _PATCH_SELECT_OPTION:
            opts = _model_select_options(_coord([_m("gpt-5.5")]), None)
        assert len(opts) == 1

    def test_empty_string_current_model_no_prepend(self) -> None:
        with _PATCH_SELECT_OPTION:
            opts = _model_select_options(_coord([_m("gpt-5.5")]), "")
        # Empty string is falsy — should not prepend
        assert len(opts) == 1
