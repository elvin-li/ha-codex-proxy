"""Tests for entity_utils.build_codex_device_info and build_codex_entry_device_info.

Runs without a full HA install by using the shared ha_stubs module.
"""
from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.ha_stubs  # noqa: F401, E402

from custom_components.codex_proxy.entity_utils import (  # noqa: E402
    build_codex_device_info,
    build_codex_entry_device_info,
)
from custom_components.codex_proxy.const import DEFAULT_MODEL, DOMAIN  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_subentry(
    subentry_id: str = "sub-1",
    title: str = "Test Agent",
    data: dict | None = None,
) -> MagicMock:
    s = MagicMock()
    s.subentry_id = subentry_id
    s.title = title
    s.data = data or {}
    return s


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildCodexDeviceInfo:
    def test_identifiers_contain_domain_and_subentry_id(self) -> None:
        sub = _make_subentry(subentry_id="my-sub-123")
        info = build_codex_device_info(sub, "chat_model")
        # DeviceInfo is stubbed as dict; identifiers are passed as keyword arg
        assert (DOMAIN, "my-sub-123") in info["identifiers"]

    def test_name_matches_subentry_title(self) -> None:
        sub = _make_subentry(title="My Codex Agent")
        info = build_codex_device_info(sub, "chat_model")
        assert info["name"] == "My Codex Agent"

    def test_manufacturer_is_set(self) -> None:
        sub = _make_subentry()
        info = build_codex_device_info(sub, "chat_model")
        assert info["manufacturer"] == "OpenAI Codex Token Pool"

    def test_model_taken_from_subentry_data(self) -> None:
        sub = _make_subentry(data={"chat_model": "gpt-5.6"})
        info = build_codex_device_info(sub, "chat_model")
        assert info["model"] == "gpt-5.6"

    def test_model_falls_back_to_default_when_key_missing(self) -> None:
        sub = _make_subentry(data={})
        info = build_codex_device_info(sub, "chat_model")
        assert info["model"] == DEFAULT_MODEL

    def test_custom_chat_model_key(self) -> None:
        sub = _make_subentry(data={"custom_key": "gpt-custom"})
        info = build_codex_device_info(sub, "custom_key")
        assert info["model"] == "gpt-custom"

    def test_two_subentries_get_different_identifiers(self) -> None:
        sub_a = _make_subentry(subentry_id="sub-a")
        sub_b = _make_subentry(subentry_id="sub-b")
        info_a = build_codex_device_info(sub_a, "chat_model")
        info_b = build_codex_device_info(sub_b, "chat_model")
        assert info_a["identifiers"] != info_b["identifiers"]


# ---------------------------------------------------------------------------
# build_codex_entry_device_info
# ---------------------------------------------------------------------------


def _make_entry(entry_id: str = "entry-1", title: str = "Codex 号池") -> MagicMock:
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.title = title
    return entry


class TestBuildCodexEntryDeviceInfo:
    def test_identifiers_contain_domain_and_entry_id(self) -> None:
        entry = _make_entry("my-entry-abc")
        info = build_codex_entry_device_info(entry)
        assert (DOMAIN, "my-entry-abc") in info["identifiers"]

    def test_name_matches_entry_title(self) -> None:
        entry = _make_entry(title="Codex Proxy Test")
        info = build_codex_entry_device_info(entry)
        assert info["name"] == "Codex Proxy Test"

    def test_manufacturer_is_set(self) -> None:
        entry = _make_entry()
        info = build_codex_entry_device_info(entry)
        assert info["manufacturer"] == "OpenAI Codex Token Pool"

    def test_no_model_key_present(self) -> None:
        """Entry-level DeviceInfo should not include a 'model' field."""
        entry = _make_entry()
        info = build_codex_entry_device_info(entry)
        assert "model" not in info

    def test_two_entries_get_different_identifiers(self) -> None:
        info_a = build_codex_entry_device_info(_make_entry("e-1"))
        info_b = build_codex_entry_device_info(_make_entry("e-2"))
        assert info_a["identifiers"] != info_b["identifiers"]
