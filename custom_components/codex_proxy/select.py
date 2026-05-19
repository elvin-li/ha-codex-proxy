"""Model-select entity for the Codex Token Pool integration.

Exposes one ``SelectEntity`` per LLM-bearing subentry (conversation +
ai_task_data). The dropdown shows all chat-capable models discovered by the
coordinator; selecting one updates the subentry and reloads the config entry
so the conversation / AI-task entity picks up the change immediately.

The entity is **disabled by default** — most users will manage their model
via the config-flow sub-agent settings or the update entity. Enable it
explicitly if you want dashboard-level model switching.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import callback
from homeassistant.components.openai_conversation.const import (
    CONF_CHAT_MODEL as UPSTREAM_CONF_CHAT_MODEL,
)
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
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
    """Create one model-select entity per LLM subentry."""
    coordinator: CodexModelCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    entities = [
        CodexModelSelectEntity(coordinator, entry, subentry)
        for subentry in entry.subentries.values()
        if subentry.subentry_type in LLM_BEARING_SUBENTRY_TYPES
    ]
    async_add_entities(entities)


class CodexModelSelectEntity(
    CoordinatorEntity[CodexModelCoordinator], SelectEntity
):
    """Dropdown for selecting the active chat model on a subentry.

    Options are built from the coordinator's live ``chat_models`` list.
    The current selection is read from ``subentry.data[chat_model_key]``.
    Selecting a new model writes it to the subentry and reloads the entry.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "active_model"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False  # opt-in; keeps dashboards clean

    def __init__(
        self,
        coordinator: CodexModelCoordinator,
        entry: ConfigEntry,
        subentry: ConfigSubentry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._subentry = subentry
        self._attr_unique_id = f"{subentry.subentry_id}_model_select"
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
        )

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def current_option(self) -> str | None:
        """Currently configured model id."""
        return self._subentry.data.get(UPSTREAM_CONF_CHAT_MODEL, DEFAULT_MODEL)

    @property
    def options(self) -> list[str]:
        """All chat-capable model ids from the last coordinator poll.

        The current model is always included — even if the coordinator hasn't
        returned it yet — so the entity never shows an invalid selection.
        """
        seen: set[str] = set()
        result: list[str] = []

        for m in self.coordinator.chat_models:
            mid = m["id"]
            if mid not in seen:
                seen.add(mid)
                result.append(mid)

        current = self.current_option
        if current and current not in seen:
            result.insert(0, current)

        if not result:
            result.append(DEFAULT_MODEL)

        return result

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------

    async def async_select_option(self, option: str) -> None:
        """Update the subentry's model and reload the config entry."""
        if option == self.current_option:
            return

        new_data = {**self._subentry.data, UPSTREAM_CONF_CHAT_MODEL: option}
        self.hass.config_entries.async_update_subentry(
            self._entry, self._subentry, data=new_data
        )
        _LOGGER.info(
            "Model for subentry '%s' changed from '%s' to '%s'; reloading entry",
            self._subentry.title,
            self.current_option,
            option,
        )
        await self.hass.config_entries.async_reload(self._entry.entry_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Re-read the subentry so current_option reflects external changes.

        If the user reconfigures the subentry via the config flow (which
        doesn't go through this entity), ``self._subentry`` would otherwise
        be stale and ``current_option`` would return the pre-change model.
        """
        live = self._entry.subentries.get(self._subentry.subentry_id)
        if live is not None:
            self._subentry = live
        super()._handle_coordinator_update()
