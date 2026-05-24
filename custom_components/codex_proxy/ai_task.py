"""AI Task entity for the Codex Token Pool integration.

Subclass of upstream
``homeassistant.components.openai_conversation.ai_task.OpenAITaskEntity``,
so HA Core upgrades to AI Task data generation / image generation flow
into this integration automatically.

Override is just ``device_info`` (anchored under our DOMAIN).
"""
from __future__ import annotations

from homeassistant.components.openai_conversation.ai_task import OpenAITaskEntity
from homeassistant.components.openai_conversation.const import (
    CONF_CHAT_MODEL as UPSTREAM_CONF_CHAT_MODEL,
)
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_MODEL, SUBENTRY_TYPE_AI_TASK, build_codex_device_info


class CodexAITaskEntity(OpenAITaskEntity):
    """Drop-in subclass anchoring device_info onto our DOMAIN."""

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        super().__init__(entry, subentry)
        self._attr_device_info = build_codex_device_info(
            subentry,
            model=subentry.data.get(UPSTREAM_CONF_CHAT_MODEL, DEFAULT_MODEL),
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one AI Task entity per ``ai_task_data`` subentry."""
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_AI_TASK:
            continue
        async_add_entities(
            [CodexAITaskEntity(entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )
