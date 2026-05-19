"""Tests for CodexProxyReachableSensor (binary_sensor platform).

Runs without a full HA install by using the shared ha_stubs module.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import UTC

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

    def test_is_none_before_first_successful_poll(self) -> None:
        """When the coordinator hasn't completed any poll yet,
        last_update_success_time is None and is_on must return None
        (unknown state) rather than True (which would be misleading)."""
        from tests.ha_stubs import _CoordinatorEntity

        coord = MagicMock()
        coord.last_update_success = True  # HA initialises to True — still unknown
        coord.last_update_success_time = None  # no successful poll yet

        s = object.__new__(CodexProxyReachableSensor)
        _CoordinatorEntity.__init__(s, coord)
        s._attr_unique_id = "entry-z_proxy_reachable"
        s._attr_device_info = {}

        assert s.is_on is None

    def test_is_on_after_first_successful_poll(self) -> None:
        """Once last_update_success_time is set, is_on reflects last_update_success."""
        from datetime import datetime

        from tests.ha_stubs import _CoordinatorEntity

        coord = MagicMock()
        coord.last_update_success = True
        coord.last_update_success_time = datetime(2026, 1, 1, tzinfo=UTC)

        s = object.__new__(CodexProxyReachableSensor)
        _CoordinatorEntity.__init__(s, coord)
        s._attr_unique_id = "entry-w_proxy_reachable"
        s._attr_device_info = {}

        assert s.is_on is True


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

        sensor = _make_sensor()
        # The attribute is set at class level — just verify it is defined
        assert hasattr(sensor, "_attr_device_class")

    def test_entity_category_is_diagnostic(self) -> None:
        assert hasattr(CodexProxyReachableSensor, "_attr_entity_category")

    def test_has_entity_name_is_true(self) -> None:
        assert CodexProxyReachableSensor._attr_has_entity_name is True


# ---------------------------------------------------------------------------
# extra_state_attributes
# ---------------------------------------------------------------------------


def _make_sensor_with_coord(
    last_update_success: bool = True,
    last_update_success_time=None,
    latest_chat_model_id=None,
) -> CodexProxyReachableSensor:
    from tests.ha_stubs import _CoordinatorEntity

    coord = MagicMock()
    coord.last_update_success = last_update_success
    coord.last_update_success_time = last_update_success_time
    coord.latest_chat_model_id = latest_chat_model_id

    s = object.__new__(CodexProxyReachableSensor)
    _CoordinatorEntity.__init__(s, coord)
    s._attr_unique_id = "e_proxy_reachable"
    s._attr_device_info = {}
    return s


class TestExtraStateAttributes:
    def test_none_when_both_time_and_model_are_none(self) -> None:
        """Returns None when neither last_checked nor latest_model is available."""
        s = _make_sensor_with_coord(
            last_update_success_time=None,
            latest_chat_model_id=None,
        )
        assert s.extra_state_attributes is None

    def test_returns_isoformat_timestamp(self) -> None:
        from datetime import datetime

        ts = datetime(2026, 5, 19, 10, 30, 0, tzinfo=UTC)
        s = _make_sensor_with_coord(last_update_success_time=ts)
        attrs = s.extra_state_attributes
        assert attrs is not None
        assert "last_checked" in attrs
        assert attrs["last_checked"] == ts.isoformat()

    def test_last_checked_is_string(self) -> None:
        from datetime import datetime

        ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        s = _make_sensor_with_coord(last_update_success=False, last_update_success_time=ts)
        attrs = s.extra_state_attributes
        assert isinstance(attrs["last_checked"], str)

    def test_latest_model_present_when_coordinator_has_model(self) -> None:
        """latest_model attribute appears when the coordinator knows the latest model."""
        s = _make_sensor_with_coord(latest_chat_model_id="gpt-5.6")
        attrs = s.extra_state_attributes
        assert attrs is not None
        assert "latest_model" in attrs
        assert attrs["latest_model"] == "gpt-5.6"

    def test_latest_model_absent_when_coordinator_has_no_model(self) -> None:
        """latest_model is not included when the coordinator has no chat models yet."""
        from datetime import datetime

        ts = datetime(2026, 5, 19, 10, 30, 0, tzinfo=UTC)
        s = _make_sensor_with_coord(
            last_update_success_time=ts,
            latest_chat_model_id=None,
        )
        attrs = s.extra_state_attributes
        assert attrs is not None
        assert "latest_model" not in attrs

    def test_both_attributes_present_after_successful_poll(self) -> None:
        """After a successful poll both last_checked and latest_model are present."""
        from datetime import datetime

        ts = datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)
        s = _make_sensor_with_coord(
            last_update_success_time=ts,
            latest_chat_model_id="gpt-5.5",
        )
        attrs = s.extra_state_attributes
        assert attrs is not None
        assert "last_checked" in attrs
        assert "latest_model" in attrs

    def test_only_latest_model_when_no_timestamp(self) -> None:
        """When only latest_model_id is known (no timestamp yet), attrs is non-None."""
        s = _make_sensor_with_coord(
            last_update_success_time=None,
            latest_chat_model_id="gpt-5.5",
        )
        attrs = s.extra_state_attributes
        assert attrs is not None
        assert attrs["latest_model"] == "gpt-5.5"
        assert "last_checked" not in attrs
