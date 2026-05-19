"""Tests for CodexModelCoordinator.__init__ attribute wiring.

Verifies that _api_key, _base_url, _installation_id, and _http are set
correctly from the config entry and hass. Uses the ha_stubs DataUpdateCoordinator
so the actual __init__ code path is exercised (not bypassed via object.__new__).
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

# Bootstrap HA stubs BEFORE any codex_proxy import
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402
from custom_components.codex_proxy.const import (  # noqa: E402
    CONF_API_KEY,
    CONF_BASE_URL,
    MODEL_REFRESH_INTERVAL,
)
from custom_components.codex_proxy.coordinator import CodexModelCoordinator  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_HTTP_CLIENT = MagicMock()


def _make_entry(
    api_key: str = "sk-test",
    base_url: str = "https://proxy.example.com",
    entry_id: str = "entry-1",
) -> MagicMock:
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = {CONF_API_KEY: api_key, CONF_BASE_URL: base_url}
    return entry


def _make_coordinator(
    api_key: str = "sk-test",
    base_url: str = "https://proxy.example.com",
    installation_id: str = "00000000-0000-0000-0000-000000000001",
) -> CodexModelCoordinator:
    hass = MagicMock()
    entry = _make_entry(api_key=api_key, base_url=base_url)
    with patch(
        "custom_components.codex_proxy.coordinator.get_async_client",
        return_value=_FAKE_HTTP_CLIENT,
    ):
        return CodexModelCoordinator(hass, entry, installation_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCoordinatorInit:
    def test_api_key_stored(self) -> None:
        coord = _make_coordinator(api_key="sk-secret")
        assert coord._api_key == "sk-secret"

    def test_base_url_stored(self) -> None:
        coord = _make_coordinator(base_url="https://proxy.example.com")
        assert coord._base_url == "https://proxy.example.com"

    def test_base_url_trailing_slash_stripped(self) -> None:
        coord = _make_coordinator(base_url="https://proxy.example.com/")
        assert not coord._base_url.endswith("/")
        assert coord._base_url == "https://proxy.example.com"

    def test_installation_id_stored(self) -> None:
        iid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        coord = _make_coordinator(installation_id=iid)
        assert coord._installation_id == iid

    def test_http_client_set_from_hass(self) -> None:
        coord = _make_coordinator()
        assert coord._http is _FAKE_HTTP_CLIENT

    def test_update_interval_set(self) -> None:
        coord = _make_coordinator()
        assert coord.update_interval == MODEL_REFRESH_INTERVAL

    def test_name_contains_entry_id(self) -> None:
        hass = MagicMock()
        entry = _make_entry(entry_id="my-unique-entry")
        with patch(
            "custom_components.codex_proxy.coordinator.get_async_client",
            return_value=MagicMock(),
        ):
            coord = CodexModelCoordinator(hass, entry, "iid-1")
        assert "my-unique-entry" in coord.name
