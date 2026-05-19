"""Diagnostics support for the Codex Token Pool integration.

Accessible via HA's "Download Diagnostics" button on the integration card.
The API key is redacted before the data leaves the device.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, DATA_COORDINATOR, DOMAIN
from .entity_utils import INTEGRATION_VERSION

_TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostic info for the config entry (API key redacted)."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    last_exc = coordinator.last_exception
    coordinator_info: dict[str, Any] = {
        "last_update_success": coordinator.last_update_success,
        "last_update_success_time": (
            coordinator.last_update_success_time.isoformat()
            if coordinator.last_update_success_time
            else None
        ),
        # str() of a timedelta produces a human-readable form such as "6:00:00"
        # that is easy to copy into a bug report or compare with MODEL_REFRESH_INTERVAL.
        "update_interval": str(coordinator.update_interval),
        # last_exception is set by DataUpdateCoordinator when an update fails and
        # cleared on success. str(exc) gives the error message without a traceback
        # — safe to include because our error messages contain only the URL and
        # exception type, never the API key (which is in HTTP headers).
        "last_error": str(last_exc) if last_exc is not None else None,
        "chat_models_count": len(coordinator.chat_models),
        "latest_chat_model": coordinator.latest_chat_model_id,
        "models": coordinator.data.get("models", []) if coordinator.data else [],
    }

    subentries_info = [
        {
            "subentry_type": s.subentry_type,
            "title": s.title,
            "data": async_redact_data(dict(s.data), _TO_REDACT),
        }
        for s in entry.subentries.values()
    ]

    return {
        "integration_version": INTEGRATION_VERSION,
        "entry_data": async_redact_data(dict(entry.data), _TO_REDACT),
        "coordinator": coordinator_info,
        "subentries": subentries_info,
    }
