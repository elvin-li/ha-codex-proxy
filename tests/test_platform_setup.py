"""Integration-level tests for platform async_setup_entry functions.

Uses the shared conftest fixtures (mock_entry, mock_coordinator) to verify
that each platform registers the correct number and type of entities.
Runs without a full HA install.
"""
from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock

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
    async def test_setup_creates_one_entity_per_entry(
        self, mock_entry, mock_coordinator
    ) -> None:
        from custom_components.codex_proxy.binary_sensor import (
            async_setup_entry,
            CodexProxyReachableSensor,
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert len(added) == 1
        assert isinstance(added[0], CodexProxyReachableSensor)

    @pytest.mark.asyncio
    async def test_entity_unique_id_contains_entry_id(
        self, mock_entry, mock_coordinator
    ) -> None:
        from custom_components.codex_proxy.binary_sensor import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert mock_entry.entry_id in added[0]._attr_unique_id


# ---------------------------------------------------------------------------
# button platform
# ---------------------------------------------------------------------------


class TestButtonSetup:
    @pytest.mark.asyncio
    async def test_setup_creates_one_button_per_entry(
        self, mock_entry, mock_coordinator
    ) -> None:
        from custom_components.codex_proxy.button import (
            async_setup_entry,
            CodexRefreshModelsButton,
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert len(added) == 1
        assert isinstance(added[0], CodexRefreshModelsButton)

    @pytest.mark.asyncio
    async def test_button_coordinator_reference(
        self, mock_entry, mock_coordinator
    ) -> None:
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
    async def test_setup_creates_two_sensors_per_entry(
        self, mock_entry, mock_coordinator
    ) -> None:
        from custom_components.codex_proxy.sensor import (
            async_setup_entry,
            CodexChatModelCountSensor,
            CodexLastRefreshSensor,
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert len(added) == 2
        types = {type(e) for e in added}
        assert CodexChatModelCountSensor in types
        assert CodexLastRefreshSensor in types

    @pytest.mark.asyncio
    async def test_sensor_unique_ids_are_distinct(
        self, mock_entry, mock_coordinator
    ) -> None:
        from custom_components.codex_proxy.sensor import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        uids = [e._attr_unique_id for e in added]
        assert len(set(uids)) == 2


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
            async_setup_entry,
            CodexModelSelectEntity,
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert len(added) == 2
        assert all(isinstance(e, CodexModelSelectEntity) for e in added)

    @pytest.mark.asyncio
    async def test_select_unique_ids_are_distinct(
        self, mock_entry, mock_coordinator
    ) -> None:
        from custom_components.codex_proxy.select import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        uids = [e._attr_unique_id for e in added]
        assert len(set(uids)) == 2


# ---------------------------------------------------------------------------
# update platform
# ---------------------------------------------------------------------------


class TestUpdateSetup:
    @pytest.mark.asyncio
    async def test_setup_creates_one_update_per_llm_subentry(
        self, mock_entry, mock_coordinator
    ) -> None:
        from custom_components.codex_proxy.update import (
            async_setup_entry,
            CodexModelUpdate,
        )

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        assert len(added) == 2
        assert all(isinstance(e, CodexModelUpdate) for e in added)

    @pytest.mark.asyncio
    async def test_update_unique_ids_are_distinct(
        self, mock_entry, mock_coordinator
    ) -> None:
        from custom_components.codex_proxy.update import async_setup_entry

        hass = _make_hass(mock_entry, mock_coordinator)
        add, added = _collecting_add_entities()
        await async_setup_entry(hass, mock_entry, add)

        uids = [e._attr_unique_id for e in added]
        assert len(set(uids)) == 2


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
            async_setup_entry,
            CodexConversationEntity,
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
    async def test_setup_passes_config_subentry_id(
        self, mock_entry, mock_coordinator
    ) -> None:
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
            async_setup_entry,
            CodexAITaskEntity,
        )

        add, added = _collecting_add_entities()
        await async_setup_entry(MagicMock(), mock_entry, add)

        assert len(added) == 1
        assert isinstance(added[0], CodexAITaskEntity)

    @pytest.mark.asyncio
    async def test_setup_skips_non_ai_task_subentries(
        self, mock_entry, mock_coordinator
    ) -> None:
        """The conversation subentry must NOT produce an ai_task entity."""
        from custom_components.codex_proxy.ai_task import async_setup_entry

        add, added = _collecting_add_entities()
        await async_setup_entry(MagicMock(), mock_entry, add)

        assert len(added) == 1

    @pytest.mark.asyncio
    async def test_setup_passes_config_subentry_id(
        self, mock_entry, mock_coordinator
    ) -> None:
        from custom_components.codex_proxy.ai_task import async_setup_entry

        calls: list = []

        def _add(entities, config_subentry_id: str | None = None):
            calls.append(config_subentry_id)

        await async_setup_entry(MagicMock(), mock_entry, _add)

        assert calls[0] == "sub-task-1"
