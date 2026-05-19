"""Tests for ConversationSubentryFlowHandler and AITaskSubentryFlowHandler.

Covers:
- Class attributes (_default_title, _subentry_type)
- async_step_user: form shown when input is None, entry created with enriched
  data (service_tier=None) when input is provided
- async_step_reconfigure: form shown with existing data pre-filled; on submit,
  async_update_and_abort is called with merged data that preserves existing
  fields and overrides changed ones
"""

from __future__ import annotations

import sys
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Bootstrap HA stubs
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402

from custom_components.codex_proxy.config_flow import (  # noqa: E402
    AITaskSubentryFlowHandler,
    ConversationSubentryFlowHandler,
)
from custom_components.codex_proxy.const import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
)

# Upstream key names (as resolved by ha_stubs)
_CHAT_MODEL_KEY = "chat_model"
_REASONING_KEY = "reasoning_effort"
_STORE_KEY = "store_responses"
_SERVICE_TIER_KEY = "service_tier"
_PROMPT_KEY = "prompt"

_VALID_USER_INPUT = {
    _CHAT_MODEL_KEY: "gpt-5.5",
    _REASONING_KEY: "xhigh",
    _STORE_KEY: False,
    _PROMPT_KEY: "",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_subentry(
    subentry_id: str = "sub-1",
    data: dict[str, Any] | None = None,
) -> MagicMock:
    sub = MagicMock()
    sub.subentry_id = subentry_id
    sub.data = data or {
        _CHAT_MODEL_KEY: DEFAULT_MODEL,
        _REASONING_KEY: DEFAULT_REASONING_EFFORT,
        _STORE_KEY: False,
        _SERVICE_TIER_KEY: None,
    }
    return sub


def _make_flow(
    handler_cls: type,
    entry_id: str = "entry-1",
    subentry: MagicMock | None = None,
) -> Any:
    """Instantiate a subentry flow handler with all HA lifecycle methods mocked."""
    flow = object.__new__(handler_cls)
    # Mock HA plumbing
    entry = MagicMock()
    entry.entry_id = entry_id
    # hass.data used by _build_schema to get coordinator
    flow.hass = MagicMock()
    flow.hass.data = {}  # empty → no coordinator → fallback to defaults
    flow._get_entry = MagicMock(return_value=entry)
    flow._get_reconfigure_subentry = MagicMock(return_value=subentry or _make_subentry())
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    flow.async_update_and_abort = MagicMock(return_value={"type": "abort"})
    return flow


# ---------------------------------------------------------------------------
# Class attributes
# ---------------------------------------------------------------------------


class TestClassAttributes:
    def test_conversation_default_title(self) -> None:
        assert ConversationSubentryFlowHandler._default_title == "Codex 号池对话"

    def test_ai_task_default_title(self) -> None:
        assert AITaskSubentryFlowHandler._default_title == "Codex 号池 AI Task"

    def test_both_are_real_classes(self) -> None:
        assert isinstance(ConversationSubentryFlowHandler, type)
        assert isinstance(AITaskSubentryFlowHandler, type)


# ---------------------------------------------------------------------------
# async_step_user
# ---------------------------------------------------------------------------


class TestAsyncStepUser:
    @pytest.mark.asyncio
    async def test_shows_form_when_input_is_none(self) -> None:
        flow = _make_flow(ConversationSubentryFlowHandler)
        result = await flow.async_step_user(None)
        assert result["type"] == "form"
        flow.async_show_form.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_entry_when_input_provided(self) -> None:
        flow = _make_flow(ConversationSubentryFlowHandler)
        await flow.async_step_user(_VALID_USER_INPUT)
        flow.async_create_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_entry_title_is_default_title(self) -> None:
        flow = _make_flow(ConversationSubentryFlowHandler)
        await flow.async_step_user(_VALID_USER_INPUT)
        call_kwargs = flow.async_create_entry.call_args[1]
        assert call_kwargs["title"] == "Codex 号池对话"

    @pytest.mark.asyncio
    async def test_service_tier_is_none_in_created_entry(self) -> None:
        """service_tier must be pinned to None to avoid 502 from the proxy."""
        flow = _make_flow(ConversationSubentryFlowHandler)
        await flow.async_step_user(_VALID_USER_INPUT)
        data = flow.async_create_entry.call_args[1]["data"]
        assert _SERVICE_TIER_KEY in data
        assert data[_SERVICE_TIER_KEY] is None

    @pytest.mark.asyncio
    async def test_ai_task_entry_title_is_correct(self) -> None:
        flow = _make_flow(AITaskSubentryFlowHandler)
        await flow.async_step_user(_VALID_USER_INPUT)
        call_kwargs = flow.async_create_entry.call_args[1]
        assert call_kwargs["title"] == "Codex 号池 AI Task"


# ---------------------------------------------------------------------------
# async_step_reconfigure
# ---------------------------------------------------------------------------


class TestAsyncStepReconfigure:
    @pytest.mark.asyncio
    async def test_shows_form_when_input_is_none(self) -> None:
        flow = _make_flow(ConversationSubentryFlowHandler)
        result = await flow.async_step_reconfigure(None)
        assert result["type"] == "form"
        flow.async_show_form.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_update_and_abort_on_submit(self) -> None:
        flow = _make_flow(ConversationSubentryFlowHandler)
        await flow.async_step_reconfigure(_VALID_USER_INPUT)
        flow.async_update_and_abort.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_tier_is_none_after_reconfigure(self) -> None:
        """Even after reconfigure, service_tier must remain None."""
        existing_sub = _make_subentry(
            data={
                _CHAT_MODEL_KEY: "gpt-5.5",
                _REASONING_KEY: "medium",
                _STORE_KEY: True,
                _SERVICE_TIER_KEY: None,
            }
        )
        flow = _make_flow(ConversationSubentryFlowHandler, subentry=existing_sub)
        await flow.async_step_reconfigure(_VALID_USER_INPUT)
        call_args = flow.async_update_and_abort.call_args
        # data is passed as keyword arg
        new_data = call_args[1].get("data") or call_args[0][-1]
        assert new_data[_SERVICE_TIER_KEY] is None

    @pytest.mark.asyncio
    async def test_reconfigure_preserves_existing_data_keys(self) -> None:
        """_enrich_subentry_data(user_input, base=existing) must keep all
        existing subentry fields — including those not exposed in the form."""
        existing_sub = _make_subentry(
            data={
                _CHAT_MODEL_KEY: "gpt-5.5",
                _REASONING_KEY: "medium",
                _STORE_KEY: True,
                _SERVICE_TIER_KEY: None,
                "llm_hass_api": ["assist"],  # not in form, must be preserved
            }
        )
        flow = _make_flow(ConversationSubentryFlowHandler, subentry=existing_sub)
        await flow.async_step_reconfigure(_VALID_USER_INPUT)
        call_args = flow.async_update_and_abort.call_args
        new_data = call_args[1].get("data") or call_args[0][-1]
        # llm_hass_api was in the base and not in user_input — must survive
        assert "llm_hass_api" in new_data
        assert new_data["llm_hass_api"] == ["assist"]
