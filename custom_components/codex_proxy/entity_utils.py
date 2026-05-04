"""Shared helpers for Codex Token Pool entity construction."""
from __future__ import annotations

from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers import device_registry as dr

from .const import DEFAULT_MODEL, DOMAIN


def build_codex_device_info(
    subentry: ConfigSubentry, chat_model_key: str
) -> dr.DeviceInfo:
    """Return DeviceInfo anchored under the codex_proxy domain.

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
