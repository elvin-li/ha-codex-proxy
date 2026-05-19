"""Diagnostic sensor entities for the Codex Token Pool integration.

Exposes two sensors per config entry:
* **Chat model count** — number of chat-capable models currently returned by the
  proxy's /v1/models endpoint.
* **Last model refresh** — timestamp of the most recent successful coordinator poll.

Both entities are disabled by default so they don't clutter dashboards unless
the user explicitly enables them.
"""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import CodexModelCoordinator
from .entity_utils import build_codex_entry_device_info

_CHAT_MODEL_COUNT = SensorEntityDescription(
    key="chat_model_count",
    translation_key="chat_model_count",
    icon="mdi:format-list-numbered",
    state_class=SensorStateClass.MEASUREMENT,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
)

_LAST_REFRESH = SensorEntityDescription(
    key="last_model_refresh",
    translation_key="last_model_refresh",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the chat-model-count and last-refresh sensors for this entry."""
    coordinator: CodexModelCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            CodexChatModelCountSensor(coordinator, entry),
            CodexLastRefreshSensor(coordinator, entry),
        ]
    )


class _CodexSensorBase(CoordinatorEntity[CodexModelCoordinator], SensorEntity):
    """Base class for Codex proxy diagnostic sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CodexModelCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = build_codex_entry_device_info(entry)


class CodexChatModelCountSensor(_CodexSensorBase):
    """Number of chat-capable models currently visible on the proxy."""

    def __init__(self, coordinator: CodexModelCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, _CHAT_MODEL_COUNT)

    @property
    def native_value(self) -> int:
        """Count of chat-capable models from the last successful /v1/models poll.

        Returns 0 when the coordinator has not yet completed its first poll or
        when the proxy only returns image-generation models.
        """
        return len(self.coordinator.chat_models)


class CodexLastRefreshSensor(_CodexSensorBase):
    """Timestamp of the most recent successful /v1/models refresh."""

    def __init__(self, coordinator: CodexModelCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, _LAST_REFRESH)

    @property
    def native_value(self) -> datetime | None:
        """Datetime of the most recent successful /v1/models poll, or ``None``.

        Returns ``None`` until the first successful poll completes so HA
        displays "unknown" rather than a misleading epoch timestamp.
        """
        return self.coordinator.last_update_success_time
