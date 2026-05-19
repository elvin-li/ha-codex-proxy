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
    async def test_entry_title_exact_format(self) -> None:
        """Entry title must follow the exact format 'Codex 号池 (<netloc>)'.

        test_entry_title_includes_host uses a substring check that passes
        even if the title format changes (e.g. 'Proxy proxy.example.com' or
        'Codex proxy.example.com' without the parentheses would both pass).
        The exact title is critical because it appears in the HA integrations
        dashboard and in YAML snippets shared between users; a refactor that
        changes the format silently breaks existing user documentation.

        Expected: 'Codex 号池 (proxy.example.com)' for base_url
        'https://proxy.example.com'."""
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_user(_VALID_INPUT)
        title = flow.async_create_entry.call_args[1]["title"]
        assert title == "Codex 号池 (proxy.example.com)", (
            f"Entry title {title!r} does not match expected format "
            "'Codex 号池 (proxy.example.com)' — the substring test "
            "test_entry_title_includes_host would still pass with the wrong format"
        )

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
    async def test_subentry_types_exact_set(self) -> None:
        """async_create_entry must produce *exactly* one conversation subentry and
        one ai_task_data subentry — no more, no less.

        test_subentry_types_are_conversation_and_ai_task uses two ``in`` checks
        which pass even if a third unexpected subentry type is accidentally added
        (e.g. ``"light"`` from a misapplied copy-paste).  An extra subentry type
        would silently create unwanted entities in the device registry.  Exact
        set equality catches that before it reaches production."""
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_user(_VALID_INPUT)
        subentries = flow.async_create_entry.call_args[1]["subentries"]
        types = {s["subentry_type"] for s in subentries}
        expected = {SUBENTRY_TYPE_CONVERSATION, SUBENTRY_TYPE_AI_TASK}
        assert types == expected, (
            f"Expected subentry types {expected}, got {types}. Unexpected: {types - expected}"
        )

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

    @pytest.mark.asyncio
    async def test_probe_called_with_user_credentials(self) -> None:
        """_probe_proxy must receive the api_key and base_url from user input.

        A regression that probed with hardcoded or default values would silently
        validate the wrong credentials and store the user-supplied ones.  This
        test pins that the probe positional arguments match the submitted form."""
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ) as mock_probe:
            await flow.async_step_user(_VALID_INPUT)

        mock_probe.assert_awaited_once()
        probe_args = mock_probe.call_args[0]
        assert probe_args[1] == "sk-test", f"probe received wrong api_key: {probe_args[1]!r}"
        assert probe_args[2] == "https://proxy.example.com", (
            f"probe received wrong base_url: {probe_args[2]!r}"
        )

    @pytest.mark.asyncio
    async def test_unique_id_set_to_base_url(self) -> None:
        """async_set_unique_id must be called with the base_url so HA prevents
        duplicate config entries pointing at the same proxy endpoint.

        Without this call, a user could add the same proxy twice, causing two
        sets of entities to poll the same /v1/models endpoint and fill the
        Devices & Services page with duplicates."""
        flow = _make_flow()
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_user(_VALID_INPUT)

        flow.async_set_unique_id.assert_awaited_once_with("https://proxy.example.com")

    @pytest.mark.asyncio
    async def test_api_key_whitespace_stripped_in_flow(self) -> None:
        """An api_key submitted with surrounding whitespace must be stripped
        before being stored — guards the v0.2.46 fix that prevents a pasted
        key with leading/trailing spaces from producing a cryptic auth error."""
        flow = _make_flow()
        padded_input = {**_VALID_INPUT, CONF_API_KEY: "  sk-test  "}
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_user(padded_input)
        call_kwargs = flow.async_create_entry.call_args[1]
        assert call_kwargs["data"][CONF_API_KEY] == "sk-test"

    @pytest.mark.asyncio
    async def test_probe_receives_stripped_api_key(self) -> None:
        """_probe_proxy must receive the STRIPPED api_key, not the raw padded
        string the user submitted.

        The existing test_api_key_whitespace_stripped_in_flow only verifies
        the STORED key is stripped; without this companion test a refactor that
        moves the strip() call to happen after the probe would silently send the
        padded key to the proxy — potentially producing an 'invalid_auth' error
        on a key that would otherwise succeed, with no indication that whitespace
        was the cause."""
        flow = _make_flow()
        padded_input = {**_VALID_INPUT, CONF_API_KEY: "  sk-padded  "}
        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ) as mock_probe:
            await flow.async_step_user(padded_input)

        probe_args = mock_probe.call_args[0]  # positional args
        assert probe_args[1] == "sk-padded", (
            f"probe received {probe_args[1]!r} instead of 'sk-padded' — "
            "api_key whitespace stripping must happen BEFORE the probe call, not after"
        )
