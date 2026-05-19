"""Shared helpers for Codex Token Pool entity construction."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.helpers import device_registry as dr

from .const import DEFAULT_MODEL, DOMAIN


def build_codex_device_info(
    subentry: ConfigSubentry, chat_model_key: str
) -> dr.DeviceInfo:
    """Return DeviceInfo for a *subentry*-level entity (conversation / AI task).

    Both conversation and AI-task entities use this so any future change
    (e.g. adding sw_version) only needs to happen in one place.
    """
    return dr.DeviceInfo(
        identifiers={(DOMAIN, subentry.subentry_id)},
        name=subentry.title,
        manufacturer="OpenAI Codex Token Pool",
        model=subentry.data.get(chat_model_key, DEFAULT_MODEL),
        entry_type=dr.DeviceEntryType.SERVICE,
    )


def build_codex_entry_device_info(entry: ConfigEntry) -> dr.DeviceInfo:
    """Return DeviceInfo for an *entry*-level entity (binary_sensor, button, sensor).

    button.py, binary_sensor.py, and sensor.py all attach their entities to the
    top-level config entry device rather than a subentry device. This helper
    centralises that identical 5-line block so future changes (e.g. adding
    ``hw_version``) only need one edit.
    """
    return dr.DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="OpenAI Codex Token Pool",
        entry_type=dr.DeviceEntryType.SERVICE,
    )
