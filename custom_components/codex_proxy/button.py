"""Refresh-models button entity for the Codex Token Pool integration.

One button per config entry. Pressing it triggers an immediate coordinator
refresh of ``/v1/models`` outside the normal 6-hour schedule, so the model
dropdown and update entity reflect the proxy's current catalogue without
having to wait for the next automatic poll.

The entity is **enabled by default** because manual refresh is a first-class
troubleshooting action (the README's "立刻刷新" tip previously required
navigating to Developer Tools → Services).
"""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import CodexModelCoordinator
from .entity_utils import build_codex_entry_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: CodexModelCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    async_add_entities([CodexRefreshModelsButton(coordinator, entry)])


class CodexRefreshModelsButton(ButtonEntity):
    """Button that forces an immediate /v1/models refresh."""

    _attr_has_entity_name = True
    _attr_translation_key = "refresh_models"
    _attr_device_class = ButtonDeviceClass.UPDATE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: CodexModelCoordinator,
        entry: ConfigEntry,
    ) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_refresh_models"
        self._attr_device_info = build_codex_entry_device_info(entry)

    async def async_press(self) -> None:
        """Trigger an out-of-schedule model list refresh."""
        _LOGGER.debug("Manual /v1/models refresh requested")
        await self._coordinator.async_request_refresh()
