"""AI Task entity for the Codex Token Pool integration.

Subclass of upstream `homeassistant.components.openai_conversation.ai_task.OpenAITaskEntity`
so HA Core upgrades to AI Task data generation / image generation flow into
this integration automatically.

We override `device_info` to anchor under our DOMAIN and that's it.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_MODEL, DOMAIN, SUBENTRY_TYPE_AI_TASK

if TYPE_CHECKING:
    from . import CodexConfigEntry

_LOGGER = logging.getLogger(__name__)


def _import_upstream():
    """Late-import upstream so module load doesn't fail if HA renames."""
    from homeassistant.components.openai_conversation.ai_task import (
        OpenAITaskEntity,
    )
    from homeassistant.components.openai_conversation.const import (
        CONF_CHAT_MODEL,
    )

    return OpenAITaskEntity, CONF_CHAT_MODEL


async def async_setup_entry(
    hass: HomeAssistant,
    entry: "CodexConfigEntry",
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one AI Task entity per ai_task_data subentry."""
    OpenAITaskEntity, CONF_CHAT_MODEL = _import_upstream()

    class CodexAITaskEntity(OpenAITaskEntity):
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
        if subentry.subentry_type != SUBENTRY_TYPE_AI_TASK:
            continue
        async_add_entities(
            [CodexAITaskEntity(entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )
