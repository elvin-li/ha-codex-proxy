"""Tests for _parse_toml_and_validate in config_flow.py.

This is the combined TOML-parse-and-validate helper used by both the initial
setup step and the reconfigure step. It covers:
 - Manual form input (no TOML)
 - TOML with full set of keys
 - TOML with missing base_url (toml_no_base_url error)
 - Malformed TOML (bad_toml error)
 - Invalid URL schemes (invalid_url_scheme / invalid_url errors)
 - Missing base_url with no TOML (required error)
 - URL trailing-slash stripping
 - model default fallback
"""

from __future__ import annotations

import os
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap HA stubs BEFORE any codex_proxy import
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402  — must precede codex_proxy imports
from custom_components.codex_proxy.config_flow import _parse_toml_and_validate  # noqa: E402
from custom_components.codex_proxy.const import (  # noqa: E402
    CONF_API_KEY,
    CONF_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_STORE,
)

_CONF_TOML = "toml_config"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _input(
    api_key: str = "sk-test",
    base_url: str = "https://proxy.example.com",
    model: str = DEFAULT_MODEL,
    toml: str = "",
) -> dict[str, Any]:
    return {
        CONF_API_KEY: api_key,
        CONF_BASE_URL: base_url,
        "model": model,
        _CONF_TOML: toml,
    }


# ---------------------------------------------------------------------------
# Tests: manual form (no TOML)
# ---------------------------------------------------------------------------


class TestManualInput:
    def test_valid_input_no_errors(self) -> None:
        errors, api_key, base_url, model, _, _ = _parse_toml_and_validate(
            _input(api_key="sk-abc", base_url="https://proxy.example.com")
        )
        assert not errors
        assert api_key == "sk-abc"
        assert base_url == "https://proxy.example.com"

    def test_trailing_slash_stripped_from_base_url(self) -> None:
        errors, _, base_url, _, _, _ = _parse_toml_and_validate(
            _input(base_url="https://proxy.example.com/")
        )
        assert not errors
        assert base_url == "https://proxy.example.com"

    def test_model_defaults_when_empty(self) -> None:
        errors, _, _, model, _, _ = _parse_toml_and_validate(_input(model=""))
        assert model == DEFAULT_MODEL

    def test_model_preserved_when_set(self) -> None:
        errors, _, _, model, _, _ = _parse_toml_and_validate(_input(model="gpt-5.6"))
        assert model == "gpt-5.6"

    def test_missing_base_url_returns_required_error(self) -> None:
        errors, _, _, _, _, _ = _parse_toml_and_validate(_input(base_url=""))
        assert CONF_BASE_URL in errors
        assert errors[CONF_BASE_URL] == "required"

    def test_ftp_scheme_returns_invalid_url_scheme(self) -> None:
        errors, _, _, _, _, _ = _parse_toml_and_validate(_input(base_url="ftp://proxy.example.com"))
        assert errors.get(CONF_BASE_URL) == "invalid_url_scheme"

    def test_no_scheme_returns_invalid_url_scheme(self) -> None:
        errors, _, _, _, _, _ = _parse_toml_and_validate(_input(base_url="proxy.example.com"))
        assert errors.get(CONF_BASE_URL) == "invalid_url_scheme"

    def test_https_no_host_returns_invalid_url(self) -> None:
        errors, _, _, _, _, _ = _parse_toml_and_validate(_input(base_url="https://"))
        assert errors.get(CONF_BASE_URL) == "invalid_url"

    def test_http_url_valid(self) -> None:
        errors, _, base_url, _, _, _ = _parse_toml_and_validate(
            _input(base_url="http://localhost:8080")
        )
        assert not errors
        assert "localhost" in base_url

    def test_base_url_with_surrounding_whitespace_stripped(self) -> None:
        """A manually pasted URL with extra leading/trailing spaces must be
        accepted and stripped — a common paste-from-browser artifact."""
        errors, _, base_url, _, _, _ = _parse_toml_and_validate(
            _input(base_url="  https://proxy.example.com  ")
        )
        assert not errors
        assert base_url == "https://proxy.example.com"


# ---------------------------------------------------------------------------
# Tests: TOML input
# ---------------------------------------------------------------------------


class TestTomlInput:
    def test_toml_provides_base_url(self) -> None:
        toml = """
[model_providers.p]
base_url = "https://from-toml.example.com"
"""
        errors, _, base_url, _, _, _ = _parse_toml_and_validate(_input(base_url="", toml=toml))
        assert not errors
        assert base_url == "https://from-toml.example.com"

    def test_toml_overrides_manual_base_url(self) -> None:
        toml = """
[model_providers.p]
base_url = "https://from-toml.example.com"
"""
        errors, _, base_url, _, _, _ = _parse_toml_and_validate(
            _input(base_url="https://manual.example.com", toml=toml)
        )
        assert not errors
        assert base_url == "https://from-toml.example.com"

    def test_toml_sets_model(self) -> None:
        toml = 'model = "gpt-5.6"\n[model_providers.p]\nbase_url = "https://x.com"\n'
        errors, _, _, model, _, _ = _parse_toml_and_validate(_input(base_url="", toml=toml))
        assert not errors
        assert model == "gpt-5.6"

    def test_toml_sets_reasoning_effort(self) -> None:
        toml = (
            'model_reasoning_effort = "medium"\n[model_providers.p]\nbase_url = "https://x.com"\n'
        )
        errors, _, _, _, reasoning_effort, _ = _parse_toml_and_validate(
            _input(base_url="", toml=toml)
        )
        assert not errors
        assert reasoning_effort == "medium"

    def test_toml_sets_store_responses_false(self) -> None:
        toml = 'disable_response_storage = true\n[model_providers.p]\nbase_url = "https://x.com"\n'
        errors, _, _, _, _, store = _parse_toml_and_validate(_input(base_url="", toml=toml))
        assert not errors
        assert store is False

    def test_toml_no_base_url_returns_error(self) -> None:
        toml = 'model = "gpt-5.5"\n'  # no model_providers table
        errors, _, _, _, _, _ = _parse_toml_and_validate(_input(base_url="", toml=toml))
        assert errors.get("base") == "toml_no_base_url"

    def test_bad_toml_returns_bad_toml_error(self) -> None:
        errors, _, _, _, _, _ = _parse_toml_and_validate(
            _input(base_url="", toml="this [ is not [ valid toml")
        )
        assert errors.get("base") == "bad_toml"

    def test_toml_trailing_slash_stripped(self) -> None:
        toml = '[model_providers.p]\nbase_url = "https://x.example.com/"\n'
        errors, _, base_url, _, _, _ = _parse_toml_and_validate(_input(base_url="", toml=toml))
        assert not errors
        assert not base_url.endswith("/")

    def test_defaults_preserved_when_toml_empty_string(self) -> None:
        errors, _, _, _, reasoning_effort, store = _parse_toml_and_validate(
            _input(base_url="https://proxy.example.com", toml="")
        )
        assert not errors
        assert reasoning_effort == DEFAULT_REASONING_EFFORT
        assert store == DEFAULT_STORE

    def test_invalid_reasoning_effort_from_toml_uses_default(self) -> None:
        """A TOML with an unrecognised model_reasoning_effort value must not
        be stored; the default effort should be used instead and no error
        should be returned (the flow continues with a warning logged)."""
        toml = (
            'model_reasoning_effort = "turbo"\n'
            '[model_providers.p]\nbase_url = "https://proxy.example.com"\n'
        )
        errors, _, _, _, reasoning_effort, _ = _parse_toml_and_validate(
            _input(base_url="", toml=toml)
        )
        assert not errors
        assert reasoning_effort == DEFAULT_REASONING_EFFORT

    def test_valid_reasoning_effort_from_toml_used(self) -> None:
        """Known effort values from TOML are accepted without any error."""
        from custom_components.codex_proxy.const import REASONING_EFFORTS  # noqa: E402

        for effort in REASONING_EFFORTS:
            toml = (
                f'model_reasoning_effort = "{effort}"\n'
                '[model_providers.p]\nbase_url = "https://proxy.example.com"\n'
            )
            errors, _, _, _, reasoning_effort, _ = _parse_toml_and_validate(
                _input(base_url="", toml=toml)
            )
            assert not errors, f"unexpected error for effort={effort}: {errors}"
            assert reasoning_effort == effort
