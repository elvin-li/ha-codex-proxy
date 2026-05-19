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

import os
import sys
from typing import Any
from unittest.mock import MagicMock

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


def _make_coordinator_with_models(model_ids: list[str]) -> MagicMock:
    """Return a coordinator mock whose chat_models list contains the given IDs."""
    coord = MagicMock()
    coord.chat_models = [
        {"id": mid, "created": 0, "owned_by": "", "display_name": mid} for mid in model_ids
    ]
    return coord


def _make_flow(
    handler_cls: type,
    entry_id: str = "entry-1",
    subentry: MagicMock | None = None,
    coordinator: MagicMock | None = None,
) -> Any:
    """Instantiate a subentry flow handler with all HA lifecycle methods mocked.

    Pass *coordinator* to simulate a live coordinator in hass.data so that
    _build_schema exercises the coordinator-populated model dropdown path.
    """
    from custom_components.codex_proxy.const import DATA_COORDINATOR, DOMAIN

    flow = object.__new__(handler_cls)
    # Mock HA plumbing
    entry = MagicMock()
    entry.entry_id = entry_id
    # hass.data used by _build_schema to get coordinator
    flow.hass = MagicMock()
    if coordinator is not None:
        flow.hass.data = {DOMAIN: {entry_id: {DATA_COORDINATOR: coordinator}}}
    else:
        flow.hass.data = {}  # empty → no coordinator → fallback to defaults
    flow._get_entry = MagicMock(return_value=entry)
    flow._get_reconfigure_subentry = MagicMock(return_value=subentry or _make_subentry())
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    flow.async_update_and_abort = MagicMock(return_value={"type": "abort"})
    return flow


# ---------------------------------------------------------------------------
# _build_schema with live coordinator
# ---------------------------------------------------------------------------


class TestBuildSchemaWithCoordinator:
    @pytest.mark.asyncio
    async def test_form_shown_when_coordinator_has_models(self) -> None:
        """_build_schema uses coordinator.chat_models when the coordinator is
        present in hass.data — smoke test verifying no crash and form is shown."""
        coord = _make_coordinator_with_models(["gpt-5.5", "gpt-5.6"])
        flow = _make_flow(ConversationSubentryFlowHandler, coordinator=coord)

        result = await flow.async_step_user(None)

        assert result["type"] == "form"
        flow.async_show_form.assert_called_once()

    @pytest.mark.asyncio
    async def test_schema_options_include_coordinator_models(self) -> None:
        """The data_schema passed to async_show_form must include the model IDs
        supplied by the coordinator (verified via _model_select_options directly
        to avoid introspecting voluptuous internals)."""
        from custom_components.codex_proxy.config_flow import _model_select_options

        coord = _make_coordinator_with_models(["gpt-5.5", "gpt-5.6"])
        options = _model_select_options(coord, None)
        option_values = [o["value"] for o in options]

        assert "gpt-5.5" in option_values
        assert "gpt-5.6" in option_values

    def test_coordinator_model_options_exact_list(self) -> None:
        """_model_select_options must return exactly the coordinator's models in
        coordinator order — no extras, no duplicates.

        test_coordinator_model_options uses two ``in`` checks which pass even if
        option_values contains a spurious DEFAULT_MODEL prepend or a duplicate
        (e.g. from a buggy dedup branch).  Exact list equality here verifies the
        happy-path output is clean."""
        from custom_components.codex_proxy.config_flow import _model_select_options

        coord = _make_coordinator_with_models(["gpt-5.5", "gpt-5.6"])
        options = _model_select_options(coord, None)
        option_values = [o["value"] for o in options]
        assert option_values == ["gpt-5.5", "gpt-5.6"], (
            f"Expected exactly ['gpt-5.5', 'gpt-5.6'] in coordinator order, "
            f"got {option_values!r}"
        )

    @pytest.mark.asyncio
    async def test_empty_coordinator_falls_back_to_default(self) -> None:
        """When the coordinator has no chat models, the dropdown falls back to
        the DEFAULT_MODEL so the form is never empty."""
        coord = _make_coordinator_with_models([])
        flow = _make_flow(ConversationSubentryFlowHandler, coordinator=coord)

        result = await flow.async_step_user(None)

        # Form should still be shown (not crash)
        assert result["type"] == "form"


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
    async def test_llm_hass_api_defaults_to_empty_list(self) -> None:
        """llm_hass_api must default to [] so HA Assist is opt-in, not opt-out."""
        from custom_components.codex_proxy.config_flow import _upstream_keys

        keys = _upstream_keys()
        flow = _make_flow(ConversationSubentryFlowHandler)
        await flow.async_step_user(_VALID_USER_INPUT)
        data = flow.async_create_entry.call_args[1]["data"]
        assert data.get(keys.get("llm_hass_api", "llm_hass_api"), []) == []

    @pytest.mark.asyncio
    async def test_ai_task_entry_title_is_correct(self) -> None:
        flow = _make_flow(AITaskSubentryFlowHandler)
        await flow.async_step_user(_VALID_USER_INPUT)
        call_kwargs = flow.async_create_entry.call_args[1]
        assert call_kwargs["title"] == "Codex 号池 AI Task"

    @pytest.mark.asyncio
    async def test_chat_model_stored_in_entry_data(self) -> None:
        """The user-selected model must appear in the created subentry data.

        Tests for service_tier and llm_hass_api confirm the enrichment
        plumbing, but the primary purpose of the subentry flow is model
        selection.  Without this test a refactor that accidentally dropped
        the chat_model key from the enrichment dict would go undetected
        while all other assertions still passed."""
        flow = _make_flow(ConversationSubentryFlowHandler)
        await flow.async_step_user(_VALID_USER_INPUT)
        data = flow.async_create_entry.call_args[1]["data"]
        # _VALID_USER_INPUT has _CHAT_MODEL_KEY: "gpt-5.5"
        assert data.get(_CHAT_MODEL_KEY) == "gpt-5.5", (
            f"chat_model key {_CHAT_MODEL_KEY!r} missing or wrong in created "
            f"entry data: {data!r}"
        )


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
    async def test_update_and_abort_data_is_keyword_arg(self) -> None:
        """async_update_and_abort must be called with ``data=`` as a keyword
        argument.

        Three tests in this class extract the data dict via an OR fallback:
        ``call_args[1].get("data") or call_args[0][-1]`` — they pass whether
        data arrives as a keyword or the last positional arg.  If the
        implementation changes to positional-only, those tests still pass while
        the HA subentry API (which expects a keyword) may reject the call.

        This test pins the keyword calling convention directly, mirroring the
        pattern used in test_select.py
        (test_update_subentry_data_passed_as_keyword, v0.2.121)."""
        flow = _make_flow(ConversationSubentryFlowHandler)
        await flow.async_step_reconfigure(_VALID_USER_INPUT)
        call_args = flow.async_update_and_abort.call_args
        assert "data" in call_args.kwargs, (
            f"async_update_and_abort must be called with data= as a keyword arg; "
            f"got kwargs={call_args.kwargs!r}, args={call_args.args!r}"
        )

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
    async def test_chat_model_updated_after_reconfigure(self) -> None:
        """The reconfigured model must overwrite the old value in the subentry data.

        The existing test_reconfigure_preserves_existing_data_keys verifies that
        *unlisted* keys (e.g. llm_hass_api) survive the update; this test
        verifies the opposite: that the *changed* primary field (chat_model) is
        actually updated rather than silently preserved from the old subentry."""
        existing_sub = _make_subentry(
            data={
                _CHAT_MODEL_KEY: "gpt-5.5",  # old model
                _SERVICE_TIER_KEY: None,
            }
        )
        # Submit reconfigure form choosing the new model "gpt-5.6"
        new_input = {**_VALID_USER_INPUT, _CHAT_MODEL_KEY: "gpt-5.6"}
        flow = _make_flow(ConversationSubentryFlowHandler, subentry=existing_sub)
        await flow.async_step_reconfigure(new_input)
        call_args = flow.async_update_and_abort.call_args
        new_data = call_args[1].get("data") or call_args[0][-1]
        assert new_data.get(_CHAT_MODEL_KEY) == "gpt-5.6", (
            f"chat_model was not updated after reconfigure — got {new_data.get(_CHAT_MODEL_KEY)!r}"
        )

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


# ---------------------------------------------------------------------------
# AITaskSubentryFlowHandler — reconfigure parity smoke test
# ---------------------------------------------------------------------------


class TestAITaskReconfigure:
    @pytest.mark.asyncio
    async def test_shows_form_when_input_is_none(self) -> None:
        """AITaskSubentryFlowHandler.async_step_reconfigure shows a form (smoke test
        verifying parity with ConversationSubentryFlowHandler via shared base class)."""
        flow = _make_flow(AITaskSubentryFlowHandler)
        result = await flow.async_step_reconfigure(None)
        assert result["type"] == "form"
        flow.async_show_form.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_and_abort_called_on_submit(self) -> None:
        """Submitting the AI Task reconfigure form calls async_update_and_abort."""
        flow = _make_flow(AITaskSubentryFlowHandler)
        await flow.async_step_reconfigure(_VALID_USER_INPUT)
        flow.async_update_and_abort.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_tier_none_after_ai_task_reconfigure(self) -> None:
        """service_tier must remain None after AI Task reconfigure (not 'auto')."""
        flow = _make_flow(AITaskSubentryFlowHandler)
        await flow.async_step_reconfigure(_VALID_USER_INPUT)
        call_args = flow.async_update_and_abort.call_args
        new_data = call_args[1].get("data") or call_args[0][-1]
        assert new_data[_SERVICE_TIER_KEY] is None
