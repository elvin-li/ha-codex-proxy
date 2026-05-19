"""Tests for CodexConfigFlow.async_step_user (main setup flow).

Covers:
- Form is shown when user_input is None (initial load)
- Form shown with errors on validation failure (missing base_url)
- Form shown with errors when probe fails (cannot_connect)
- Entry created on success with 2 subentries and correct title
- Entry contains api_key and base_url in entry data
- Both subentries have service_tier=None in their data
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap HA stubs
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402
from custom_components.codex_proxy.config_flow import CodexConfigFlow  # noqa: E402
from custom_components.codex_proxy.const import (  # noqa: E402
    CONF_API_KEY,
    CONF_BASE_URL,
    DEFAULT_MODEL,
    SUBENTRY_TYPE_AI_TASK,
    SUBENTRY_TYPE_CONVERSATION,
)

_SERVICE_TIER_KEY = "service_tier"
_VALID_INPUT = {
    CONF_API_KEY: "sk-test",
    CONF_BASE_URL: "https://proxy.example.com",
    "model": DEFAULT_MODEL,
    "toml_config": "",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_flow() -> CodexConfigFlow:
    """Return a CodexConfigFlow with all HA lifecycle plumbing mocked."""
    flow = object.__new__(CodexConfigFlow)
    flow.hass = MagicMock()
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.add_suggested_values_to_schema = MagicMock(side_effect=lambda s, _: s)
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    return flow


# ---------------------------------------------------------------------------
# Form display (no input)
# ---------------------------------------------------------------------------


class TestFormDisplay:
    @pytest.mark.asyncio
    async def test_shows_form_on_initial_load(self) -> None:
        flow = _make_flow()
        result = await flow.async_step_user(None)
        assert result["type"] == "form"
        flow.async_show_form.assert_called_once()

    @pytest.mark.asyncio
    async def test_shows_form_with_errors_on_missing_base_url(self) -> None:
        flow = _make_flow()
        bad_input = {**_VALID_INPUT, CONF_BASE_URL: ""}
        await flow.async_step_user(bad_input)
        # Validation fails — form is re-shown, no probe, no entry creation
        flow.async_show_form.assert_called_once()
        flow.async_create_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_shows_form_with_errors_on_invalid_scheme(self) -> None:
        flow = _make_flow()
        bad_input = {**_VALID_INPUT, CONF_BASE_URL: "ftp://proxy.example.com"}
        await flow.async_step_user(bad_input)
        flow.async_show_form.assert_called_once()
        flow.async_create_entry.assert_not_called()


# ---------------------------------------------------------------------------
# Probe failure
# ---------------------------------------------------------------------------


class TestProbeFailure:
    @pytest.mark.asyncio
    async def test_shows_form_on_probe_failure(self) -> None:
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={"base": "cannot_connect"}),
        ):
            await flow.async_step_user(_VALID_INPUT)
        flow.async_show_form.assert_called_once()
        flow.async_create_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_create_entry_on_auth_error(self) -> None:
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={"base": "invalid_auth"}),
        ):
            await flow.async_step_user(_VALID_INPUT)
        flow.async_create_entry.assert_not_called()


# ---------------------------------------------------------------------------
# Successful entry creation
# ---------------------------------------------------------------------------


class TestEntryCreation:
    @pytest.mark.asyncio
    async def test_creates_entry_on_success(self) -> None:
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_user(_VALID_INPUT)
        flow.async_create_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_entry_data_contains_api_key(self) -> None:
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_user(_VALID_INPUT)
        call_kwargs = flow.async_create_entry.call_args[1]
        assert call_kwargs["data"][CONF_API_KEY] == "sk-test"

    @pytest.mark.asyncio
    async def test_entry_data_contains_base_url(self) -> None:
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_user(_VALID_INPUT)
        call_kwargs = flow.async_create_entry.call_args[1]
        assert call_kwargs["data"][CONF_BASE_URL] == "https://proxy.example.com"

    @pytest.mark.asyncio
    async def test_entry_title_includes_host(self) -> None:
        """Entry title should reference the proxy host for identification."""
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_user(_VALID_INPUT)
        title = flow.async_create_entry.call_args[1]["title"]
        assert "proxy.example.com" in title

    @pytest.mark.asyncio
    async def test_creates_two_subentries(self) -> None:
        """Both conversation and ai_task_data subentries must be created."""
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_user(_VALID_INPUT)
        subentries = flow.async_create_entry.call_args[1]["subentries"]
        assert len(subentries) == 2

    @pytest.mark.asyncio
    async def test_subentry_types_are_conversation_and_ai_task(self) -> None:
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_user(_VALID_INPUT)
        subentries = flow.async_create_entry.call_args[1]["subentries"]
        types = {s["subentry_type"] for s in subentries}
        assert SUBENTRY_TYPE_CONVERSATION in types
        assert SUBENTRY_TYPE_AI_TASK in types

    @pytest.mark.asyncio
    async def test_both_subentries_have_service_tier_none(self) -> None:
        """service_tier=None is critical — prevents proxy 502 errors."""
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_user(_VALID_INPUT)
        subentries = flow.async_create_entry.call_args[1]["subentries"]
        for s in subentries:
            assert s["data"].get(_SERVICE_TIER_KEY) is None, (
                f"Subentry {s['subentry_type']} has non-None service_tier"
            )
