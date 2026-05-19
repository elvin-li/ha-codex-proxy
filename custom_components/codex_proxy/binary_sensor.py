"""Proxy-reachable binary sensor for the Codex Token Pool integration.

Exposes one ``BinarySensorEntity`` per config entry that is ``ON`` when the
most recent ``/v1/models`` poll succeeded and ``OFF`` when it failed.  This
makes it trivial to build HA automations or dashboard badges that alert when
the reverse proxy is unreachable.

The entity is **enabled by default** because proxy reachability is a primary
health signal users want to monitor.

``extra_state_attributes`` exposes ``last_checked`` (ISO-8601 string) for
automations and template sensors that need the exact timestamp of the last
successful poll.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import CodexModelCoordinator
from .entity_utils import build_codex_entry_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: CodexModelCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([CodexProxyReachableSensor(coordinator, entry)])


class CodexProxyReachableSensor(CoordinatorEntity[CodexModelCoordinator], BinarySensorEntity):
    """``ON`` while the proxy's /v1/models endpoint is responding successfully."""

    _attr_has_entity_name = True
    _attr_translation_key = "proxy_reachable"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: CodexModelCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_proxy_reachable"
        self._attr_device_info = build_codex_entry_device_info(entry)

    @property
    def is_on(self) -> bool | None:
        """Return True when the last coordinator poll succeeded.

        Returns ``None`` (unknown state) until the first **successful** poll
        sets ``last_update_success_time``, so the entity never prematurely
        reports "connected" while HA is still starting up.  If the proxy is
        persistently unreachable, ``last_update_success_time`` stays ``None``
        and the state remains unknown until at least one poll succeeds.
        """
        if self.coordinator.last_update_success_time is None:
            return None  # no successful poll yet — state is unknown
        return bool(self.coordinator.last_update_success)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose last_checked timestamp and latest_model for automations.

        ``last_checked`` is an ISO-8601 string of the most recent successful
        ``/v1/models`` poll.  ``latest_model`` is the newest chat-capable model
        id known to the coordinator — both attributes are absent when the
        coordinator has not yet completed its first successful poll.
        """
        attrs: dict[str, Any] = {}
        t = self.coordinator.last_update_success_time
        if t is not None:
            attrs["last_checked"] = t.isoformat()
        latest = self.coordinator.latest_chat_model_id
        if latest is not None:
            attrs["latest_model"] = latest
        return attrs or None
