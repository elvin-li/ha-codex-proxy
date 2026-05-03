"""Conversation entity for the Codex Token Pool integration.

This is intentionally a near-empty subclass of the upstream
`homeassistant.components.openai_conversation.conversation.OpenAIConversationEntity`.
Doing so means every improvement upstream ships — new tool kinds, new event
types, refusal handling, structured output, reasoning summaries — flows into
this integration the moment Home Assistant Core is upgraded, with **no code
change required here**.

The two things we override are:
  * device_info — to claim the device under our DOMAIN, not upstream's.
  * model fallback — default to `gpt-5.5` when the subentry doesn't specify one.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_MODEL, DOMAIN, SUBENTRY_TYPE_CONVERSATION

if TYPE_CHECKING:
    from . import CodexConfigEntry

_LOGGER = logging.getLogger(__name__)


def _import_upstream():
    """Late-import the upstream classes so module load doesn't fail if HA
    Core ever renames them; the error surfaces at setup time with a clear
    message instead of crashing the whole integration registry."""
    from homeassistant.components.openai_conversation.conversation import (
        OpenAIConversationEntity,
    )
    from homeassistant.components.openai_conversation.const import (
        CONF_CHAT_MODEL,
    )

    return OpenAIConversationEntity, CONF_CHAT_MODEL


async def async_setup_entry(
    hass: HomeAssistant,
    entry: "CodexConfigEntry",
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one conversation entity per `conversation` subentry."""
    OpenAIConversationEntity, CONF_CHAT_MODEL = _import_upstream()

    class CodexConversationEntity(OpenAIConversationEntity):
        """Drop-in subclass that re-anchors device_info onto our DOMAIN."""

        def __init__(
            self, entry: ConfigEntry, subentry: ConfigSubentry
        ) -> None:
            super().__init__(entry, subentry)
            self._attr_device_info = dr.DeviceInfo(
                identifiers={(DOMAIN, subentry.subentry_id)},
                name=subentry.title,
                manufacturer="OpenAI Codex Token Pool",
                model=subentry.data.get(CONF_CHAT_MODEL, DEFAULT_MODEL),
                entry_type=dr.DeviceEntryType.SERVICE,
            )

    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_CONVERSATION:
            continue
        async_add_entities(
            [CodexConversationEntity(entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )
