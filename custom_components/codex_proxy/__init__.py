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
from typing import TYPE_CHECKING, Any

import httpx
import openai
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import UpdateFailed

from ._pure_helpers import normalize_base_url
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
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CONVERSATION,
    Platform.AI_TASK,
    Platform.SELECT,
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
    stored_base_url: str = entry.data[CONF_BASE_URL]
    # Normalise the base URL so the OpenAI SDK (which expects an "openai-
    # compatible base" ending in /v1) hits /v1/responses rather than
    # /responses.  Entries created by older versions stored the bare host
    # (e.g. https://proxy.example.com) which silently worked against lenient
    # proxies but produced a cryptic "Last content in chat log is not an
    # AssistantContent" error against strict proxies — we now lazily migrate
    # those entries here so users don't have to delete-and-recreate.
    base_url = normalize_base_url(stored_base_url)

    installation_id = entry.data.get(CONF_INSTALLATION_ID)
    new_data: dict[str, str] | None = None
    new_unique_id: str | None = None
    if base_url != stored_base_url:
        new_data = {**entry.data, CONF_BASE_URL: base_url}
        # Keep ``entry.unique_id`` in sync with the normalised ``base_url`` so
        # the reconfigure flow's ``_abort_if_unique_id_mismatch`` does not
        # reject every legacy entry: pre-v0.2.171 entries had
        # ``unique_id`` set to the bare-host base_url; if we migrate ``data``
        # without also rewriting ``unique_id``, the next reconfigure attempt
        # (which sets ``unique_id`` to the normalised form) aborts with a
        # mismatch error and the user can never edit their entry again.
        if entry.unique_id == stored_base_url:
            new_unique_id = base_url
    if not installation_id:
        installation_id = str(uuid.uuid4())
        new_data = {**(new_data or entry.data), CONF_INSTALLATION_ID: installation_id}
    if new_data is not None:
        update_kwargs: dict[str, Any] = {"data": new_data}
        if new_unique_id is not None:
            update_kwargs["unique_id"] = new_unique_id
        hass.config_entries.async_update_entry(entry, **update_kwargs)

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
    except (httpx.HTTPError, UpdateFailed, ConfigEntryNotReady) as err:
        # Coordinator failure is non-fatal — the entry still loads and polls
        # again at the next MODEL_REFRESH_INTERVAL tick.
        #
        # ``async_config_entry_first_refresh`` catches ``UpdateFailed`` from
        # ``_async_update_data`` internally and re-raises it as
        # ``ConfigEntryNotReady``.  Catching only ``UpdateFailed`` here would
        # therefore *never* match in production — the entry would fail to load
        # entirely on any transient proxy hiccup at HA startup, contradicting
        # the "warn and continue" contract documented in this branch.  Catch
        # all three so the entity tree is registered even when the proxy is
        # temporarily down.
        _LOGGER.warning("Initial model refresh failed: %s", err)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: CodexConfigEntry) -> bool:
    """Migrate config entries from older schema versions.

    Version 1 is the current schema (api_key + base_url + codex_installation_id).
    This function is called automatically by HA when entry.version < VERSION in
    CodexConfigFlow. Add new ``if entry.version < N`` blocks here as the schema
    evolves so existing users are migrated non-destructively on upgrade.
    """
    _LOGGER.debug("Migrating Codex Token Pool config entry from version %s", entry.version)
    # No migrations needed yet — version 1 is the only schema.
    # Future example:
    #   if entry.version < 2:
    #       hass.config_entries.async_update_entry(entry, version=2, data={...})
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CodexConfigEntry) -> bool:
    """Unload a Codex Token Pool config entry.

    We deliberately do NOT call ``client.close()`` — the AsyncOpenAI client
    wraps HA's shared httpx client (``get_async_client(hass)``); closing it
    would tear down HTTP I/O for every other integration.

    We DO shut down the ``CodexModelCoordinator`` so its scheduled refresh
    listener (set up by ``DataUpdateCoordinator.__init__`` via
    ``update_interval``) does not fire after the entry has been popped from
    ``hass.data``.  Without ``async_shutdown()`` the next periodic tick
    enters ``_async_update_data`` against a coordinator whose entry is gone,
    and any downstream code that looks up
    ``hass.data[DOMAIN][entry.entry_id]`` raises ``KeyError`` — producing
    spurious post-unload tracebacks in the HA log on every reload.
    """
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        domain_data = hass.data.get(DOMAIN, {})
        bucket = domain_data.pop(entry.entry_id, None)
        if bucket is not None:
            coordinator: CodexModelCoordinator | None = bucket.get(DATA_COORDINATOR)
            if coordinator is not None:
                await coordinator.async_shutdown()
    return unloaded
