"""Tests for async_migrate_entry in __init__.py.

Verifies that:
- Version-1 entries are accepted without modification (no schema change).
- The function always returns True (non-destructive).
Runs without a full HA install.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.ha_stubs  # noqa: F401, E402
from custom_components.codex_proxy import async_migrate_entry  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(version: int = 1, data: dict | None = None) -> MagicMock:
    entry = MagicMock()
    entry.version = version
    entry.data = data or {
        "api_key": "sk-test",
        "base_url": "https://proxy.example.com",
        "codex_installation_id": "00000000-0000-0000-0000-000000000001",
    }
    return entry


def _make_hass() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAsyncMigrateEntry:
    @pytest.mark.asyncio
    async def test_returns_true_for_version_1(self) -> None:
        hass = _make_hass()
        entry = _make_entry(version=1)
        result = await async_migrate_entry(hass, entry)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_for_future_version(self) -> None:
        """Any version should return True (forward-compat: future HA may call
        this with a higher version number; we shouldn't crash)."""
        hass = _make_hass()
        entry = _make_entry(version=99)
        result = await async_migrate_entry(hass, entry)
        assert result is True

    @pytest.mark.asyncio
    async def test_does_not_modify_entry_data_for_v1(self) -> None:
        hass = _make_hass()
        original_data = {
            "api_key": "sk-test",
            "base_url": "https://proxy.example.com",
        }
        entry = _make_entry(version=1, data=dict(original_data))
        await async_migrate_entry(hass, entry)

        # For version-1 (no migration needed), entry data must be untouched
        hass.config_entries.async_update_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_call_async_reload(self) -> None:
        hass = _make_hass()
        entry = _make_entry(version=1)
        await async_migrate_entry(hass, entry)

        hass.config_entries.async_reload.assert_not_called()

    @pytest.mark.asyncio
    async def test_emits_debug_log_with_version(self) -> None:
        """``async_migrate_entry`` must emit a debug log carrying the entry
        version so operators can confirm the migration code path was reached
        when diagnosing startup issues."""
        from unittest.mock import patch

        hass = _make_hass()
        entry = _make_entry(version=42)

        with patch("custom_components.codex_proxy._LOGGER") as mock_logger:
            await async_migrate_entry(hass, entry)

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        # First positional arg is the format string; second is the version
        assert "42" in str(call_args) or call_args.args[1] == 42

    @pytest.mark.asyncio
    async def test_debug_log_version_passed_as_format_arg(self) -> None:
        """The debug call must pass the entry version as a positional format
        argument (not hardcoded in the format string) so a future version bump
        is automatically reflected in the log without editing the format string.

        The existing test_emits_debug_log_with_version uses an OR condition:
        it passes if '42' is anywhere in str(call_args) — including hardcoded
        in the format string itself.  This test requires the version to be the
        second positional arg (call_args.args[1] == 42), ensuring the ``%s``
        (or ``%d``) placeholder is used and filled dynamically."""
        from unittest.mock import patch

        hass = _make_hass()
        entry = _make_entry(version=42)

        with patch("custom_components.codex_proxy._LOGGER") as mock_logger:
            await async_migrate_entry(hass, entry)

        call_args = mock_logger.debug.call_args
        assert call_args.args[1] == 42, (
            f"Expected version 42 as second positional format arg, got {call_args.args!r} — "
            "the version must be passed dynamically to the debug log, not hardcoded in the "
            "format string, so version bumps are reflected automatically"
        )
