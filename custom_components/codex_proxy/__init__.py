"""Codex Token Pool — Home Assistant integration.

Architecture
------------
This integration is a **thin shim on top of the official `openai_conversation`
integration** that ships with Home Assistant Core. The official integration
already targets the Responses API but hard-codes `https://api.openai.com` and
omits the Codex-CLI-flavored HTTP headers required by token-pool reverse
proxies. We only swap those two layers and inherit everything else
(streaming, tool calls, reasoning, structured output, etc.) from upstream so
that future Home Assistant releases automatically extend this integration.
"""
from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

import httpx
import openai
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    CODEX_OPENAI_BETA,
    CODEX_ORIGINATOR,
    CODEX_USER_AGENT,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_INSTALLATION_ID,
    DATA_COORDINATOR,
    DOMAIN,
)
from .coordinator import CodexModelCoordinator

if TYPE_CHECKING:
    from openai import AsyncOpenAI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.CONVERSATION,
    Platform.AI_TASK,
    Platform.SENSOR,
    Platform.UPDATE,
]

type CodexConfigEntry = ConfigEntry["AsyncOpenAI"]


def _build_codex_headers(installation_id: str) -> dict[str, str]:
    """Build the default headers that mimic a real Codex CLI request.

    Token-pool reverse proxies routinely gate on these headers to distinguish
    Codex traffic from generic OpenAI SDK traffic. Sending them defensively
    costs nothing if the proxy doesn't check them.
    """
    return {
        "User-Agent": CODEX_USER_AGENT,
        "OpenAI-Beta": CODEX_OPENAI_BETA,
        "originator": CODEX_ORIGINATOR,
        "x-codex-installation-id": installation_id,
    }


async def async_setup_entry(hass: HomeAssistant, entry: CodexConfigEntry) -> bool:
    """Set up Codex Token Pool from a config entry."""
    api_key: str = entry.data[CONF_API_KEY]
    base_url: str = entry.data[CONF_BASE_URL]

    installation_id = entry.data.get(CONF_INSTALLATION_ID)
    if not installation_id:
        installation_id = str(uuid.uuid4())
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_INSTALLATION_ID: installation_id},
        )

    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=get_async_client(hass),
        default_headers=_build_codex_headers(installation_id),
    )

    # No probe call here on purpose — config_flow already verified the proxy
    # via /v1/responses, and `models.list()` cannot be used because the openai
    # SDK 2.x page parser is incompatible with this proxy's /v1/models shape
    # (see coordinator.py for the raw httpx workaround we use instead).
    entry.runtime_data = client

    coordinator = CodexModelCoordinator(hass, entry, installation_id)
    try:
        await coordinator.async_config_entry_first_refresh()
    except (httpx.HTTPError, UpdateFailed) as err:
        # Coordinator failure is non-fatal — the entry still loads and polls
        # again at the next MODEL_REFRESH_INTERVAL tick.
        _LOGGER.warning("Initial model refresh failed: %s", err)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: CodexConfigEntry) -> bool:
    """Migrate config entries from older schema versions.

    Version 1 is the current schema (api_key + base_url + codex_installation_id).
    This function is called automatically by HA when entry.version < VERSION in
    CodexConfigFlow. Add new ``if entry.version < N`` blocks here as the schema
    evolves so existing users are migrated non-destructively on upgrade.
    """
    _LOGGER.debug(
        "Migrating Codex Token Pool config entry from version %s", entry.version
    )
    # No migrations needed yet — version 1 is the only schema.
    # Future example:
    #   if entry.version < 2:
    #       hass.config_entries.async_update_entry(entry, version=2, data={...})
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CodexConfigEntry) -> bool:
    """Unload a Codex Token Pool config entry.

    We deliberately do NOT call `client.close()` — the AsyncOpenAI client
    is wrapping HA's shared httpx client (`get_async_client(hass)`); closing
    it would tear down HTTP I/O for every other integration.
    """
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded


async def _async_update_listener(
    hass: HomeAssistant, entry: CodexConfigEntry
) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
