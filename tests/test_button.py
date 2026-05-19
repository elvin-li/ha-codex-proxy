"""Tests for CodexRefreshModelsButton.

Covers: unique_id, async_press calls async_request_refresh exactly once,
noop on double-press is handled by coordinator throttle (not our code).
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.ha_stubs  # noqa: F401, E402
from custom_components.codex_proxy.button import CodexRefreshModelsButton  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coordinator() -> MagicMock:
    coord = MagicMock()
    coord.async_request_refresh = AsyncMock()
    return coord


def _make_button(entry_id: str = "entry-1") -> CodexRefreshModelsButton:
    """Construct a button entity wired to a live coordinator via ``hass.data``.

    The button no longer holds a direct ``self._coordinator`` reference — it
    looks up the coordinator from ``hass.data[DOMAIN][entry_id][DATA_COORDINATOR]``
    on every press so a reload that swaps the coordinator instance does not
    leave the button pointing at a stale one.  Tests can still inspect the
    coordinator via the ``_test_coordinator`` attribute installed below.
    """
    from custom_components.codex_proxy.const import DATA_COORDINATOR, DOMAIN

    coord = _make_coordinator()
    btn = object.__new__(CodexRefreshModelsButton)
    btn._entry_id = entry_id
    btn._attr_unique_id = f"{entry_id}_refresh_models"
    btn._attr_device_info = {}
    btn.hass = MagicMock()
    btn.hass.data = {DOMAIN: {entry_id: {DATA_COORDINATOR: coord}}}
    # Expose the coordinator for test assertions without re-introducing the
    # stale-reference issue the production code path was hardened against.
    btn._test_coordinator = coord
    return btn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestClassAttributes:
    def test_has_entity_name_is_true(self) -> None:
        assert CodexRefreshModelsButton._attr_has_entity_name is True

    def test_translation_key(self) -> None:
        assert CodexRefreshModelsButton._attr_translation_key == "refresh_models"

    def test_entity_category_is_diagnostic(self) -> None:
        from homeassistant.const import EntityCategory  # type: ignore[attr-defined]

        assert CodexRefreshModelsButton._attr_entity_category is EntityCategory.DIAGNOSTIC

    def test_device_class_is_update(self) -> None:
        from homeassistant.components.button import ButtonDeviceClass  # type: ignore[attr-defined]

        assert CodexRefreshModelsButton._attr_device_class is ButtonDeviceClass.UPDATE

    def test_translation_key_in_strings_json(self) -> None:
        """_attr_translation_key must map to an existing key in strings.json entity.button.

        HA renders the raw translation-key string (e.g. 'refresh_models') instead
        of a human-readable label when this mapping is absent.  A refactor that
        renames the Python attribute without updating strings.json would pass all
        other ClassAttribute tests but silently break the UI; this test catches
        exactly that drift."""
        import json
        import pathlib

        strings_path = (
            pathlib.Path(__file__).parent.parent
            / "custom_components"
            / "codex_proxy"
            / "strings.json"
        )
        button_strings = json.loads(strings_path.read_text()).get("entity", {}).get("button", {})
        key = CodexRefreshModelsButton._attr_translation_key
        assert key in button_strings, (
            f"'{key}' missing from strings.json entity.button — "
            "HA will render the raw translation key instead of a human-readable button label"
        )


class TestRefreshModelsButton:
    def test_unique_id_exact_format(self) -> None:
        """unique_id must be '{entry_id}_refresh_models' exactly.

        Builds via the real ``__init__`` so a change in the constructor is
        caught directly.  Round-3 audit removed the prior
        ``test_unique_id_uses_entry_id`` because it tested the test helper
        (``_make_button`` *manually* assigned ``_attr_unique_id``) rather
        than the production ``__init__`` — the assertion would have passed
        even if ``CodexRefreshModelsButton.__init__`` were stubbed out.
        This single exact-format test, which exercises the real ``__init__``,
        supersedes it."""
        entry = MagicMock()
        entry.entry_id = "pin-entry-99"
        btn = object.__new__(CodexRefreshModelsButton)
        CodexRefreshModelsButton.__init__(btn, _make_coordinator(), entry)
        assert btn._attr_unique_id == "pin-entry-99_refresh_models"

    @pytest.mark.asyncio
    async def test_press_calls_async_request_refresh(self) -> None:
        btn = _make_button()
        await btn.async_press()
        btn._test_coordinator.async_request_refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_double_press_calls_refresh_twice(self) -> None:
        """The button is stateless — it calls async_request_refresh on every press.
        The coordinator itself throttles redundant refreshes."""
        btn = _make_button()
        await btn.async_press()
        await btn.async_press()
        assert btn._test_coordinator.async_request_refresh.await_count == 2

    @pytest.mark.asyncio
    async def test_press_emits_debug_log(self) -> None:
        """async_press should emit exactly one DEBUG log so operators can confirm
        the manual refresh was triggered."""
        from unittest.mock import patch

        btn = _make_button()
        with patch("custom_components.codex_proxy.button._LOGGER") as mock_log:
            await btn.async_press()
        mock_log.debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_press_debug_log_message_content(self) -> None:
        """The debug log format string must mention 'refresh' so the message is
        self-explanatory in HA logs without needing to cross-reference source code.

        test_press_emits_debug_log only asserts the logger was called once; a
        refactor that changed the message to a generic 'OK' or an empty string
        would still pass that test.  This test pins the format string at args[0]
        so a content change is caught immediately."""
        from unittest.mock import patch

        btn = _make_button()
        with patch("custom_components.codex_proxy.button._LOGGER") as mock_log:
            await btn.async_press()
        fmt = mock_log.debug.call_args.args[0]
        assert "refresh" in fmt.lower(), (
            f"Button debug log message {fmt!r} must mention 'refresh' — "
            "operators look for this keyword when triaging manual-refresh events"
        )

    @pytest.mark.asyncio
    async def test_press_debug_log_exact_format_string(self) -> None:
        """async_press must log exactly 'Manual /v1/models refresh requested'.

        test_press_debug_log_mentions_refresh uses a case-insensitive substring
        check — any message containing 'refresh' passes, including a generic
        'refresh done' that drops the '/v1/models' endpoint detail operators
        need to identify which API call was triggered.  Pinning the exact string
        catches any wording change before it reaches production log streams."""
        from unittest.mock import patch

        btn = _make_button()
        with patch("custom_components.codex_proxy.button._LOGGER") as mock_log:
            await btn.async_press()
        fmt = mock_log.debug.call_args.args[0]
        assert fmt == "Manual /v1/models refresh requested", (
            f"Expected exact log message 'Manual /v1/models refresh requested', got {fmt!r}"
        )
