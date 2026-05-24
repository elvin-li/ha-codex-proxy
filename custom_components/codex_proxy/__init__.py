"""Codex Token Pool — Home Assistant integration.

Architecture
------------
This integration is a **thin shim on top of the official `openai_conversation`
integration** that ships with Home Assistant Core. The official integration
already targets the Responses API but hard-codes ``https://api.openai.com``
and omits the Codex-CLI-flavored HTTP headers required by token-pool reverse
proxies. We only swap those two layers and inherit everything else
(streaming, tool calls, reasoning, structured output, etc.) from upstream so
that future Home Assistant releases automatically extend this integration.

Runtime state
~~~~~~~~~~~~~
All per-entry runtime state lives on ``entry.runtime_data`` as a typed
``CodexRuntimeData`` dataclass — a single typed slot that carries both the
``AsyncOpenAI`` client (consumed by upstream's conversation/ai_task entities
via ``entry.runtime_data``) and the ``CodexModelCoordinator`` (consumed by
our update entity and config flow). We deliberately avoid ``hass.data`` so
that there is exactly one source of truth per entry.

Upstream's ``OpenAIConversationEntity`` reads ``entry.runtime_data`` directly
as the OpenAI client, so ``CodexRuntimeData`` exposes the client via
``__call__``- and attribute-compatible duck typing: it forwards every
attribute lookup to the wrapped client.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import openai
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_INSTALLATION_ID,
    DOMAIN,
    build_codex_headers,
)
from .coordinator import CodexModelCoordinator

if TYPE_CHECKING:
    from openai import AsyncOpenAI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.CONVERSATION,
    Platform.AI_TASK,
    Platform.UPDATE,
]


@dataclass(slots=True)
class CodexRuntimeData:
    """Typed payload pinned to ``entry.runtime_data``.

    Upstream's openai_conversation entities read ``entry.runtime_data`` as
    the ``AsyncOpenAI`` client, so we proxy attribute access to ``client``.
    The coordinator hangs off the same object instead of ``hass.data`` to
    keep one source of truth per entry.
    """

    client: "AsyncOpenAI"
    coordinator: CodexModelCoordinator
    installation_id: str

    def __getattr__(self, item: str) -> Any:
        # Fallback only — dataclass slots resolve declared fields normally
        # and `__getattr__` is consulted only on miss. This keeps
        # ``entry.runtime_data.<openai-method>`` working for upstream code
        # that still treats runtime_data as the bare client.
        return getattr(self.client, item)


type CodexConfigEntry = ConfigEntry[CodexRuntimeData]


def _ensure_installation_id(
    hass: HomeAssistant, entry: CodexConfigEntry
) -> str:
    """Return a stable, persisted Codex installation id for this entry."""
    installation_id = entry.data.get(CONF_INSTALLATION_ID)
    if installation_id:
        return installation_id
    installation_id = str(uuid.uuid4())
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, CONF_INSTALLATION_ID: installation_id},
    )
    return installation_id


async def async_setup_entry(hass: HomeAssistant, entry: CodexConfigEntry) -> bool:
    """Set up Codex Token Pool from a config entry."""
    api_key: str = entry.data[CONF_API_KEY]
    base_url: str = entry.data[CONF_BASE_URL]

    installation_id = _ensure_installation_id(hass, entry)

    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=get_async_client(hass),
        default_headers=build_codex_headers(installation_id),
    )

    # No probe call here on purpose — config_flow already verified the proxy
    # via /v1/responses, and `models.list()` cannot be used because the openai
    # SDK 2.x page parser is incompatible with this proxy's /v1/models shape
    # (see coordinator.py for the raw httpx workaround we use instead).

    coordinator = CodexModelCoordinator(hass, entry, installation_id)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # noqa: BLE001 — model discovery is non-fatal
        _LOGGER.warning("Initial model refresh failed: %s", err)

    entry.runtime_data = CodexRuntimeData(
        client=client,
        coordinator=coordinator,
        installation_id=installation_id,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CodexConfigEntry) -> bool:
    """Unload a Codex Token Pool config entry.

    We deliberately do NOT call ``client.close()`` — the AsyncOpenAI client
    wraps HA's shared httpx client (``get_async_client(hass)``); closing it
    would tear down HTTP I/O for every other integration sharing it.
    HA clears ``entry.runtime_data`` automatically once unload returns True.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    entry: CodexConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow the user to remove a device row tied to a deleted subentry.

    HA only invokes this when a device exists with no live entities still
    pointing at it (i.e. the subentry that owned it has already been deleted
    or renamed). We always allow removal in that case.
    """
    live_subentry_ids = {
        identifier[1]
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN
    } & set(entry.subentries)
    return not live_subentry_ids


async def _async_update_listener(
    hass: HomeAssistant, entry: CodexConfigEntry
) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
