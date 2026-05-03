"""Update entity that surfaces newer chat models from the proxy.

When the reverse proxy starts advertising a model newer than the one currently
configured on a `conversation` subentry (e.g. `gpt-5.6` shows up while we're
still on `gpt-5.5`), this entity becomes "update available" and a one-click
install rewrites the subentry data to the latest model and reloads the entry.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.update import (
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_COORDINATOR,
    DEFAULT_MODEL,
    DOMAIN,
    SUBENTRY_TYPE_CONVERSATION,
)
from .coordinator import CodexModelCoordinator

if TYPE_CHECKING:
    from . import CodexConfigEntry

_LOGGER = logging.getLogger(__name__)


def _conf_chat_model_key() -> str:
    """Late-import upstream's CONF_CHAT_MODEL so we don't break load if it is
    ever renamed; we'll just degrade to the literal default."""
    try:
        from homeassistant.components.openai_conversation.const import (
            CONF_CHAT_MODEL,
        )

        return CONF_CHAT_MODEL
    except ImportError:  # pragma: no cover
        return "chat_model"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: "CodexConfigEntry",
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one update entity per conversation subentry."""
    coordinator: CodexModelCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    chat_model_key = _conf_chat_model_key()

    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_CONVERSATION:
            continue
        async_add_entities(
            [CodexModelUpdate(coordinator, entry, subentry, chat_model_key)],
            config_subentry_id=subentry.subentry_id,
        )


class CodexModelUpdate(
    CoordinatorEntity[CodexModelCoordinator], UpdateEntity
):
    """Tracks the latest chat model surfaced by the proxy."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_supported_features = UpdateEntityFeature.INSTALL
    _attr_translation_key = "model_update"

    def __init__(
        self,
        coordinator: CodexModelCoordinator,
        entry: "CodexConfigEntry",
        subentry: ConfigSubentry,
        chat_model_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._subentry = subentry
        self._chat_model_key = chat_model_key
        self._attr_unique_id = f"{subentry.subentry_id}_model_update"
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
        )

    @property
    def installed_version(self) -> str | None:
        return self._subentry.data.get(self._chat_model_key, DEFAULT_MODEL)

    @property
    def latest_version(self) -> str | None:
        latest = self.coordinator.latest_chat_model_id
        return latest or self.installed_version

    @property
    def title(self) -> str | None:
        return "Codex 号池模型"

    @property
    def release_summary(self) -> str | None:
        latest = self.coordinator.latest_chat_model_id
        installed = self.installed_version
        if not latest or latest == installed:
            return "已经是反代上的最新模型。"
        return (
            f"反代发现新模型 {latest}（当前：{installed}）。"
            "点击安装可一键切换。"
        )

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Switch the subentry's model to the requested (or latest) version
        and reload the config entry."""
        target = version or self.coordinator.latest_chat_model_id
        if not target:
            return
        new_data = {**self._subentry.data, self._chat_model_key: target}
        self.hass.config_entries.async_update_subentry(
            self._entry, self._subentry, data=new_data
        )
        await self.hass.config_entries.async_reload(self._entry.entry_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        # Re-read the subentry from the entry registry so installed_version
        # reflects user changes that didn't come through this entity.
        live = self._entry.subentries.get(self._subentry.subentry_id)
        if live is not None:
            self._subentry = live
        super()._handle_coordinator_update()
