"""Tests for _probe_proxy in config_flow.py.

Exercises all error branches (AuthenticationError, NotFoundError, BadRequestError,
APIConnectionError, TimeoutError/OSError) and the success path.

Strategy: we define our own exception stubs as simple Exception subclasses,
then patch config_flow.openai so each `except openai.XyzError:` clause sees
our stub class instead of the real one.  This avoids the test-ordering fragility
caused by ha_stubs potentially replacing sys.modules["openai"] with a MagicMock
before test_probe_proxy.py is imported.
"""

from __future__ import annotations

import sys
import os
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402

from custom_components.codex_proxy.config_flow import _probe_proxy  # noqa: E402


# ---------------------------------------------------------------------------
# Independent exception stubs — no dependency on real openai package
# ---------------------------------------------------------------------------


class _FakeAuthError(Exception):
    pass


class _FakeNotFoundError(Exception):
    pass


class _FakeBadRequestError(Exception):
    def __init__(self, message: str = "bad request") -> None:
        super().__init__(message)
        self.message = message


class _FakeAPIConnectionError(Exception):
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_API_KEY = "sk-test"
_BASE_URL = "https://proxy.example.com"
_MODEL = "gpt-5.5"


def _make_hass() -> MagicMock:
    return MagicMock()


@contextmanager
def _patch_openai(exc_instance=None):
    """Patch config_flow.openai and get_async_client.

    If exc_instance is given, responses.create raises it.
    Otherwise it succeeds and returns a MagicMock.
    """
    if exc_instance is not None:
        create_mock = AsyncMock(side_effect=exc_instance)
    else:
        create_mock = AsyncMock(return_value=MagicMock())

    options_mock = MagicMock()
    options_mock.responses.create = create_mock
    client_mock = MagicMock()
    client_mock.with_options.return_value = options_mock

    with (
        patch("custom_components.codex_proxy.config_flow.openai") as mock_openai,
        patch("custom_components.codex_proxy.config_flow.get_async_client"),
    ):
        mock_openai.AsyncOpenAI.return_value = client_mock
        # Wire our stub classes so except clauses in _probe_proxy match them
        mock_openai.AuthenticationError = _FakeAuthError
        mock_openai.NotFoundError = _FakeNotFoundError
        mock_openai.BadRequestError = _FakeBadRequestError
        mock_openai.APIConnectionError = _FakeAPIConnectionError
        yield mock_openai


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProbeProxySuccess:
    @pytest.mark.asyncio
    async def test_no_errors_on_success(self) -> None:
        with _patch_openai():
            errors = await _probe_proxy(_make_hass(), _API_KEY, _BASE_URL, _MODEL)
        assert errors == {}


class TestProbeProxyAuthError:
    @pytest.mark.asyncio
    async def test_auth_error_returns_invalid_auth(self) -> None:
        with _patch_openai(_FakeAuthError()):
            errors = await _probe_proxy(_make_hass(), _API_KEY, _BASE_URL, _MODEL)
        assert errors.get("base") == "invalid_auth"


class TestProbeProxyNotFoundError:
    @pytest.mark.asyncio
    async def test_not_found_returns_unknown_model(self) -> None:
        with _patch_openai(_FakeNotFoundError()):
            errors = await _probe_proxy(_make_hass(), _API_KEY, _BASE_URL, _MODEL)
        assert errors.get("base") == "unknown_model"


class TestProbeProxyBadRequest:
    @pytest.mark.asyncio
    async def test_bad_request_model_in_message_returns_unknown_model(self) -> None:
        with _patch_openai(_FakeBadRequestError("model not found")):
            errors = await _probe_proxy(_make_hass(), _API_KEY, _BASE_URL, _MODEL)
        assert errors.get("base") == "unknown_model"

    @pytest.mark.asyncio
    async def test_bad_request_without_model_returns_unknown(self) -> None:
        with _patch_openai(_FakeBadRequestError("invalid parameter")):
            errors = await _probe_proxy(_make_hass(), _API_KEY, _BASE_URL, _MODEL)
        assert errors.get("base") == "unknown"


class TestProbeProxyConnectionError:
    @pytest.mark.asyncio
    async def test_api_connection_error_returns_cannot_connect(self) -> None:
        with _patch_openai(_FakeAPIConnectionError()):
            errors = await _probe_proxy(_make_hass(), _API_KEY, _BASE_URL, _MODEL)
        assert errors.get("base") == "cannot_connect"


class TestProbeProxyOsError:
    @pytest.mark.asyncio
    async def test_os_error_returns_cannot_connect(self) -> None:
        with _patch_openai(OSError("network unreachable")):
            errors = await _probe_proxy(_make_hass(), _API_KEY, _BASE_URL, _MODEL)
        assert errors.get("base") == "cannot_connect"

    @pytest.mark.asyncio
    async def test_timeout_error_returns_cannot_connect(self) -> None:
        with _patch_openai(TimeoutError("timed out")):
            errors = await _probe_proxy(_make_hass(), _API_KEY, _BASE_URL, _MODEL)
        assert errors.get("base") == "cannot_connect"
