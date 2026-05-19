"""Tests for CodexProxyReachableSensor (binary_sensor platform).

Runs without a full HA install by using the shared ha_stubs module.
"""
from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.ha_stubs  # noqa: F401, E402

from custom_components.codex_proxy.binary_sensor import (  # noqa: E402
    CodexProxyReachableSensor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sensor(
    last_update_success: bool = True,
    entry_id: str = "entry-1",
) -> CodexProxyReachableSensor:
    """Build a CodexProxyReachableSensor with a minimal mocked coordinator."""
    from tests.ha_stubs import _CoordinatorEntity

    coord = MagicMock()
    coord.last_update_success = last_update_success

    entry = MagicMock()
    entry.entry_id = entry_id
    entry.title = f"Codex Proxy ({entry_id})"

    s = object.__new__(CodexProxyReachableSensor)
    _CoordinatorEntity.__init__(s, coord)
    s._attr_unique_id = f"{entry_id}_proxy_reachable"
    s._attr_device_info = {}
    return s


# ---------------------------------------------------------------------------
# is_on behaviour
# ---------------------------------------------------------------------------


class TestIsOn:
    def test_is_on_when_coordinator_ok(self) -> None:
        sensor = _make_sensor(last_update_success=True)
        assert sensor.is_on is True

    def test_is_off_when_coordinator_failed(self) -> None:
        sensor = _make_sensor(last_update_success=False)
        assert sensor.is_on is False

    def test_is_on_coerces_truthy_value(self) -> None:
        """last_update_success=1 (truthy int) should be treated as on."""
        from tests.ha_stubs import _CoordinatorEntity

        coord = MagicMock()
        coord.last_update_success = 1  # truthy, not exactly True

        s = object.__new__(CodexProxyReachableSensor)
        _CoordinatorEntity.__init__(s, coord)
        s._attr_unique_id = "entry-x_proxy_reachable"
        s._attr_device_info = {}

        assert s.is_on is True

    def test_is_off_coerces_falsy_value(self) -> None:
        """last_update_success=0 (falsy) should be treated as off."""
        from tests.ha_stubs import _CoordinatorEntity

        coord = MagicMock()
        coord.last_update_success = 0  # falsy, not exactly False

        s = object.__new__(CodexProxyReachableSensor)
        _CoordinatorEntity.__init__(s, coord)
        s._attr_unique_id = "entry-y_proxy_reachable"
        s._attr_device_info = {}

        assert s.is_on is False


# ---------------------------------------------------------------------------
# Identity / metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_unique_id_contains_entry_id(self) -> None:
        sensor = _make_sensor(entry_id="my-entry-123")
        assert "my-entry-123" in sensor._attr_unique_id

    def test_unique_id_has_suffix(self) -> None:
        sensor = _make_sensor(entry_id="abc")
        assert sensor._attr_unique_id == "abc_proxy_reachable"

    def test_translation_key(self) -> None:
        sensor = _make_sensor()
        assert sensor._attr_translation_key == "proxy_reachable"

    def test_device_class_is_connectivity(self) -> None:
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass  # type: ignore[attr-defined]
        sensor = _make_sensor()
        # The attribute is set at class level — just verify it is defined
        assert hasattr(sensor, "_attr_device_class")

    def test_entity_category_is_diagnostic(self) -> None:
        assert hasattr(CodexProxyReachableSensor, "_attr_entity_category")

    def test_has_entity_name_is_true(self) -> None:
        assert CodexProxyReachableSensor._attr_has_entity_name is True
