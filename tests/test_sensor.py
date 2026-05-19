"""Tests for CodexChatModelCountSensor and CodexLastRefreshSensor.

Runs without a full HA install by using the shared ha_stubs module.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.ha_stubs  # noqa: F401, E402

# Extra stubs needed only by sensor.py
_sen = sys.modules["homeassistant.components.sensor"]
if not callable(getattr(_sen, "SensorEntityDescription", None)):
    _sen.SensorEntityDescription = MagicMock(
        side_effect=lambda **kw: type("Desc", (), kw)()
    )

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


def _make_count_sensor(
    chat_models: list[dict[str, Any]] | None = None,
    entry_id: str = "entry-1",
) -> CodexChatModelCountSensor:
    from tests.ha_stubs import _CoordinatorEntity
    coord = _make_coordinator(chat_models=chat_models)
    s = object.__new__(CodexChatModelCountSensor)
    _CoordinatorEntity.__init__(s, coord)
    s._attr_unique_id = f"{entry_id}_chat_model_count"
    s._attr_device_info = {}
    s.entity_description = type("Desc", (), {"key": "chat_model_count"})()
    return s


def _make_refresh_sensor(
    last_time: datetime | None = None,
    entry_id: str = "entry-1",
) -> CodexLastRefreshSensor:
    from tests.ha_stubs import _CoordinatorEntity
    coord = _make_coordinator(last_update_success_time=last_time)
    s = object.__new__(CodexLastRefreshSensor)
    _CoordinatorEntity.__init__(s, coord)
    s._attr_unique_id = f"{entry_id}_last_model_refresh"
    s._attr_device_info = {}
    s.entity_description = type("Desc", (), {"key": "last_model_refresh"})()
    return s


# ---------------------------------------------------------------------------
# CodexChatModelCountSensor
# ---------------------------------------------------------------------------


class TestClassAttributes:
    def test_has_entity_name_is_true(self) -> None:
        assert CodexChatModelCountSensor._attr_has_entity_name is True
        assert CodexLastRefreshSensor._attr_has_entity_name is True


class TestEntityDescriptions:
    def test_chat_model_count_key(self) -> None:
        from custom_components.codex_proxy.sensor import _CHAT_MODEL_COUNT
        assert _CHAT_MODEL_COUNT.key == "chat_model_count"

    def test_chat_model_count_disabled_by_default(self) -> None:
        from custom_components.codex_proxy.sensor import _CHAT_MODEL_COUNT
        assert _CHAT_MODEL_COUNT.entity_registry_enabled_default is False

    def test_chat_model_count_state_class_is_measurement(self) -> None:
        from custom_components.codex_proxy.sensor import _CHAT_MODEL_COUNT
        from homeassistant.components.sensor import SensorStateClass  # type: ignore[attr-defined]
        assert _CHAT_MODEL_COUNT.state_class is SensorStateClass.MEASUREMENT

    def test_last_refresh_key(self) -> None:
        from custom_components.codex_proxy.sensor import _LAST_REFRESH
        assert _LAST_REFRESH.key == "last_model_refresh"

    def test_last_refresh_disabled_by_default(self) -> None:
        from custom_components.codex_proxy.sensor import _LAST_REFRESH
        assert _LAST_REFRESH.entity_registry_enabled_default is False

    def test_last_refresh_device_class_is_timestamp(self) -> None:
        from custom_components.codex_proxy.sensor import _LAST_REFRESH
        from homeassistant.components.sensor import SensorDeviceClass  # type: ignore[attr-defined]
        assert _LAST_REFRESH.device_class is SensorDeviceClass.TIMESTAMP


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
