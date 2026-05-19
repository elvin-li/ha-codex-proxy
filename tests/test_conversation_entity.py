"""Tests for CodexConversationEntity and CodexAITaskEntity.

Verifies that both thin-shim entities:
- Successfully subclass the upstream HA entity (patched to a real class in ha_stubs)
- Override _attr_device_info with the correct identifiers / manufacturer
Runs without a full HA install.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.ha_stubs  # noqa: F401, E402
from custom_components.codex_proxy.ai_task import CodexAITaskEntity  # noqa: E402
from custom_components.codex_proxy.const import DEFAULT_MODEL, DOMAIN  # noqa: E402
from custom_components.codex_proxy.conversation import CodexConversationEntity  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_subentry(
    subentry_id: str = "sub-1",
    title: str = "Test Agent",
    chat_model: str = DEFAULT_MODEL,
) -> MagicMock:
    sub = MagicMock()
    sub.subentry_id = subentry_id
    sub.title = title
    sub.data = {"chat_model": chat_model}
    return sub


def _make_entry(entry_id: str = "entry-1") -> MagicMock:
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.runtime_data = MagicMock()
    return entry


# ---------------------------------------------------------------------------
# CodexConversationEntity
# ---------------------------------------------------------------------------


class TestCodexConversationEntity:
    def test_device_info_identifiers_use_domain_and_subentry_id(self) -> None:
        entry = _make_entry()
        sub = _make_subentry("sub-conv")
        entity = CodexConversationEntity(entry, sub)
        assert (DOMAIN, "sub-conv") in entity._attr_device_info["identifiers"]

    def test_device_info_name_matches_subentry_title(self) -> None:
        entry = _make_entry()
        sub = _make_subentry(title="Codex 对话")
        entity = CodexConversationEntity(entry, sub)
        assert entity._attr_device_info["name"] == "Codex 对话"

    def test_device_info_manufacturer_set(self) -> None:
        entity = CodexConversationEntity(_make_entry(), _make_subentry())
        assert entity._attr_device_info["manufacturer"] == "OpenAI Codex Token Pool"

    def test_device_info_model_uses_chat_model(self) -> None:
        entry = _make_entry()
        sub = _make_subentry(chat_model="gpt-5.6")
        entity = CodexConversationEntity(entry, sub)
        assert entity._attr_device_info["model"] == "gpt-5.6"

    def test_device_info_sw_version_present(self) -> None:
        """sw_version must be included after entity_utils was updated to expose it."""
        entity = CodexConversationEntity(_make_entry(), _make_subentry())
        assert "sw_version" in entity._attr_device_info

    def test_device_info_entry_type_is_service(self) -> None:
        """entry_type must be DeviceEntryType.SERVICE so HA categorises the
        conversation subentry as a cloud service rather than a physical device.

        build_codex_device_info already tests this at the builder level
        (TestBuildCodexDeviceInfo.test_entry_type_is_service); this test pins
        the invariant at the entity level so a refactor that swaps in a
        different builder (one that omits entry_type) is caught here and not
        just discovered when HA shows an area-picker for a network proxy."""
        from homeassistant.helpers import device_registry as dr  # type: ignore[attr-defined]

        entity = CodexConversationEntity(_make_entry(), _make_subentry())
        assert entity._attr_device_info.get("entry_type") is dr.DeviceEntryType.SERVICE


# ---------------------------------------------------------------------------
# CodexAITaskEntity
# ---------------------------------------------------------------------------


class TestCodexAITaskEntity:
    def test_device_info_identifiers_use_domain_and_subentry_id(self) -> None:
        entry = _make_entry()
        sub = _make_subentry("sub-task")
        entity = CodexAITaskEntity(entry, sub)
        assert (DOMAIN, "sub-task") in entity._attr_device_info["identifiers"]

    def test_device_info_name_matches_subentry_title(self) -> None:
        entry = _make_entry()
        sub = _make_subentry(title="Codex AI Task")
        entity = CodexAITaskEntity(entry, sub)
        assert entity._attr_device_info["name"] == "Codex AI Task"

    def test_device_info_manufacturer_set(self) -> None:
        entity = CodexAITaskEntity(_make_entry(), _make_subentry())
        assert entity._attr_device_info["manufacturer"] == "OpenAI Codex Token Pool"

    def test_device_info_sw_version_present(self) -> None:
        """sw_version must be included (parity with conversation entity)."""
        entity = CodexAITaskEntity(_make_entry(), _make_subentry())
        assert "sw_version" in entity._attr_device_info

    def test_device_info_model_uses_chat_model(self) -> None:
        """device_info['model'] must reflect the subentry's chat_model so HA's
        device card shows which AI model the AI Task agent is using.

        Parity with TestCodexConversationEntity.test_device_info_model_uses_chat_model.
        Both entities call build_codex_device_info with UPSTREAM_CONF_CHAT_MODEL;
        without this test, a refactor that accidentally passed the wrong key for
        the AI Task entity would be caught for Conversation but not for AI Task."""
        entry = _make_entry()
        sub = _make_subentry(chat_model="gpt-5.6")
        entity = CodexAITaskEntity(entry, sub)
        assert entity._attr_device_info["model"] == "gpt-5.6"

    def test_device_info_entry_type_is_service(self) -> None:
        """entry_type must be DeviceEntryType.SERVICE for the AI Task entity.

        Parity with TestCodexConversationEntity.test_device_info_entry_type_is_service —
        both entities use build_codex_device_info which sets entry_type=SERVICE,
        but the entity-level test ensures a builder swap that drops entry_type
        is caught for AI Task independently of the Conversation entity test."""
        from homeassistant.helpers import device_registry as dr  # type: ignore[attr-defined]

        entity = CodexAITaskEntity(_make_entry(), _make_subentry())
        assert entity._attr_device_info.get("entry_type") is dr.DeviceEntryType.SERVICE

    def test_device_info_differs_between_entities(self) -> None:
        entity_a = CodexConversationEntity(_make_entry(), _make_subentry("sub-a"))
        entity_b = CodexAITaskEntity(_make_entry(), _make_subentry("sub-b"))
        assert (
            entity_a._attr_device_info["identifiers"] != entity_b._attr_device_info["identifiers"]
        )
