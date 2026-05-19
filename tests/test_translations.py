"""Tests for translation file consistency.

Verifies that strings.json, translations/en.json, and translations/zh-Hans.json
all have the same top-level keys and that critical sections (config.error,
entity) are present and non-empty. A mismatch here causes HA to render
raw translation-key strings in the UI instead of human-readable text.
"""

from __future__ import annotations

import json
import os

# Path to the integration root
_INTEGRATION = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "custom_components",
    "codex_proxy",
)


def _load(filename: str) -> dict:
    with open(os.path.join(_INTEGRATION, filename), encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTranslationKeyConsistency:
    def test_strings_and_en_have_same_top_level_keys(self) -> None:
        strings = _load("strings.json")
        en = _load("translations/en.json")
        assert set(strings.keys()) == set(en.keys())

    def test_strings_and_zh_have_same_top_level_keys(self) -> None:
        strings = _load("strings.json")
        zh = _load("translations/zh-Hans.json")
        assert set(strings.keys()) == set(zh.keys())

    def test_config_error_keys_consistent_across_all_files(self) -> None:
        strings = _load("strings.json")
        en = _load("translations/en.json")
        zh = _load("translations/zh-Hans.json")

        s_errors = set(strings["config"]["error"].keys())
        e_errors = set(en["config"]["error"].keys())
        z_errors = set(zh["config"]["error"].keys())

        assert s_errors == e_errors, f"en.json missing keys: {s_errors - e_errors}"
        assert s_errors == z_errors, f"zh-Hans.json missing keys: {s_errors - z_errors}"

    def test_config_error_keys_exact_set(self) -> None:
        """strings.json must define exactly the known config error keys.

        test_config_error_keys_consistent_across_all_files proves cross-file
        agreement, but if all three files simultaneously gain or lose an error
        key that test still passes. This test pins the canonical set so any
        accidental addition or removal is caught at the source (strings.json)
        regardless of whether the other files mirror the change."""
        strings = _load("strings.json")
        actual = set(strings["config"]["error"].keys())
        expected = {
            "cannot_connect",
            "invalid_auth",
            "unknown_model",
            "unknown",
            "bad_toml",
            "required",
            "invalid_url_scheme",
            "invalid_url",
            "toml_no_base_url",
            "rate_limited",
        }
        assert actual == expected, (
            f"Expected config error keys {expected!r}, got {actual!r} — "
            "update this test when an error key is intentionally added or removed"
        )

    def test_entity_section_present_in_all_files(self) -> None:
        for fname in ("strings.json", "translations/en.json", "translations/zh-Hans.json"):
            data = _load(fname)
            assert "entity" in data, f"{fname} missing 'entity' section"

    def test_binary_sensor_proxy_reachable_in_all_files(self) -> None:
        for fname in ("strings.json", "translations/en.json", "translations/zh-Hans.json"):
            data = _load(fname)
            assert "binary_sensor" in data["entity"], f"{fname} missing entity.binary_sensor"
            assert "proxy_reachable" in data["entity"]["binary_sensor"], (
                f"{fname} missing entity.binary_sensor.proxy_reachable"
            )

    def test_config_step_user_present_in_all_files(self) -> None:
        for fname in ("strings.json", "translations/en.json", "translations/zh-Hans.json"):
            data = _load(fname)
            assert "user" in data["config"]["step"], f"{fname} missing config.step.user"

    def test_config_step_reconfigure_present_in_all_files(self) -> None:
        for fname in ("strings.json", "translations/en.json", "translations/zh-Hans.json"):
            data = _load(fname)
            assert "reconfigure" in data["config"]["step"], (
                f"{fname} missing config.step.reconfigure"
            )

    def test_no_empty_translation_values(self) -> None:
        """Spot-check that key translation strings are non-empty."""
        for fname in ("strings.json", "translations/en.json", "translations/zh-Hans.json"):
            data = _load(fname)
            for error_key, error_val in data["config"]["error"].items():
                assert error_val, f"{fname} has empty string for config.error.{error_key}"

    def test_entity_platform_keys_consistent_across_all_files(self) -> None:
        """All three files must declare the same set of entity platform keys
        (binary_sensor, button, select, sensor, update)."""
        strings = _load("strings.json")
        en = _load("translations/en.json")
        zh = _load("translations/zh-Hans.json")

        s_platforms = set(strings["entity"].keys())
        e_platforms = set(en["entity"].keys())
        z_platforms = set(zh["entity"].keys())

        assert s_platforms == e_platforms, (
            f"en.json entity platform mismatch: {s_platforms ^ e_platforms}"
        )
        assert s_platforms == z_platforms, (
            f"zh-Hans.json entity platform mismatch: {s_platforms ^ z_platforms}"
        )

    def test_entity_platform_keys_exact_set(self) -> None:
        """strings.json must declare exactly the five entity platform keys.

        test_entity_platform_keys_consistent_across_all_files proves all three
        files agree with each other, but if all three files simultaneously drop
        a platform (e.g. 'button') that test still passes. This test pins the
        canonical set so a simultaneous omission is caught."""
        strings = _load("strings.json")
        actual = set(strings["entity"].keys())
        expected = {"binary_sensor", "button", "select", "sensor", "update"}
        assert actual == expected, (
            f"Expected entity platforms {expected!r}, got {actual!r} — "
            "update this test only when a platform is intentionally added or removed"
        )

    def test_entity_keys_consistent_across_all_files(self) -> None:
        """Within each platform, the entity translation keys (proxy_reachable,
        refresh_models, etc.) must match across all three files."""
        strings = _load("strings.json")
        en = _load("translations/en.json")
        zh = _load("translations/zh-Hans.json")

        for platform in strings["entity"]:
            s_keys = set(strings["entity"][platform].keys())
            e_keys = set(en["entity"].get(platform, {}).keys())
            z_keys = set(zh["entity"].get(platform, {}).keys())
            assert s_keys == e_keys, f"en.json entity.{platform} key mismatch: {s_keys ^ e_keys}"
            assert s_keys == z_keys, (
                f"zh-Hans.json entity.{platform} key mismatch: {s_keys ^ z_keys}"
            )

    def test_all_entity_keys_have_name_field(self) -> None:
        """Every entity translation entry must have a 'name' field so HA can
        display a human-readable name in the UI."""
        for fname in ("strings.json", "translations/en.json", "translations/zh-Hans.json"):
            data = _load(fname)
            for platform, entities in data["entity"].items():
                for key, entry in entities.items():
                    assert "name" in entry, (
                        f"{fname} entity.{platform}.{key} is missing 'name' field"
                    )
                    assert entry["name"], f"{fname} entity.{platform}.{key}.name is empty"

    def test_config_subentries_keys_consistent_across_all_files(self) -> None:
        """config_subentries section must have the same subentry types and step
        keys in all three files so HA can render the subentry flows correctly."""
        strings = _load("strings.json")
        en = _load("translations/en.json")
        zh = _load("translations/zh-Hans.json")

        s_types = set(strings.get("config_subentries", {}).keys())
        e_types = set(en.get("config_subentries", {}).keys())
        z_types = set(zh.get("config_subentries", {}).keys())
        assert s_types == e_types, f"en.json config_subentries type mismatch: {s_types ^ e_types}"
        assert s_types == z_types, (
            f"zh-Hans.json config_subentries type mismatch: {s_types ^ z_types}"
        )

        for subentry_type in s_types:
            s_steps = set(strings["config_subentries"][subentry_type].get("step", {}).keys())
            e_steps = set(en["config_subentries"][subentry_type].get("step", {}).keys())
            z_steps = set(zh["config_subentries"][subentry_type].get("step", {}).keys())
            assert s_steps == e_steps, (
                f"en.json config_subentries.{subentry_type}.step mismatch: {s_steps ^ e_steps}"
            )
            assert s_steps == z_steps, (
                f"zh-Hans.json config_subentries.{subentry_type}.step mismatch: {s_steps ^ z_steps}"
            )

    def test_no_empty_data_description_values(self) -> None:
        """data_description fields in config_subentries steps must be non-empty.

        A developer adding a new subentry field may forget to fill in the
        description; this test catches empty strings before they reach users.
        """
        for fname in ("strings.json", "translations/en.json", "translations/zh-Hans.json"):
            data = _load(fname)
            for subentry_type, subentry_data in data.get("config_subentries", {}).items():
                for step_name, step_data in subentry_data.get("step", {}).items():
                    for field_key, description in step_data.get("data_description", {}).items():
                        assert description, (
                            f"{fname} config_subentries.{subentry_type}.step."
                            f"{step_name}.data_description.{field_key} is empty"
                        )

    def test_binary_sensor_state_attributes_documented(self) -> None:
        """proxy_reachable exposes last_checked, latest_model, and last_error via
        extra_state_attributes; all translation files must document them so
        HA's UI renders proper labels in the More Info dialog."""
        for fname in ("strings.json", "translations/en.json", "translations/zh-Hans.json"):
            data = _load(fname)
            ps = data["entity"]["binary_sensor"]["proxy_reachable"]
            assert "state_attributes" in ps, (
                f"{fname} entity.binary_sensor.proxy_reachable missing state_attributes"
            )
            attrs = ps["state_attributes"]
            for key in ("last_checked", "latest_model", "last_error"):
                assert key in attrs, (
                    f"{fname} entity.binary_sensor.proxy_reachable.state_attributes "
                    f"missing {key!r}"
                )
                assert "name" in attrs[key], (
                    f"{fname} state_attributes.{key} is missing 'name' field"
                )
                assert attrs[key]["name"], (
                    f"{fname} state_attributes.{key}.name is empty"
                )

    def test_all_translation_keys_in_sync(self) -> None:
        """Deep structural check: the full set of dotted key paths in strings.json,
        en.json, and zh-Hans.json must be identical. This catches any new key added
        to one file but forgotten in the others at any nesting depth."""

        def _flatten(d: dict, prefix: str = "") -> set[str]:
            result: set[str] = set()
            for k, v in d.items():
                full = f"{prefix}.{k}" if prefix else k
                result.add(full)
                if isinstance(v, dict):
                    result |= _flatten(v, full)
            return result

        strings_keys = _flatten(_load("strings.json"))
        en_keys = _flatten(_load("translations/en.json"))
        zh_keys = _flatten(_load("translations/zh-Hans.json"))

        assert strings_keys == en_keys, (
            f"Key mismatch between strings.json and en.json:\n"
            f"  In strings only: {strings_keys - en_keys}\n"
            f"  In en only: {en_keys - strings_keys}"
        )
        assert strings_keys == zh_keys, (
            f"Key mismatch between strings.json and zh-Hans.json:\n"
            f"  In strings only: {strings_keys - zh_keys}\n"
            f"  In zh only: {zh_keys - strings_keys}"
        )
