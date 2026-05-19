"""Tests for entity_utils.build_codex_device_info and build_codex_entry_device_info.

Runs without a full HA install by using the shared ha_stubs module.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.ha_stubs  # noqa: F401, E402
from custom_components.codex_proxy.const import DEFAULT_MODEL, DOMAIN  # noqa: E402
from custom_components.codex_proxy.entity_utils import (  # noqa: E402
    INTEGRATION_VERSION,
    build_codex_device_info,
    build_codex_entry_device_info,
)

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

    def test_sw_version_is_present(self) -> None:
        """sw_version should be populated from the manifest (not missing/absent).

        Symmetry with build_codex_entry_device_info which has always included it.
        """
        sub = _make_subentry()
        info = build_codex_device_info(sub, "chat_model")
        assert "sw_version" in info
        # Value is either a non-empty string (real run) or None (manifest read failed).
        assert info["sw_version"] is None or isinstance(info["sw_version"], str)

    def test_sw_version_matches_manifest(self) -> None:
        """sw_version must equal the version field in manifest.json exactly.

        Parity test: TestBuildCodexEntryDeviceInfo already pins this invariant
        for entry-level entities; this test closes the gap for subentry-level
        entities created by build_codex_device_info."""
        import json
        import pathlib

        manifest_path = (
            pathlib.Path(__file__).parent.parent
            / "custom_components"
            / "codex_proxy"
            / "manifest.json"
        )
        expected = json.loads(manifest_path.read_text()).get("version")
        sub = _make_subentry()
        info = build_codex_device_info(sub, "chat_model")
        assert info["sw_version"] == expected


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

    def test_sw_version_is_populated(self) -> None:
        """sw_version should be a non-empty string read from manifest.json."""
        entry = _make_entry()
        info = build_codex_entry_device_info(entry)
        # INTEGRATION_VERSION is read from the real manifest.json at import time;
        # it must be a non-None, non-empty string in any checkout that has the file.
        assert info.get("sw_version") is not None
        assert isinstance(info["sw_version"], str)
        assert len(info["sw_version"]) > 0

    def test_sw_version_matches_manifest(self) -> None:
        """sw_version must match the version field in manifest.json exactly."""
        import json
        import pathlib

        manifest_path = (
            pathlib.Path(__file__).parent.parent
            / "custom_components"
            / "codex_proxy"
            / "manifest.json"
        )
        expected = json.loads(manifest_path.read_text()).get("version")
        entry = _make_entry()
        info = build_codex_entry_device_info(entry)
        assert info["sw_version"] == expected


# ---------------------------------------------------------------------------
# INTEGRATION_VERSION public constant
# ---------------------------------------------------------------------------


class TestIntegrationVersion:
    def test_is_public_name(self) -> None:
        """INTEGRATION_VERSION must be a non-None string in any checkout that
        has a valid manifest.json.  The previous assertion here was a tautology
        (``x is not None or x is None`` is always True); this replacement
        verifies the manifest was actually read at import time so the HA device
        card shows a real version string rather than the literal text 'None'."""
        assert INTEGRATION_VERSION is not None, (
            "INTEGRATION_VERSION is None — manifest.json failed to load at "
            "import time; the HA device card would display 'None' as the "
            "integration version instead of the real semver string."
        )

    def test_is_string_or_none(self) -> None:
        """INTEGRATION_VERSION must be a string (real manifest) or None
        (manifest read failed at import time — covered by pragma: no cover)."""
        assert INTEGRATION_VERSION is None or isinstance(INTEGRATION_VERSION, str)

    def test_matches_manifest(self) -> None:
        """INTEGRATION_VERSION must equal what manifest.json declares so that
        the diagnostics output shows the correct version."""
        import json
        import pathlib

        manifest_path = (
            pathlib.Path(__file__).parent.parent
            / "custom_components"
            / "codex_proxy"
            / "manifest.json"
        )
        expected = json.loads(manifest_path.read_text()).get("version")
        assert expected == INTEGRATION_VERSION
