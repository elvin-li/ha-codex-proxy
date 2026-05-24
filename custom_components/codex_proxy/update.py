"""Update entity that surfaces newer chat models from the proxy.

When the reverse proxy starts advertising a model newer than the one
currently configured on a ``conversation`` or ``ai_task_data`` subentry
(e.g. ``gpt-5.6`` shows up while we're still on ``gpt-5.5``), this entity
becomes "update available" and a one-click install rewrites the subentry
data to the latest model and reloads the config entry.

One update entity per LLM-bearing subentry — both conversation agents
and AI Task entities get tracked.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.openai_conversation.const import (
    CONF_CHAT_MODEL as UPSTREAM_CONF_CHAT_MODEL,
)
from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_BASE_URL,
    DEFAULT_MODEL,
    LLM_BEARING_SUBENTRY_TYPES,
    build_codex_device_info,
)
from .coordinator import CodexModelCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one update entity per conversation/ai_task subentry."""
    coordinator: CodexModelCoordinator = entry.runtime_data.coordinator
    for subentry in entry.subentries.values():
        if subentry.subentry_type not in LLM_BEARING_SUBENTRY_TYPES:
            continue
        async_add_entities(
            [CodexModelUpdate(coordinator, entry, subentry)],
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
        entry: ConfigEntry,
        subentry: ConfigSubentry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._subentry = subentry
        self._attr_unique_id = f"{subentry.subentry_id}_model_update"
        # Reuse the same device row the conversation/ai_task entity already
        # registered; we pass model=None so we don't fight that entity for
        # the device's displayed model attribute.
        self._attr_device_info = build_codex_device_info(subentry)

    @property
    def installed_version(self) -> str | None:
        return self._subentry.data.get(UPSTREAM_CONF_CHAT_MODEL, DEFAULT_MODEL)

    @property
    def latest_version(self) -> str | None:
        # When the coordinator hasn't returned data yet (or proxy is down),
        # report installed_version so HA doesn't render "update available"
        # against a phantom None.
        return self.coordinator.latest_chat_model_id or self.installed_version

    @property
    def title(self) -> str | None:
        return "Codex 号池模型"

    @property
    def release_url(self) -> str | None:
        """Link to the proxy's /v1/models endpoint, useful for inspection."""
        base_url = self._entry.data.get(CONF_BASE_URL)
        if not base_url:
            return None
        return f"{str(base_url).rstrip('/')}/v1/models"

    @property
    def release_summary(self) -> str | None:
        latest = self.coordinator.latest_chat_model_id
        installed = self.installed_version
        if not latest:
            return "尚未从反代取得模型列表（首次刷新最长 6h，可手动 update_entity）。"
        if latest == installed:
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
        if not target or target == self.installed_version:
            return
        new_data = {**self._subentry.data, UPSTREAM_CONF_CHAT_MODEL: target}
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
