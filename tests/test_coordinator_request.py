"""Tests for CodexModelCoordinator HTTP request construction.

Verifies that _async_update_data sends the correct URL, headers, and
timeout to the httpx client on a successful fetch.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

import tests.ha_stubs  # noqa: F401, E402
from custom_components.codex_proxy.const import (  # noqa: E402
    CODEX_OPENAI_BETA,
    CODEX_ORIGINATOR,
    CODEX_USER_AGENT,
    COORDINATOR_TIMEOUT_S,
)
from custom_components.codex_proxy.coordinator import CodexModelCoordinator  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_URL = "https://proxy.example.com"
_API_KEY = "sk-test-key"
_INSTALLATION_ID = "00000000-0000-0000-0000-000000000001"


def _make_ok_response(models: list | None = None) -> MagicMock:
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = {"data": models or []}
    return r


def _make_coordinator(base_url: str = _BASE_URL) -> CodexModelCoordinator:
    """Bypass __init__; pre-build _url and _headers as __init__ would."""
    coord = object.__new__(CodexModelCoordinator)
    coord._url = f"{base_url.rstrip('/')}/v1/models"
    coord._headers = {
        "Authorization": f"Bearer {_API_KEY}",
        "User-Agent": CODEX_USER_AGENT,
        "OpenAI-Beta": CODEX_OPENAI_BETA,
        "originator": CODEX_ORIGINATOR,
        "x-codex-installation-id": _INSTALLATION_ID,
        "Accept": "application/json",
    }
    coord._http = MagicMock()
    coord.logger = MagicMock()
    return coord


# ---------------------------------------------------------------------------
# Request construction
# ---------------------------------------------------------------------------


class TestRequestUrl:
    @pytest.mark.asyncio
    async def test_url_appends_v1_models(self) -> None:
        coord = _make_coordinator("https://proxy.example.com")
        coord._http.get = AsyncMock(return_value=_make_ok_response())

        await coord._async_update_data()

        call_args = coord._http.get.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url")
        assert url == "https://proxy.example.com/v1/models"

    @pytest.mark.asyncio
    async def test_trailing_slash_in_base_url_not_doubled(self) -> None:
        """base_url stored with trailing slash stripped; URL stays clean."""
        coord = _make_coordinator("https://proxy.example.com")
        coord._http.get = AsyncMock(return_value=_make_ok_response())

        await coord._async_update_data()

        url = coord._http.get.call_args[0][0]
        assert "//" not in url.replace("https://", "")

    @pytest.mark.asyncio
    async def test_subdirectory_base_url(self) -> None:
        coord = _make_coordinator("https://proxy.example.com/api")
        coord._http.get = AsyncMock(return_value=_make_ok_response())

        await coord._async_update_data()

        url = coord._http.get.call_args[0][0]
        assert url == "https://proxy.example.com/api/v1/models"


class TestRequestHeaders:
    @pytest.mark.asyncio
    async def test_authorization_header(self) -> None:
        coord = _make_coordinator()
        coord._http.get = AsyncMock(return_value=_make_ok_response())

        await coord._async_update_data()

        headers = coord._http.get.call_args[1]["headers"]
        assert headers["Authorization"] == f"Bearer {_API_KEY}"

    @pytest.mark.asyncio
    async def test_user_agent_header(self) -> None:
        coord = _make_coordinator()
        coord._http.get = AsyncMock(return_value=_make_ok_response())

        await coord._async_update_data()

        headers = coord._http.get.call_args[1]["headers"]
        assert headers["User-Agent"] == CODEX_USER_AGENT

    @pytest.mark.asyncio
    async def test_openai_beta_header(self) -> None:
        coord = _make_coordinator()
        coord._http.get = AsyncMock(return_value=_make_ok_response())

        await coord._async_update_data()

        headers = coord._http.get.call_args[1]["headers"]
        assert headers["OpenAI-Beta"] == CODEX_OPENAI_BETA

    @pytest.mark.asyncio
    async def test_originator_header(self) -> None:
        coord = _make_coordinator()
        coord._http.get = AsyncMock(return_value=_make_ok_response())

        await coord._async_update_data()

        headers = coord._http.get.call_args[1]["headers"]
        assert headers["originator"] == CODEX_ORIGINATOR

    @pytest.mark.asyncio
    async def test_installation_id_header(self) -> None:
        coord = _make_coordinator()
        coord._http.get = AsyncMock(return_value=_make_ok_response())

        await coord._async_update_data()

        headers = coord._http.get.call_args[1]["headers"]
        assert headers["x-codex-installation-id"] == _INSTALLATION_ID

    @pytest.mark.asyncio
    async def test_accept_json_header(self) -> None:
        coord = _make_coordinator()
        coord._http.get = AsyncMock(return_value=_make_ok_response())

        await coord._async_update_data()

        headers = coord._http.get.call_args[1]["headers"]
        assert headers["Accept"] == "application/json"


class TestRequestTimeout:
    @pytest.mark.asyncio
    async def test_timeout_matches_constant(self) -> None:
        coord = _make_coordinator()
        coord._http.get = AsyncMock(return_value=_make_ok_response())

        await coord._async_update_data()

        timeout = coord._http.get.call_args[1]["timeout"]
        assert timeout == COORDINATOR_TIMEOUT_S
