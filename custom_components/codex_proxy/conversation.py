"""Conversation entity for the Codex Token Pool integration.

Near-empty subclass of upstream
``homeassistant.components.openai_conversation.conversation.OpenAIConversationEntity``.
HA Core ships improvements (new event types, refusal handling, structured
output, reasoning summaries) directly into our conversation entity with no
code change needed here.

The only override is ``device_info``, which anchors the device under our
DOMAIN instead of upstream's, so HA's *Devices & Services* attributes the
entity to Codex Token Pool, not OpenAI Conversation.
"""
from __future__ import annotations

from homeassistant.components.openai_conversation.const import (
    CONF_CHAT_MODEL as UPSTREAM_CONF_CHAT_MODEL,
)
from homeassistant.components.openai_conversation.conversation import (
    OpenAIConversationEntity,
)
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DEFAULT_MODEL,
    SUBENTRY_TYPE_CONVERSATION,
    build_codex_device_info,
)


class CodexConversationEntity(OpenAIConversationEntity):
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
    """Create one conversation entity per ``conversation`` subentry."""
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_CONVERSATION:
            continue
        async_add_entities(
            [CodexConversationEntity(entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )
