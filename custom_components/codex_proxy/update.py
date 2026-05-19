"""Update entity that surfaces newer chat models from the proxy.

When the reverse proxy starts advertising a model newer than the one
currently configured on a `conversation` or `ai_task_data` subentry
(e.g. `gpt-5.6` shows up while we're still on `gpt-5.5`), this entity
becomes "update available" and a one-click install rewrites the
subentry data to the latest model and reloads the config entry.

One update entity per LLM-bearing subentry — both conversation agents
and AI Task entities get tracked.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.openai_conversation.const import (
    CONF_CHAT_MODEL as UPSTREAM_CONF_CHAT_MODEL,
)
from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_COORDINATOR,
    DEFAULT_MODEL,
    DOMAIN,
    LLM_BEARING_SUBENTRY_TYPES,
)
from .coordinator import CodexModelCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one update entity per conversation/ai_task subentry."""
    coordinator: CodexModelCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    for subentry in entry.subentries.values():
        if subentry.subentry_type not in LLM_BEARING_SUBENTRY_TYPES:
            continue
        async_add_entities(
            [CodexModelUpdate(coordinator, entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class CodexModelUpdate(CoordinatorEntity[CodexModelCoordinator], UpdateEntity):
    """Tracks the latest chat model surfaced by the proxy."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_supported_features = UpdateEntityFeature.INSTALL
    _attr_translation_key = "model_update"

    def __init__(
        self,
        coordinator: CodexModelCoordinator,
        entry: ConfigEntry,
        subentry: ConfigSubentry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._subentry = subentry
        self._attr_unique_id = f"{subentry.subentry_id}_model_update"
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
        )

    @property
    def installed_version(self) -> str | None:
        """The chat model currently configured on this subentry.

        Reads ``subentry.data[UPSTREAM_CONF_CHAT_MODEL]`` and falls back to
        ``DEFAULT_MODEL`` when the key is absent (e.g. fresh subentry created
        before the model was explicitly set by the user).
        """
        return self._subentry.data.get(UPSTREAM_CONF_CHAT_MODEL, DEFAULT_MODEL)

    @property
    def latest_version(self) -> str | None:
        """The newest chat model advertised by the proxy, or ``installed_version``.

        Falls back to ``installed_version`` when the coordinator hasn't
        completed its first successful poll yet (``latest_chat_model_id`` is
        ``None``), preventing HA from rendering a spurious "update available"
        badge against a phantom ``None`` version.
        """
        return self.coordinator.latest_chat_model_id or self.installed_version

    @property
    def title(self) -> str | None:
        return "Proxy chat model"

    @property
    def release_summary(self) -> str | None:
        latest = self.coordinator.latest_chat_model_id
        installed = self.installed_version
        if not latest:
            return (
                "Model list not yet available "
                "(first refresh runs within 6 hours; trigger manually via update_entity)."
            )
        if latest == installed:
            return "Already on the latest model from the proxy."
        return (
            f"Proxy has a newer model available: {latest} "
            f"(installed: {installed}). Click Install to switch."
        )

    @property
    def release_url(self) -> str | None:
        # Proxy model IDs are not necessarily OpenAI model IDs, so we cannot
        # construct a meaningful release-notes URL. Return None so the HA
        # update card does not show a broken link.
        return None

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Switch the subentry's model to the requested (or latest) version
        and reload the config entry."""
        target = version or self.coordinator.latest_chat_model_id
        if not target or target == self.installed_version:
            return
        _LOGGER.info(
            "Installing model '%s' on subentry '%s' (was '%s'); reloading entry",
            target,
            self._subentry.title,
            self.installed_version,
        )
        new_data = {**self._subentry.data, UPSTREAM_CONF_CHAT_MODEL: target}
        self.hass.config_entries.async_update_subentry(self._entry, self._subentry, data=new_data)
        await self.hass.config_entries.async_reload(self._entry.entry_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Re-read the subentry so installed_version reflects external changes.

        If the user reconfigures the subentry via the config flow (which
        doesn't go through this entity), ``self._subentry`` would otherwise
        be stale and ``installed_version`` would return the pre-change model.
        """
        live = self._entry.subentries.get(self._subentry.subentry_id)
        if live is not None:
            self._subentry = live
        super()._handle_coordinator_update()
