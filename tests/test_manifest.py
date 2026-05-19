"""Tests for custom_components/codex_proxy/manifest.json.

Verifies the manifest is valid JSON with all HA-required and HACS-required
fields, correct types, and a well-formed semantic version string.
"""

from __future__ import annotations

import json
import os
import re

_MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "custom_components",
    "codex_proxy",
    "manifest.json",
)


def _load() -> dict:
    with open(_MANIFEST_PATH, encoding="utf-8") as fh:
        return json.load(fh)


class TestManifestValidity:
    def test_is_valid_json(self) -> None:
        """manifest.json must parse without raising."""
        data = _load()
        assert isinstance(data, dict)

    def test_domain_is_codex_proxy(self) -> None:
        assert _load()["domain"] == "codex_proxy"

    def test_name_is_non_empty_string(self) -> None:
        name = _load()["name"]
        assert isinstance(name, str) and name

    def test_version_is_semver(self) -> None:
        """Version must be X.Y.Z (HACS and HA enforce this)."""
        version = _load()["version"]
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"Version {version!r} is not semver X.Y.Z"

    def test_config_flow_is_true(self) -> None:
        assert _load()["config_flow"] is True

    def test_integration_type_is_service(self) -> None:
        assert _load()["integration_type"] == "service"

    def test_iot_class_present(self) -> None:
        assert "iot_class" in _load()

    def test_homeassistant_min_version_present(self) -> None:
        data = _load()
        assert "homeassistant" in data
        assert re.fullmatch(r"\d{4}\.\d+\.\d+", data["homeassistant"]), (
            f"homeassistant value {data['homeassistant']!r} does not match YYYY.MM.N"
        )

    def test_codeowners_is_list(self) -> None:
        codeowners = _load()["codeowners"]
        assert isinstance(codeowners, list)
        assert len(codeowners) > 0

    def test_requirements_is_empty_list(self) -> None:
        """We delegate all requirements to the upstream openai_conversation integration."""
        assert _load()["requirements"] == []

    def test_after_dependencies_includes_openai_conversation(self) -> None:
        assert "openai_conversation" in _load()["after_dependencies"]
