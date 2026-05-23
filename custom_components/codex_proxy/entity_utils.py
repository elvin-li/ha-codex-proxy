"""Shared helpers for Codex Token Pool entity construction."""

from __future__ import annotations

import json
import pathlib

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.helpers import device_registry as dr

from .const import DEFAULT_MODEL, DOMAIN

# Read sw_version once at import time from the manifest so the device card in
# HA reflects the installed integration version without manual maintenance.
_MANIFEST_PATH = pathlib.Path(__file__).parent / "manifest.json"
try:
    INTEGRATION_VERSION: str | None = json.loads(_MANIFEST_PATH.read_text()).get("version")
except (OSError, ValueError, KeyError):  # pragma: no cover
    INTEGRATION_VERSION = None  # pragma: no cover


def build_codex_device_info(subentry: ConfigSubentry, chat_model_key: str) -> dr.DeviceInfo:
    """Return DeviceInfo for a *subentry*-level entity (conversation / AI task).

    Both conversation and AI-task entities use this so any future change
    only needs to happen in one place.  ``sw_version`` is populated from the
    manifest so the device card in HA always shows the installed version.

    ``model`` collapses falsy ``chat_model`` values (``None`` or ``""``) to
    ``DEFAULT_MODEL`` — consistency with ``select.current_option`` and
    ``update.installed_version`` (both already handle this in v0.2.173+).
    Without the ``or`` fallback, a subentry created via reconfigure with an
    explicitly-blanked model field would surface as an empty model line in
    HA's device card.
    """
    return dr.DeviceInfo(
        identifiers={(DOMAIN, subentry.subentry_id)},
        name=subentry.title,
        manufacturer="OpenAI Codex Token Pool",
        model=subentry.data.get(chat_model_key) or DEFAULT_MODEL,
        entry_type=dr.DeviceEntryType.SERVICE,
        sw_version=INTEGRATION_VERSION,
    )


def build_codex_entry_device_info(entry: ConfigEntry) -> dr.DeviceInfo:
    """Return DeviceInfo for an *entry*-level entity (binary_sensor, button, sensor).

    button.py, binary_sensor.py, and sensor.py all attach their entities to the
    top-level config entry device rather than a subentry device. This helper
    centralises that identical 5-line block so future changes only need one edit.
    ``sw_version`` is populated from the manifest so HA's device card always
    shows the installed integration version.
    """
    return dr.DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="OpenAI Codex Token Pool",
        entry_type=dr.DeviceEntryType.SERVICE,
        sw_version=INTEGRATION_VERSION,
    )
