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
    """Build a CodexProxyReachableSensor with a minimal mocked coordinator.

    Sets last_update_success_time to a real datetime so the post-poll branch
    of is_on is exercised (not the "unknown before first poll" guard).
    """
    from datetime import datetime

    from tests.ha_stubs import _CoordinatorEntity

    coord = MagicMock()
    coord.last_update_success = last_update_success
    # Explicit non-None timestamp so is_on exercises the post-poll branch.
    coord.last_update_success_time = datetime(2026, 1, 1, tzinfo=UTC)
    coord.last_exception = None  # no error by default

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

    def test_unique_id_exact_format_via_constructor(self) -> None:
        """unique_id must be '{entry_id}_proxy_reachable' when built via the
        real __init__, not just via the _make_sensor helper.

        The existing test_unique_id_has_suffix pins the format but uses the
        _make_sensor helper, which manually sets _attr_unique_id — bypassing the
        constructor.  This test builds via CodexProxyReachableSensor.__init__
        directly so a refactor that changes the suffix or separator in the
        constructor is caught here rather than only discovered at runtime."""
        from unittest.mock import MagicMock

        from tests.ha_stubs import _CoordinatorEntity

        entry = MagicMock()
        entry.entry_id = "pin-entry-bs-42"
        entry.title = "Codex Proxy (pin-entry-bs-42)"
        coord = MagicMock()

        s = object.__new__(CodexProxyReachableSensor)
        _CoordinatorEntity.__init__(s, coord)
        CodexProxyReachableSensor.__init__(s, coord, entry)
        assert s._attr_unique_id == "pin-entry-bs-42_proxy_reachable"

    def test_translation_key(self) -> None:
        sensor = _make_sensor()
        assert sensor._attr_translation_key == "proxy_reachable"

    def test_device_class_is_connectivity(self) -> None:
        """_attr_device_class must be BinarySensorDeviceClass.CONNECTIVITY so the
        entity renders as a connectivity sensor in HA's UI — not just 'defined'
        (matches the value-pinning pattern used in test_button.py and test_sensor.py)."""
        from homeassistant.components.binary_sensor import (  # type: ignore[attr-defined]
            BinarySensorDeviceClass,
        )

        assert CodexProxyReachableSensor._attr_device_class is BinarySensorDeviceClass.CONNECTIVITY

    def test_entity_category_is_diagnostic(self) -> None:
        """_attr_entity_category must be EntityCategory.DIAGNOSTIC so the entity
        lands in the Diagnostic section of the device card, not the primary card."""
        from homeassistant.const import EntityCategory  # type: ignore[attr-defined]

        assert CodexProxyReachableSensor._attr_entity_category is EntityCategory.DIAGNOSTIC

    def test_has_entity_name_is_true(self) -> None:
        assert CodexProxyReachableSensor._attr_has_entity_name is True

    def test_translation_key_in_strings_json(self) -> None:
        """_attr_translation_key must map to an existing key in strings.json entity.binary_sensor.

        HA renders the raw translation-key string (e.g. 'proxy_reachable') instead
        of a human-readable name when this mapping is absent.  A refactor that
        renames the Python attribute without updating strings.json would pass all
        other metadata tests but silently break the UI; this test catches exactly
        that drift."""
        import json
        import pathlib

        strings_path = (
            pathlib.Path(__file__).parent.parent
            / "custom_components"
            / "codex_proxy"
            / "strings.json"
        )
        binary_strings = (
            json.loads(strings_path.read_text()).get("entity", {}).get("binary_sensor", {})
        )
        key = CodexProxyReachableSensor._attr_translation_key
        assert key in binary_strings, (
            f"'{key}' missing from strings.json entity.binary_sensor — "
            "HA will render the raw translation key instead of a human-readable sensor name"
        )


# ---------------------------------------------------------------------------
# extra_state_attributes
# ---------------------------------------------------------------------------


def _make_sensor_with_coord(
    last_update_success: bool = True,
    last_update_success_time=None,
    latest_chat_model_id=None,
    last_exception=None,
    last_update_attempt_time=None,
) -> CodexProxyReachableSensor:
    """Build a sensor wired to a mocked coordinator.

    The ``last_update_attempt_time`` parameter (v0.2.175+) defaults to
    ``last_update_success_time`` for backwards compatibility with tests
    written before the attempt/success split.  This lets old tests continue
    to assert on ``last_checked`` (now derived from attempt time) using
    only the ``last_update_success_time`` kwarg they already pass."""
    from tests.ha_stubs import _CoordinatorEntity

    coord = MagicMock()
    coord.last_update_success = last_update_success
    coord.last_update_success_time = last_update_success_time
    # If the caller didn't override attempt time, mirror the success time so
    # ``last_checked`` keeps the v0.2.174-and-earlier semantic that
    # "last_checked == last_successful_poll" in the absence of any
    # intervening failure.  Tests covering attempt/success divergence pass
    # both kwargs explicitly.
    coord.last_update_attempt_time = (
        last_update_attempt_time
        if last_update_attempt_time is not None
        else last_update_success_time
    )
    coord.latest_chat_model_id = latest_chat_model_id
    coord.last_exception = last_exception

    s = object.__new__(CodexProxyReachableSensor)
    _CoordinatorEntity.__init__(s, coord)
    s._attr_unique_id = "e_proxy_reachable"
    s._attr_device_info = {}
    return s


class TestExtraStateAttributes:
    def test_none_when_both_time_and_model_are_none(self) -> None:
        """Returns None when all three optional attributes are absent.

        Requires ``last_update_success_time=None``, ``latest_chat_model_id=None``,
        **and** ``last_exception=None`` — if any one of them is set the dict is
        non-empty and ``extra_state_attributes`` returns it rather than ``None``.
        """
        s = _make_sensor_with_coord(
            last_update_success_time=None,
            latest_chat_model_id=None,
            last_exception=None,
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

    def test_attrs_exact_keys_after_successful_poll(self) -> None:
        """extra_state_attributes must contain exactly
        {'last_checked', 'last_success', 'latest_model'} after a successful
        poll (v0.2.175+ added ``last_success`` as a separate semantic).

        The previous expected set was {'last_checked', 'latest_model'} —
        before v0.2.175 there was only one timestamp; now ``last_checked``
        means "attempt time" and ``last_success`` means "success time".
        A refactor that accidentally re-merged them, or dropped ``last_error``
        suppression on a healthy coordinator, would slip past an ``in``-only
        check but trips exact set equality."""
        from datetime import datetime

        ts = datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)
        s = _make_sensor_with_coord(
            last_update_success_time=ts,
            latest_chat_model_id="gpt-5.5",
            last_exception=None,
        )
        attrs = s.extra_state_attributes
        assert attrs is not None
        expected = {"last_checked", "last_success", "latest_model"}
        assert set(attrs.keys()) == expected, (
            f"Unexpected keys in extra_state_attributes: "
            f"got {set(attrs.keys())!r}, expected {expected!r}"
        )

    def test_last_checked_diverges_from_last_success_after_failure(self) -> None:
        """v0.2.175 split adds genuine observability value: after a failed
        poll, ``last_checked`` advances to the failed-attempt time while
        ``last_success`` stays at the last good poll.  Operators reading
        the attribute table can immediately tell "the integration is
        actively retrying (last_checked > last_success)" vs "the
        integration is dead silent (last_checked == last_success)"."""
        from datetime import datetime

        success_ts = datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)
        attempt_ts = datetime(2026, 5, 19, 12, 6, 0, tzinfo=UTC)  # 6 min later
        s = _make_sensor_with_coord(
            last_update_success=False,
            last_update_success_time=success_ts,
            last_update_attempt_time=attempt_ts,
            last_exception=Exception("HTTP 503"),
        )
        attrs = s.extra_state_attributes
        assert attrs is not None
        assert attrs["last_checked"] == attempt_ts.isoformat(), (
            "last_checked must follow the most recent attempt, not the last success"
        )
        assert attrs["last_success"] == success_ts.isoformat(), (
            "last_success must stay pinned at the most recent successful poll"
        )
        assert attrs["last_checked"] > attrs["last_success"], (
            "After a failure the attempt timestamp must be strictly newer "
            "than the success timestamp"
        )

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

    def test_last_error_absent_when_no_exception(self) -> None:
        """last_error must not appear in attrs when the coordinator has no exception
        (last poll succeeded or the proxy hasn't been polled yet)."""
        from datetime import datetime

        ts = datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)
        s = _make_sensor_with_coord(
            last_update_success=True,
            last_update_success_time=ts,
            last_exception=None,
        )
        attrs = s.extra_state_attributes
        assert attrs is not None
        assert "last_error" not in attrs

    def test_last_error_present_when_exception_set(self) -> None:
        """When the last poll failed (last_exception is set), last_error must
        appear in attrs so automations can surface the failure reason."""
        s = _make_sensor_with_coord(
            last_exception=Exception("HTTP 503 from proxy"),
        )
        attrs = s.extra_state_attributes
        assert attrs is not None
        assert "last_error" in attrs
        assert "503" in attrs["last_error"]

    def test_last_error_exact_value_from_exception_str(self) -> None:
        """last_error must be exactly str(last_exception) — i.e. the exception
        message without any 'Exception: ' prefix or traceback.

        test_last_error_present_when_exception_set uses a substring check
        ('503' in attrs['last_error']) which passes even if the implementation
        formats the error differently (e.g. 'Exception: HTTP 503 from proxy'
        would still contain '503').  Pinning the exact string ensures the binary
        sensor exposes a clean, jinja-templatable value and not an internal repr."""
        s = _make_sensor_with_coord(
            last_exception=Exception("HTTP 503 from proxy"),
        )
        attrs = s.extra_state_attributes
        assert attrs["last_error"] == "HTTP 503 from proxy", (
            f"Expected 'HTTP 503 from proxy', got {attrs['last_error']!r} — "
            "last_error must be str(exception), not repr() or a prefixed form"
        )

    def test_last_error_is_string(self) -> None:
        """last_error must be a string, not an Exception object, so HA can
        serialise it to the state machine without raising a TypeError."""
        s = _make_sensor_with_coord(
            last_exception=Exception("connection refused"),
        )
        attrs = s.extra_state_attributes
        assert isinstance(attrs["last_error"], str)

    def test_last_error_only_when_no_timestamp_or_model(self) -> None:
        """When only ``last_exception`` is set (no timestamp, no latest model),
        ``extra_state_attributes`` returns a non-None dict containing just the
        ``last_error`` key.  This exercises the branch where ``last_error`` is
        the sole attribute that makes the dict non-empty."""
        s = _make_sensor_with_coord(
            last_update_success_time=None,
            latest_chat_model_id=None,
            last_exception=Exception("never polled"),
        )
        attrs = s.extra_state_attributes
        assert attrs is not None
        assert attrs == {"last_error": "never polled"}
