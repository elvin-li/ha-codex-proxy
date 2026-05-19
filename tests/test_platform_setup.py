"""Integration-level tests for platform async_setup_entry functions.

Uses the shared conftest fixtures (mock_entry, mock_coordinator) to verify
that each platform registers the correct number and type of entities.
Runs without a full HA install.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.ha_stubs  # noqa: F401, E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hass(mock_entry, mock_coordinator):
    """Wire up hass.data so platform setup can look up the coordinator."""
    from custom_components.codex_proxy.const import DATA_COORDINATOR, DOMAIN

    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            mock_entry.entry_id: {DATA_COORDINATOR: mock_coordinator},
        }
    }
    return hass


def _collecting_add_entities():
    """Return an (add_entities callable, result list) pair."""
    added: list = []

    def _add(entities, config_subentry_id: str | None = None):
        added.extend(entities)

    return _add, added


# ---------------------------------------------------------------------------
# binary_sensor platform
# ---------------------------------------------------------------------------


class TestBinarySensorSetup:
    @pytest.mark.asyncio
    async def test_setup_creates_one_entity_per_entry(self, mock_entry, mock_coordinator) -> None:
        from custom_components.codex_proxy.binary_sensor import (
            CodexProxyReachableSensor,
            async_setup_entry,
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert len(added) == 1
        assert isinstance(added[0], CodexProxyReachableSensor)

    @pytest.mark.asyncio
    async def test_entity_unique_id_contains_entry_id(self, mock_entry, mock_coordinator) -> None:
        from custom_components.codex_proxy.binary_sensor import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert mock_entry.entry_id in added[0]._attr_unique_id

    @pytest.mark.asyncio
    async def test_entity_unique_id_exact_format(self, mock_entry, mock_coordinator) -> None:
        """The binary sensor unique_id must be exactly '<entry_id>_proxy_reachable'.

        test_entity_unique_id_contains_entry_id only checks that entry_id is a
        substring — 'prefix_<entry_id>' or '<entry_id>_something_else' both
        pass the ``in`` check.  Pinning the exact format catches a refactor
        that changes the suffix (e.g. to '_reachable' or '_health'), which
        would orphan any automations or dashboard cards that target the old
        entity_id derived from the unique_id."""
        from custom_components.codex_proxy.binary_sensor import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        expected_uid = f"{mock_entry.entry_id}_proxy_reachable"
        assert added[0]._attr_unique_id == expected_uid, (
            f"Expected unique_id {expected_uid!r}, got {added[0]._attr_unique_id!r}"
        )

    @pytest.mark.asyncio
    async def test_binary_sensor_coordinator_reference(
        self, mock_entry, mock_coordinator
    ) -> None:
        """The binary sensor entity must reference the coordinator retrieved
        from hass.data so it can read last_update_success during is_on.

        Parity with TestButtonSetup.test_button_coordinator_reference —
        both entry-level entities are wired to the coordinator at setup time;
        this test pins that the binary sensor's reference is the same object."""
        from custom_components.codex_proxy.binary_sensor import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert added[0].coordinator is mock_coordinator


# ---------------------------------------------------------------------------
# button platform
# ---------------------------------------------------------------------------


class TestButtonSetup:
    @pytest.mark.asyncio
    async def test_setup_creates_one_button_per_entry(self, mock_entry, mock_coordinator) -> None:
        from custom_components.codex_proxy.button import (
            CodexRefreshModelsButton,
            async_setup_entry,
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert len(added) == 1
        assert isinstance(added[0], CodexRefreshModelsButton)

    @pytest.mark.asyncio
    async def test_button_coordinator_reference(self, mock_entry, mock_coordinator) -> None:
        from custom_components.codex_proxy.button import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert added[0]._coordinator is mock_coordinator


# ---------------------------------------------------------------------------
# sensor platform
# ---------------------------------------------------------------------------


class TestSensorSetup:
    @pytest.mark.asyncio
    async def test_setup_creates_two_sensors_per_entry(self, mock_entry, mock_coordinator) -> None:
        from custom_components.codex_proxy.sensor import (
            CodexChatModelCountSensor,
            CodexLastRefreshSensor,
            async_setup_entry,
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert len(added) == 2
        types = {type(e) for e in added}
        assert CodexChatModelCountSensor in types
        assert CodexLastRefreshSensor in types

    @pytest.mark.asyncio
    async def test_sensor_types_exact_set(self, mock_entry, mock_coordinator) -> None:
        """The sensor platform must produce *exactly* one CodexChatModelCountSensor
        and one CodexLastRefreshSensor — no more, no less.

        test_setup_creates_two_sensors_per_entry uses two ``in`` checks which pass
        even if a third unexpected sensor type is accidentally added (e.g. a
        CodexDebugSensor left over from a refactor).  Exact set equality catches
        that before the extra entity pollutes the device registry."""
        from custom_components.codex_proxy.sensor import (
            CodexChatModelCountSensor,
            CodexLastRefreshSensor,
            async_setup_entry,
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        types = {type(e) for e in added}
        expected = {CodexChatModelCountSensor, CodexLastRefreshSensor}
        assert types == expected, (
            f"Expected sensor types {expected}, got {types}. "
            f"Unexpected: {types - expected}"
        )

    @pytest.mark.asyncio
    async def test_sensor_unique_ids_are_distinct(self, mock_entry, mock_coordinator) -> None:
        from custom_components.codex_proxy.sensor import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        uids = [e._attr_unique_id for e in added]
        assert len(set(uids)) == 2

    @pytest.mark.asyncio
    async def test_sensor_unique_ids_exact_format(self, mock_entry, mock_coordinator) -> None:
        """The two sensor unique_ids must be exactly
        '<entry_id>_chat_model_count' and '<entry_id>_last_model_refresh'.

        test_sensor_unique_ids_are_distinct only checks len(set(uids)) == 2 —
        it passes even if the suffix is changed (e.g. '_count' instead of
        '_chat_model_count').  The unique_id is the stable entity-registry key
        in HA; any suffix change silently orphans existing automations and
        dashboard cards that reference the old entity_id.  Pinning the exact
        format catches that before it reaches users."""
        from custom_components.codex_proxy.sensor import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        uids = {e._attr_unique_id for e in added}
        expected = {
            f"{mock_entry.entry_id}_chat_model_count",
            f"{mock_entry.entry_id}_last_model_refresh",
        }
        assert uids == expected, (
            f"Expected sensor unique_ids {expected}, got {uids}. "
            f"Unexpected: {uids - expected}. Missing: {expected - uids}."
        )

    @pytest.mark.asyncio
    async def test_sensor_coordinator_reference(self, mock_entry, mock_coordinator) -> None:
        """Both sensor entities must reference the coordinator from hass.data
        so native_value reads coordinator.chat_models / last_update_success_time.

        Parity with TestButtonSetup.test_button_coordinator_reference —
        all entry-level coordinator entities must be wired at setup time."""
        from custom_components.codex_proxy.sensor import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        for entity in added:
            assert entity.coordinator is mock_coordinator, (
                f"{type(entity).__name__} coordinator is not mock_coordinator"
            )


# ---------------------------------------------------------------------------
# select platform
# ---------------------------------------------------------------------------


class TestSelectSetup:
    @pytest.mark.asyncio
    async def test_setup_creates_one_select_per_llm_subentry(
        self, mock_entry, mock_coordinator
    ) -> None:
        """mock_entry has 1 conversation + 1 ai_task_data subentry → 2 selects."""
        from custom_components.codex_proxy.select import (
            CodexModelSelectEntity,
            async_setup_entry,
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert len(added) == 2
        assert all(isinstance(e, CodexModelSelectEntity) for e in added)

    @pytest.mark.asyncio
    async def test_select_unique_ids_are_distinct(self, mock_entry, mock_coordinator) -> None:
        from custom_components.codex_proxy.select import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        uids = [e._attr_unique_id for e in added]
        assert len(set(uids)) == 2

    @pytest.mark.asyncio
    async def test_non_llm_subentry_skipped(self, mock_entry, mock_coordinator) -> None:
        """A subentry of an unknown type must not produce a select entity."""
        from custom_components.codex_proxy.select import async_setup_entry
        from tests.conftest import _FakeSubentry

        # Inject a third subentry with a non-LLM type
        mock_entry.subentries["sub-other-1"] = _FakeSubentry(
            subentry_id="sub-other-1",
            subentry_type="light",  # not a LLM-bearing type
            title="Not an LLM",
            data={},
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        # Still only 2 (the LLM subentries), not 3
        assert len(added) == 2

    @pytest.mark.asyncio
    async def test_select_config_subentry_id_passed(self, mock_entry, mock_coordinator) -> None:
        """async_add_entities must be called with the correct config_subentry_id
        for each select entity so HA auto-removes it when the subentry is deleted."""
        from custom_components.codex_proxy.select import async_setup_entry

        calls: list[str | None] = []

        def _add(entities, config_subentry_id: str | None = None) -> None:
            calls.append(config_subentry_id)

        hass = _make_hass(mock_entry, mock_coordinator)
        await async_setup_entry(hass, mock_entry, _add)

        # Each of the 2 LLM subentries must have been registered with its own id
        assert None not in calls, "config_subentry_id must never be None for select"
        assert set(calls) == {"sub-conv-1", "sub-task-1"}


# ---------------------------------------------------------------------------
# update platform
# ---------------------------------------------------------------------------


class TestUpdateSetup:
    @pytest.mark.asyncio
    async def test_setup_creates_one_update_per_llm_subentry(
        self, mock_entry, mock_coordinator
    ) -> None:
        from custom_components.codex_proxy.update import (
            CodexModelUpdate,
            async_setup_entry,
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert len(added) == 2
        assert all(isinstance(e, CodexModelUpdate) for e in added)

    @pytest.mark.asyncio
    async def test_update_unique_ids_are_distinct(self, mock_entry, mock_coordinator) -> None:
        from custom_components.codex_proxy.update import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        uids = [e._attr_unique_id for e in added]
        assert len(set(uids)) == 2

    @pytest.mark.asyncio
    async def test_non_llm_subentry_skipped(self, mock_entry, mock_coordinator) -> None:
        """A subentry of an unknown type must not produce an update entity."""
        from custom_components.codex_proxy.update import async_setup_entry
        from tests.conftest import _FakeSubentry

        mock_entry.subentries["sub-other-2"] = _FakeSubentry(
            subentry_id="sub-other-2",
            subentry_type="switch",  # not a LLM-bearing type
            title="Not an LLM",
            data={},
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert len(added) == 2

    @pytest.mark.asyncio
    async def test_update_config_subentry_id_passed(self, mock_entry, mock_coordinator) -> None:
        """async_add_entities must be called with the correct config_subentry_id
        for each update entity so HA auto-removes it when the subentry is deleted."""
        from custom_components.codex_proxy.update import async_setup_entry

        calls: list[str | None] = []

        def _add(entities, config_subentry_id: str | None = None) -> None:
            calls.append(config_subentry_id)

        hass = _make_hass(mock_entry, mock_coordinator)
        await async_setup_entry(hass, mock_entry, _add)

        assert None not in calls, "config_subentry_id must never be None for update"
        assert set(calls) == {"sub-conv-1", "sub-task-1"}


# ---------------------------------------------------------------------------
# conversation platform
# ---------------------------------------------------------------------------


class TestConversationSetup:
    @pytest.mark.asyncio
    async def test_setup_creates_one_entity_per_conversation_subentry(
        self, mock_entry, mock_coordinator
    ) -> None:
        """mock_entry has exactly one 'conversation' subentry → 1 entity."""
        from custom_components.codex_proxy.conversation import (
            CodexConversationEntity,
            async_setup_entry,
        )

        add, added = _collecting_add_entities()
        await async_setup_entry(MagicMock(), mock_entry, add)

        assert len(added) == 1
        assert isinstance(added[0], CodexConversationEntity)

    @pytest.mark.asyncio
    async def test_setup_skips_non_conversation_subentries(
        self, mock_entry, mock_coordinator
    ) -> None:
        """The ai_task_data subentry must NOT produce a conversation entity."""
        from custom_components.codex_proxy.conversation import async_setup_entry

        add, added = _collecting_add_entities()
        await async_setup_entry(MagicMock(), mock_entry, add)

        # Only the conversation subentry, not the ai_task one
        assert len(added) == 1

    @pytest.mark.asyncio
    async def test_setup_passes_config_subentry_id(self, mock_entry, mock_coordinator) -> None:
        """async_add_entities must be called with config_subentry_id kwarg."""
        from custom_components.codex_proxy.conversation import async_setup_entry

        calls: list = []

        def _add(entities, config_subentry_id: str | None = None):
            calls.append(config_subentry_id)

        await async_setup_entry(MagicMock(), mock_entry, _add)

        assert calls[0] == "sub-conv-1"


# ---------------------------------------------------------------------------
# ai_task platform
# ---------------------------------------------------------------------------


class TestAITaskSetup:
    @pytest.mark.asyncio
    async def test_setup_creates_one_entity_per_ai_task_subentry(
        self, mock_entry, mock_coordinator
    ) -> None:
        """mock_entry has exactly one 'ai_task_data' subentry → 1 entity."""
        from custom_components.codex_proxy.ai_task import (
            CodexAITaskEntity,
            async_setup_entry,
        )

        add, added = _collecting_add_entities()
        await async_setup_entry(MagicMock(), mock_entry, add)

        assert len(added) == 1
        assert isinstance(added[0], CodexAITaskEntity)

    @pytest.mark.asyncio
    async def test_setup_skips_non_ai_task_subentries(self, mock_entry, mock_coordinator) -> None:
        """The conversation subentry must NOT produce an ai_task entity."""
        from custom_components.codex_proxy.ai_task import async_setup_entry

        add, added = _collecting_add_entities()
        await async_setup_entry(MagicMock(), mock_entry, add)

        assert len(added) == 1

    @pytest.mark.asyncio
    async def test_setup_passes_config_subentry_id(self, mock_entry, mock_coordinator) -> None:
        from custom_components.codex_proxy.ai_task import async_setup_entry

        calls: list = []

        def _add(entities, config_subentry_id: str | None = None):
            calls.append(config_subentry_id)

        await async_setup_entry(MagicMock(), mock_entry, _add)

        assert calls[0] == "sub-task-1"
