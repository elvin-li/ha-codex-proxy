"""Proxy-reachable binary sensor for the Codex Token Pool integration.

Exposes one ``BinarySensorEntity`` per config entry that is ``ON`` when the
most recent ``/v1/models`` poll succeeded and ``OFF`` when it failed.  This
makes it trivial to build HA automations or dashboard badges that alert when
the reverse proxy is unreachable.

The entity is **enabled by default** because proxy reachability is a primary
health signal users want to monitor.

``extra_state_attributes`` exposes three optional attributes:

* ``last_checked`` — ISO-8601 timestamp of the most recent successful
  ``/v1/models`` poll; absent until the first successful poll.
* ``latest_model`` — model id of the newest chat-capable model known to the
  coordinator; absent until the first successful poll.
* ``last_error`` — ``str(last_exception)`` from the coordinator when the
  most recent poll failed; absent when the proxy is reachable.
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
    """Create one proxy-reachable binary sensor for this config entry."""
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
        """Expose last_checked, last_attempt, latest_model, and last_error.

        ``last_checked`` keeps its pre-v0.2.175 meaning ("last *successful*
        poll") for backward compatibility — flipping it to "last attempt"
        in v0.2.175 silently broke any automation that read it as a health
        signal (``{{ as_timestamp(state_attr(..., 'last_checked')) < now() - 21600 }}``
        no longer fired when the proxy went down but kept retrying).
        v0.2.176 reverts that flip and adds a separate ``last_attempt``
        attribute for users who genuinely want the "when did the coordinator
        last try" signal.

        * ``last_checked`` — ISO-8601 of the most recent **successful** poll
          (same semantics as v0.2.169-174).  Absent until the first
          successful poll.
        * ``last_attempt`` — ISO-8601 of the most recent poll *attempt*
          (success or failure).  Lags ``last_checked`` once the proxy
          starts failing — operators comparing the two can tell whether
          the integration is actively retrying or stuck.  Absent until
          the first poll attempt completes.
        * ``latest_model`` — id of the newest chat-capable model known to
          the coordinator; absent until the first successful poll.
        * ``last_error`` — ``str(coordinator.last_exception)`` when the most
          recent poll failed; absent when the proxy is healthy.  Enables
          automations to surface the failure reason via
          ``{{ state_attr('binary_sensor.proxy_reachable', 'last_error') }}``
          without requiring a full diagnostics download.

        Returns ``None`` (no attributes) when none of the four have data yet.
        """
        attrs: dict[str, Any] = {}
        # ``last_checked`` preserves the pre-v0.2.175 semantic — last
        # *successful* poll — so user automations written against earlier
        # versions continue to work after upgrade.  See class docstring.
        success = self.coordinator.last_update_success_time
        if success is not None:
            attrs["last_checked"] = success.isoformat()
        attempt = self.coordinator.last_update_attempt_time
        if attempt is not None:
            attrs["last_attempt"] = attempt.isoformat()
        latest = self.coordinator.latest_chat_model_id
        if latest is not None:
            attrs["latest_model"] = latest
        last_exc = self.coordinator.last_exception
        if last_exc is not None:
            # Expose the error message so automations can surface the reason
            # the proxy went down without requiring HA's diagnostics download.
            attrs["last_error"] = str(last_exc)
        return attrs or None
