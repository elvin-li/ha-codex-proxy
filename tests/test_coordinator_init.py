"""Tests for CodexModelCoordinator.__init__ attribute wiring.

Verifies that _url, _headers, and _http are set correctly from the config entry
and hass. Uses the ha_stubs DataUpdateCoordinator so the actual __init__ code
path is exercised (not bypassed via object.__new__).
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
    CODEX_OPENAI_BETA,
    CODEX_ORIGINATOR,
    CODEX_USER_AGENT,
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
    def test_url_built_from_base_url(self) -> None:
        coord = _make_coordinator(base_url="https://proxy.example.com")
        assert coord._url == "https://proxy.example.com/v1/models"

    def test_url_trailing_slash_stripped(self) -> None:
        coord = _make_coordinator(base_url="https://proxy.example.com/")
        assert coord._url == "https://proxy.example.com/v1/models"
        assert "//" not in coord._url.replace("https://", "")

    def test_authorization_header_built_from_api_key(self) -> None:
        coord = _make_coordinator(api_key="sk-secret")
        assert coord._headers["Authorization"] == "Bearer sk-secret"

    def test_installation_id_in_header(self) -> None:
        iid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        coord = _make_coordinator(installation_id=iid)
        assert coord._headers["x-codex-installation-id"] == iid

    def test_user_agent_header(self) -> None:
        coord = _make_coordinator()
        assert coord._headers["User-Agent"] == CODEX_USER_AGENT

    def test_openai_beta_header(self) -> None:
        coord = _make_coordinator()
        assert coord._headers["OpenAI-Beta"] == CODEX_OPENAI_BETA

    def test_originator_header(self) -> None:
        coord = _make_coordinator()
        assert coord._headers["originator"] == CODEX_ORIGINATOR

    def test_accept_json_header(self) -> None:
        coord = _make_coordinator()
        assert coord._headers["Accept"] == "application/json"

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
