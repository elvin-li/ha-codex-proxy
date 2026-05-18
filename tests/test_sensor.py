"""Tests for CodexChatModelCountSensor and CodexLastRefreshSensor.

Runs without a full HA install by mocking the homeassistant namespace.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

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
    "homeassistant.components.openai_conversation.conversation",
    "homeassistant.components.openai_conversation.ai_task",
    "homeassistant.components.sensor",
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

# HA stubs needed by sensor.py
sys.modules["homeassistant.const"].EntityCategory = MagicMock()


class _Subscriptable:
    def __class_getitem__(cls, item: Any) -> type:
        return cls


# SensorEntity and CoordinatorEntity base classes
class _SensorEntityBase:
    _attr_has_entity_name = False


class _CoordinatorEntityBase(_Subscriptable):
    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator


sys.modules["homeassistant.components.sensor"].SensorEntity = _SensorEntityBase
sys.modules["homeassistant.components.sensor"].SensorEntityDescription = MagicMock(
    side_effect=lambda **kw: type("Desc", (), kw)()
)
sys.modules["homeassistant.components.sensor"].SensorDeviceClass = MagicMock()
sys.modules["homeassistant.components.sensor"].SensorStateClass = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = (
    _CoordinatorEntityBase
)
sys.modules["homeassistant.helpers.device_registry"].DeviceInfo = dict
sys.modules["homeassistant.helpers.device_registry"].DeviceEntryType = MagicMock()

# Now safe to import
from custom_components.codex_proxy.sensor import (  # noqa: E402
    CodexChatModelCountSensor,
    CodexLastRefreshSensor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coordinator(
    chat_models: list[dict[str, Any]] | None = None,
    last_update_success_time: datetime | None = None,
) -> MagicMock:
    coord = MagicMock()
    coord.chat_models = chat_models or []
    coord.last_update_success_time = last_update_success_time
    return coord


def _make_entry(entry_id: str = "entry-1", title: str = "Codex Pool") -> MagicMock:
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.title = title
    return entry


def _make_count_sensor(
    chat_models: list[dict[str, Any]] | None = None,
    entry_id: str = "entry-1",
) -> CodexChatModelCountSensor:
    coord = _make_coordinator(chat_models=chat_models)
    entry = _make_entry(entry_id=entry_id)
    s = object.__new__(CodexChatModelCountSensor)
    _CoordinatorEntityBase.__init__(s, coord)
    s._attr_unique_id = f"{entry_id}_chat_model_count"
    s._attr_device_info = {}
    # Attach a minimal entity_description
    s.entity_description = type("Desc", (), {"key": "chat_model_count"})()
    return s


def _make_refresh_sensor(
    last_time: datetime | None = None,
    entry_id: str = "entry-1",
) -> CodexLastRefreshSensor:
    coord = _make_coordinator(last_update_success_time=last_time)
    entry = _make_entry(entry_id=entry_id)
    s = object.__new__(CodexLastRefreshSensor)
    _CoordinatorEntityBase.__init__(s, coord)
    s._attr_unique_id = f"{entry_id}_last_model_refresh"
    s._attr_device_info = {}
    s.entity_description = type("Desc", (), {"key": "last_model_refresh"})()
    return s


# ---------------------------------------------------------------------------
# CodexChatModelCountSensor
# ---------------------------------------------------------------------------


class TestChatModelCountSensor:
    def test_zero_when_no_models(self) -> None:
        sensor = _make_count_sensor(chat_models=[])
        assert sensor.native_value == 0

    def test_count_reflects_chat_models_length(self) -> None:
        models = [
            {"id": "gpt-5.5", "created": 100, "owned_by": "openai", "display_name": "GPT-5.5"},
            {"id": "gpt-5.4", "created": 50, "owned_by": "openai", "display_name": "GPT-5.4"},
        ]
        sensor = _make_count_sensor(chat_models=models)
        assert sensor.native_value == 2

    def test_count_five_models(self) -> None:
        models = [{"id": f"gpt-5.{i}", "created": i, "owned_by": "", "display_name": ""} for i in range(5)]
        sensor = _make_count_sensor(chat_models=models)
        assert sensor.native_value == 5

    def test_unique_id_uses_entry_id(self) -> None:
        sensor = _make_count_sensor(entry_id="my-entry-99")
        assert "my-entry-99" in sensor._attr_unique_id


# ---------------------------------------------------------------------------
# CodexLastRefreshSensor
# ---------------------------------------------------------------------------


class TestLastRefreshSensor:
    def test_none_when_never_refreshed(self) -> None:
        sensor = _make_refresh_sensor(last_time=None)
        assert sensor.native_value is None

    def test_returns_datetime_when_set(self) -> None:
        ts = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)
        sensor = _make_refresh_sensor(last_time=ts)
        assert sensor.native_value == ts

    def test_unique_id_uses_entry_id(self) -> None:
        sensor = _make_refresh_sensor(entry_id="entry-xyz")
        assert "entry-xyz" in sensor._attr_unique_id

    def test_timestamp_preserves_timezone(self) -> None:
        ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        sensor = _make_refresh_sensor(last_time=ts)
        result = sensor.native_value
        assert result is not None
        assert result.tzinfo is not None
