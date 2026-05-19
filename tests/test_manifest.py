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

    def test_name_exact_value(self) -> None:
        """name must be exactly 'Codex Token Pool'.

        test_name_is_non_empty_string only checks type and truthiness — any
        non-empty string passes.  The name appears in HA's Integrations list,
        HACS, and community forum posts; an accidental rename (e.g. via
        copy-paste from another integration) would confuse existing users.
        Exact equality catches a rename before it ships."""
        assert _load()["name"] == "Codex Token Pool", (
            f"manifest.json name must be 'Codex Token Pool', got {_load()['name']!r}"
        )

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

    def test_iot_class_is_cloud_polling(self) -> None:
        """iot_class must be 'cloud_polling' — this proxy fetches model lists from a
        remote server on a schedule.  If it were changed to 'local_polling' HA would
        show incorrect metadata (no cloud dependency) and HACS would mis-categorise
        the integration.  test_iot_class_present only checks presence; this test
        pins the exact value."""
        assert _load()["iot_class"] == "cloud_polling", (
            "iot_class must be 'cloud_polling' — the integration polls a remote "
            "proxy over the network and should be labelled accordingly"
        )

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

    def test_quality_scale_is_silver(self) -> None:
        """quality_scale must be 'silver' — this controls the HACS badge and HA
        integration quality indicator.  Changing it accidentally should be caught."""
        assert _load().get("quality_scale") == "silver"

    def test_dependencies_is_empty_list(self) -> None:
        """Hard dependencies must remain empty — we piggyback on
        openai_conversation via after_dependencies (soft dependency) to avoid
        forcing it to load before HA finishes its startup sequence."""
        assert _load()["dependencies"] == []
