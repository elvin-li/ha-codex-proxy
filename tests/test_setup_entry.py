"""Tests for async_setup_entry in codex_proxy/__init__.py.

Focuses on:
- installation_id is generated when absent from entry.data
- installation_id is reused when already present (no async_update_entry call)
- coordinator failure path: entry still loads (returns True)
- hass.data is populated with DATA_COORDINATOR key
- async_forward_entry_setups is called with PLATFORMS
Runs without a full HA install.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import httpx  # noqa: E402, I001
import tests.ha_stubs  # noqa: F401, E402, I001
from custom_components.codex_proxy import async_setup_entry  # noqa: E402
from custom_components.codex_proxy.const import (  # noqa: E402
    CONF_INSTALLATION_ID,
    DATA_COORDINATOR,
    DOMAIN,
)
from homeassistant.helpers.update_coordinator import UpdateFailed  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(
    entry_id: str = "entry-1",
    installation_id: str | None = None,
) -> MagicMock:
    """Return a mock ConfigEntry optionally pre-populated with an installation_id."""
    entry = MagicMock()
    entry.entry_id = entry_id
    data: dict = {
        "api_key": "sk-test-key",
        # Use the already-normalised form so async_setup_entry does not write
        # back a migration update for the base_url (that would interfere with
        # tests asserting async_update_entry was NOT called).  Tests that need
        # to exercise the bare-host → /v1 migration set base_url explicitly.
        "base_url": "https://proxy.example.com/v1",
    }
    if installation_id is not None:
        data[CONF_INSTALLATION_ID] = installation_id
    entry.data = data
    entry.async_on_unload = MagicMock()
    return entry


def _make_hass() -> MagicMock:
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_update_entry = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    return hass


def _patch_coordinator(first_refresh_side_effect=None):
    """Return a context manager that replaces CodexModelCoordinator with a mock."""
    coord_mock = MagicMock()
    refresh = AsyncMock(side_effect=first_refresh_side_effect)
    coord_mock.async_config_entry_first_refresh = refresh
    return patch(
        "custom_components.codex_proxy.CodexModelCoordinator",
        return_value=coord_mock,
    ), coord_mock


# ---------------------------------------------------------------------------
# installation_id handling
# ---------------------------------------------------------------------------


class TestInstallationId:
    @pytest.mark.asyncio
    async def test_generates_installation_id_when_absent(self) -> None:
        """When entry.data has no installation_id, a fresh UUID is generated and
        async_update_entry is called to persist it."""
        entry = _make_entry(installation_id=None)
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = hass.config_entries.async_update_entry.call_args
        new_data = call_kwargs[1].get("data") or call_kwargs[0][1]
        assert CONF_INSTALLATION_ID in new_data
        # Should be a valid UUID string
        import uuid

        uuid.UUID(new_data[CONF_INSTALLATION_ID])  # raises if invalid

    @pytest.mark.asyncio
    async def test_installation_id_update_uses_keyword_data_arg(self) -> None:
        """async_update_entry must receive the new entry data as a ``data``
        keyword argument, not as a second positional argument.

        test_generates_installation_id_when_absent extracts new_data with:
          ``call_kwargs[1].get("data") or call_kwargs[0][1]``
        The fallback ``call_kwargs[0][1]`` (second positional arg) is dead code
        because ``async_update_entry(entry, data=…)`` only ever has one
        positional arg (entry).  This test pins the keyword-arg convention
        explicitly so a refactor that accidentally switches to a positional call
        is caught here rather than silently relying on a dead-code fallback."""
        entry = _make_entry(installation_id=None)
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        call_args = hass.config_entries.async_update_entry.call_args
        assert "data" in call_args.kwargs, (
            "async_update_entry must be called with 'data' as a keyword arg — "
            "passing it positionally would be incorrect and fragile"
        )

    @pytest.mark.asyncio
    async def test_reuses_installation_id_when_present(self) -> None:
        """When entry.data already has an installation_id, it must be reused and
        async_update_entry must NOT be called."""
        iid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        entry = _make_entry(installation_id=iid)
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        hass.config_entries.async_update_entry.assert_not_called()


# ---------------------------------------------------------------------------
# Lazy base_url migration
# ---------------------------------------------------------------------------


class TestBaseUrlMigration:
    """Pre-v0.2.171 entries stored ``base_url`` without the OpenAI-compatible
    ``/v1`` suffix; ``async_setup_entry`` lazily migrates them.  These tests
    pin the migration contract so it survives future refactors."""

    @pytest.mark.asyncio
    async def test_bare_host_data_gets_v1_appended(self) -> None:
        entry = _make_entry(installation_id="iid-mig1")
        entry.data = {
            "api_key": "sk-test",
            "base_url": "https://legacy.example.com",  # bare host, pre-v0.2.171
            CONF_INSTALLATION_ID: "iid-mig1",
        }
        entry.unique_id = "https://legacy.example.com"
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        hass.config_entries.async_update_entry.assert_called_once()
        call = hass.config_entries.async_update_entry.call_args
        new_data = call[1]["data"]
        assert new_data["base_url"] == "https://legacy.example.com/v1", (
            "Lazy migration must append /v1 to a bare-host base_url so the "
            "OpenAI SDK hits /v1/responses on subsequent loads"
        )

    @pytest.mark.asyncio
    async def test_bare_host_unique_id_also_migrated(self) -> None:
        """Migrating ``data.base_url`` without also rewriting ``unique_id``
        breaks the reconfigure flow: ``_abort_if_unique_id_mismatch`` rejects
        every legacy entry because the form sets ``unique_id`` to the
        ``/v1``-normalised form while the entry still carries the bare-host
        value.  This test pins that ``unique_id`` and ``base_url`` are
        migrated together when they previously matched."""
        entry = _make_entry(installation_id="iid-mig2")
        entry.data = {
            "api_key": "sk-test",
            "base_url": "https://legacy.example.com",
            CONF_INSTALLATION_ID: "iid-mig2",
        }
        entry.unique_id = "https://legacy.example.com"
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        call = hass.config_entries.async_update_entry.call_args
        assert call[1].get("unique_id") == "https://legacy.example.com/v1", (
            "Lazy migration must also rewrite entry.unique_id to the "
            "normalised form — otherwise the reconfigure flow's "
            "_abort_if_unique_id_mismatch rejects every legacy entry forever"
        )

    @pytest.mark.asyncio
    async def test_already_normalised_does_not_trigger_update(self) -> None:
        """When the stored ``base_url`` already ends in ``/v1`` (newer entry
        or already-migrated one), ``async_update_entry`` MUST NOT be called —
        otherwise every restart rewrites the storage file pointlessly and
        the migration is no longer idempotent."""
        entry = _make_entry(installation_id="iid-normalised")
        entry.data = {
            "api_key": "sk-test",
            "base_url": "https://newer.example.com/v1",  # already normalised
            CONF_INSTALLATION_ID: "iid-normalised",
        }
        entry.unique_id = "https://newer.example.com/v1"
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        hass.config_entries.async_update_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_user_renamed_unique_id_not_overwritten(self) -> None:
        """If the user (or a previous reconfigure) deliberately set
        ``entry.unique_id`` to something other than the bare-host base_url,
        the lazy migration must not clobber it.  We only rewrite when the
        old ``unique_id`` matched the old ``base_url`` exactly."""
        entry = _make_entry(installation_id="iid-rename")
        entry.data = {
            "api_key": "sk-test",
            "base_url": "https://legacy.example.com",
            CONF_INSTALLATION_ID: "iid-rename",
        }
        entry.unique_id = "custom-user-supplied-id"
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        call = hass.config_entries.async_update_entry.call_args
        assert "unique_id" not in call[1], (
            "Custom user-supplied unique_id must be preserved verbatim; only "
            "the legacy bare-host == base_url case triggers a unique_id rewrite"
        )


# ---------------------------------------------------------------------------
# Return value and hass.data
# ---------------------------------------------------------------------------


class TestSetupResult:
    @pytest.mark.asyncio
    async def test_returns_true(self) -> None:
        entry = _make_entry(installation_id="iid-ok")
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            result = await async_setup_entry(hass, entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_hass_data_populated(self) -> None:
        entry = _make_entry("entry-data", installation_id="iid-data")
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        assert DOMAIN in hass.data
        assert "entry-data" in hass.data[DOMAIN]
        assert DATA_COORDINATOR in hass.data[DOMAIN]["entry-data"]

    @pytest.mark.asyncio
    async def test_hass_data_entry_contains_exactly_coordinator_key(self) -> None:
        """hass.data[DOMAIN][entry_id] must contain exactly the DATA_COORDINATOR key.

        test_hass_data_populated checks the key is *present* using ``in``, but
        does not verify that no extra keys were accidentally stored alongside it.
        A refactor that adds a second key (e.g. for caching or a second coordinator)
        without updating the diagnostics or unload code would pass the existing test
        but break the single-key contract documented in const.py.

        Exact set equality here catches both omissions and accidental additions."""
        entry = _make_entry("entry-xk", installation_id="iid-xk")
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        entry_data = hass.data[DOMAIN]["entry-xk"]
        assert set(entry_data.keys()) == {DATA_COORDINATOR}, (
            f"hass.data[DOMAIN][entry_id] must contain exactly {{DATA_COORDINATOR}}, "
            f"got keys: {set(entry_data.keys())!r}"
        )

    @pytest.mark.asyncio
    async def test_forward_entry_setups_called(self) -> None:
        from custom_components.codex_proxy import PLATFORMS

        entry = _make_entry(installation_id="iid-fwd")
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(entry, PLATFORMS)


# ---------------------------------------------------------------------------
# Coordinator first-refresh failure — should not prevent entry from loading
# ---------------------------------------------------------------------------


class TestCoordinatorFailurePath:
    @pytest.mark.asyncio
    async def test_returns_true_when_coordinator_raises_update_failed(self) -> None:
        """UpdateFailed on first refresh is non-fatal; entry still loads."""

        entry = _make_entry(installation_id="iid-fail")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(first_refresh_side_effect=UpdateFailed("poll failed"))

        with patcher:
            result = await async_setup_entry(hass, entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_data_still_stored_when_coordinator_refresh_fails(self) -> None:
        """Even on refresh failure the coordinator is stored in hass.data so the
        next poll can succeed without a full reload."""
        entry = _make_entry("entry-fail2", installation_id="iid-fail2")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(first_refresh_side_effect=UpdateFailed("timeout"))

        with patcher:
            await async_setup_entry(hass, entry)

        assert DATA_COORDINATOR in hass.data[DOMAIN]["entry-fail2"]

    @pytest.mark.asyncio
    async def test_httpx_http_error_is_non_fatal(self) -> None:
        """httpx.HTTPError during first refresh is caught and treated as
        non-fatal — the except clause in __init__.py covers both UpdateFailed
        and httpx.HTTPError."""
        entry = _make_entry("entry-fail3", installation_id="iid-fail3")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(
            first_refresh_side_effect=httpx.ConnectError("connection refused")
        )

        with patcher:
            result = await async_setup_entry(hass, entry)

        assert result is True
        assert DATA_COORDINATOR in hass.data[DOMAIN]["entry-fail3"]

    @pytest.mark.asyncio
    async def test_warning_logged_when_coordinator_refresh_fails(self) -> None:
        """When the coordinator's first refresh raises UpdateFailed or
        httpx.HTTPError, ``async_setup_entry`` must emit exactly one
        ``_LOGGER.warning`` call carrying the error so operators can diagnose
        transient startup failures from HA logs without enabling full DEBUG."""
        from unittest.mock import patch

        entry = _make_entry(installation_id="iid-warn")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(first_refresh_side_effect=UpdateFailed("proxy unreachable"))

        with (
            patcher,
            patch("custom_components.codex_proxy._LOGGER") as mock_log,
        ):
            await async_setup_entry(hass, entry)

        mock_log.warning.assert_called_once()
        logged = str(mock_log.warning.call_args)
        assert "proxy unreachable" in logged or "Initial model refresh failed" in logged

    @pytest.mark.asyncio
    async def test_warning_log_prefix_is_initial_model_refresh_failed(self) -> None:
        """The warning format string must begin with 'Initial model refresh failed'
        so operators can distinguish startup-phase coordinator failures from
        later runtime poll failures in HA logs.

        The existing test_warning_logged_when_coordinator_refresh_fails uses an
        OR condition (error text OR format prefix); without this dedicated test a
        refactor that changes the format string to e.g. 'Coordinator error: %s'
        would still pass because the exception text 'proxy unreachable' appears
        in the call_args repr regardless of the format prefix."""
        from unittest.mock import patch

        entry = _make_entry(installation_id="iid-prefix")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(first_refresh_side_effect=UpdateFailed("proxy unreachable"))

        with (
            patcher,
            patch("custom_components.codex_proxy._LOGGER") as mock_log,
        ):
            await async_setup_entry(hass, entry)

        logged = str(mock_log.warning.call_args)
        assert "Initial model refresh failed" in logged, (
            "Warning format prefix 'Initial model refresh failed' missing from "
            "startup coordinator failure log — operators cannot distinguish "
            "startup-phase failures without the specific prefix in HA logs"
        )

    @pytest.mark.asyncio
    async def test_warning_log_includes_exception_message(self) -> None:
        """The warning call must pass the exception as a format argument so the
        specific error message ('proxy unreachable') appears in HA logs.

        The existing test_warning_logged_when_coordinator_refresh_fails uses an
        OR condition: it passes whether the exception text OR the format prefix
        is present.  test_warning_log_prefix_is_initial_model_refresh_failed
        covers the prefix half; this test covers the exception-text half.

        Without the ``%s`` arg (e.g. ``_LOGGER.warning("Initial model refresh
        failed")`` with no error arg), operators see the static prefix but not
        the root cause — 'proxy unreachable', 'timeout', etc. — forcing them to
        correlate timestamps with other log entries to find the failure reason."""
        from unittest.mock import patch

        entry = _make_entry(installation_id="iid-excmsg")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(first_refresh_side_effect=UpdateFailed("proxy unreachable"))

        with (
            patcher,
            patch("custom_components.codex_proxy._LOGGER") as mock_log,
        ):
            await async_setup_entry(hass, entry)

        logged = str(mock_log.warning.call_args)
        assert "proxy unreachable" in logged, (
            "Exception message 'proxy unreachable' missing from warning log — "
            "operators need the root-cause text to diagnose startup failures "
            "without enabling coordinator DEBUG logging"
        )

    @pytest.mark.asyncio
    async def test_warning_log_format_string_exact(self) -> None:
        """args[0] of the coordinator-failure warning must be the exact format string.

        test_warning_log_prefix_is_initial_model_refresh_failed checks that
        'Initial model refresh failed' appears in str(call_args) — a substring
        check that passes even if it is embedded in the exception text rather
        than in the format string (e.g. UpdateFailed('Initial model refresh
        failed: proxy unreachable') would satisfy the substring).

        test_warning_log_includes_exception_message covers the exception-text
        arg; this test covers args[0] — the format string 'Initial model
        refresh failed: %s' — ensuring the wording is split correctly between
        template and argument."""
        from unittest.mock import patch

        entry = _make_entry(installation_id="iid-fmtpin")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(first_refresh_side_effect=UpdateFailed("proxy unreachable"))

        with (
            patcher,
            patch("custom_components.codex_proxy._LOGGER") as mock_log,
        ):
            await async_setup_entry(hass, entry)

        fmt = mock_log.warning.call_args.args[0]
        assert fmt == "Initial model refresh failed: %s", (
            f"Expected format string 'Initial model refresh failed: %s', got {fmt!r} — "
            "the format string must pass the exception as a %s arg, not interpolate it"
        )

    @pytest.mark.asyncio
    async def test_config_entry_not_ready_is_non_fatal(self) -> None:
        """``async_config_entry_first_refresh`` catches ``UpdateFailed`` from
        ``_async_update_data`` and re-raises it as ``ConfigEntryNotReady``.

        Pre-v0.2.172 the except clause only covered ``UpdateFailed`` and
        ``httpx.HTTPError`` — so in production the entry would fail to load
        entirely on any transient proxy hiccup at HA startup (the
        documentation comment promised "warn and continue" but the code
        delivered "fail").  This test pins the contract: a
        ``ConfigEntryNotReady`` raised from first refresh must be caught and
        the entry must still load."""
        from homeassistant.exceptions import ConfigEntryNotReady  # type: ignore[attr-defined]

        entry = _make_entry("entry-cenr", installation_id="iid-cenr")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(
            first_refresh_side_effect=ConfigEntryNotReady("proxy unreachable")
        )

        with patcher:
            result = await async_setup_entry(hass, entry)

        assert result is True, (
            "async_setup_entry must return True even when the first refresh "
            "raises ConfigEntryNotReady — the entity tree should still register "
            "so users see the proxy_reachable binary_sensor reporting OFF "
            "instead of seeing the entire entry stuck in 'setup_retry'"
        )
        assert DATA_COORDINATOR in hass.data[DOMAIN]["entry-cenr"], (
            "coordinator must still be stored in hass.data after a "
            "ConfigEntryNotReady — otherwise the next periodic refresh has "
            "nowhere to publish its result"
        )
