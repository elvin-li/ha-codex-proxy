"""Tests for CodexModelCoordinator's @property methods.

chat_models filters image-only models; latest_chat_model_id returns the
first result from chat_models.  Runs without a full HA install.
"""
from __future__ import annotations

import sys
import os
from typing import Any
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Bootstrap
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
    "homeassistant.helpers.update_coordinator",
]
for _mod in _HA_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()


class _DataUpdateCoordinatorBase:
    def __class_getitem__(cls, item):  # type: ignore[override]
        return cls

    def __init__(self, hass, logger, name, update_interval):
        self.data: dict[str, Any] | None = None


sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = (
    _DataUpdateCoordinatorBase
)
sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = Exception

from custom_components.codex_proxy.coordinator import CodexModelCoordinator  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coordinator(models: list[dict[str, Any]]) -> CodexModelCoordinator:
    coord = object.__new__(CodexModelCoordinator)
    coord.data = {"models": models}
    return coord


def _m(mid: str, created: int = 0) -> dict[str, Any]:
    return {"id": mid, "created": created, "owned_by": "openai", "display_name": mid}


# ---------------------------------------------------------------------------
# chat_models property
# ---------------------------------------------------------------------------


class TestChatModelsProperty:
    def test_empty_when_no_data(self) -> None:
        coord = object.__new__(CodexModelCoordinator)
        coord.data = None
        assert coord.chat_models == []

    def test_empty_data_dict(self) -> None:
        coord = object.__new__(CodexModelCoordinator)
        coord.data = {}
        assert coord.chat_models == []

    def test_all_chat_models_pass_through(self) -> None:
        models = [_m("gpt-5.5"), _m("gpt-5.4")]
        coord = _make_coordinator(models)
        assert len(coord.chat_models) == 2

    def test_filters_gpt_image_prefix(self) -> None:
        models = [_m("gpt-image-1"), _m("gpt-5.5")]
        coord = _make_coordinator(models)
        ids = [m["id"] for m in coord.chat_models]
        assert "gpt-image-1" not in ids
        assert "gpt-5.5" in ids

    def test_filters_dall_e_prefix(self) -> None:
        models = [_m("dall-e-3"), _m("gpt-5.5")]
        coord = _make_coordinator(models)
        ids = [m["id"] for m in coord.chat_models]
        assert "dall-e-3" not in ids

    def test_filters_image_prefix(self) -> None:
        models = [_m("image-alpha-001"), _m("gpt-5.5")]
        coord = _make_coordinator(models)
        ids = [m["id"] for m in coord.chat_models]
        assert "image-alpha-001" not in ids

    def test_preserves_order(self) -> None:
        models = [_m("gpt-5.6", 200), _m("gpt-5.5", 100)]
        coord = _make_coordinator(models)
        ids = [m["id"] for m in coord.chat_models]
        assert ids == ["gpt-5.6", "gpt-5.5"]


# ---------------------------------------------------------------------------
# latest_chat_model_id property
# ---------------------------------------------------------------------------


class TestLatestChatModelId:
    def test_none_when_no_data(self) -> None:
        coord = object.__new__(CodexModelCoordinator)
        coord.data = None
        assert coord.latest_chat_model_id is None

    def test_none_when_only_image_models(self) -> None:
        coord = _make_coordinator([_m("gpt-image-1"), _m("dall-e-3")])
        assert coord.latest_chat_model_id is None

    def test_returns_first_chat_model(self) -> None:
        coord = _make_coordinator([_m("gpt-5.6", 200), _m("gpt-5.5", 100)])
        assert coord.latest_chat_model_id == "gpt-5.6"

    def test_returns_only_chat_model(self) -> None:
        coord = _make_coordinator([_m("gpt-5.5")])
        assert coord.latest_chat_model_id == "gpt-5.5"

    def test_image_model_skipped_to_find_chat(self) -> None:
        coord = _make_coordinator([_m("gpt-image-1"), _m("gpt-5.5")])
        assert coord.latest_chat_model_id == "gpt-5.5"
