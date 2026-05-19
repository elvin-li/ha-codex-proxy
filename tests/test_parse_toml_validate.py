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
        result = _parse_toml_and_validate(
            _input(api_key="sk-abc", base_url="https://proxy.example.com")
        )
        assert not result.errors
        assert result.api_key == "sk-abc"
        assert result.base_url == "https://proxy.example.com"

    def test_trailing_slash_stripped_from_base_url(self) -> None:
        result = _parse_toml_and_validate(_input(base_url="https://proxy.example.com/"))
        assert not result.errors
        assert result.base_url == "https://proxy.example.com"

    def test_model_defaults_when_empty(self) -> None:
        result = _parse_toml_and_validate(_input(model=""))
        assert result.model == DEFAULT_MODEL

    def test_model_preserved_when_set(self) -> None:
        result = _parse_toml_and_validate(_input(model="gpt-5.6"))
        assert result.model == "gpt-5.6"

    def test_missing_base_url_returns_required_error(self) -> None:
        result = _parse_toml_and_validate(_input(base_url=""))
        assert CONF_BASE_URL in result.errors
        assert result.errors[CONF_BASE_URL] == "required"

    def test_ftp_scheme_returns_invalid_url_scheme(self) -> None:
        result = _parse_toml_and_validate(_input(base_url="ftp://proxy.example.com"))
        assert result.errors.get(CONF_BASE_URL) == "invalid_url_scheme"

    def test_no_scheme_returns_invalid_url_scheme(self) -> None:
        result = _parse_toml_and_validate(_input(base_url="proxy.example.com"))
        assert result.errors.get(CONF_BASE_URL) == "invalid_url_scheme"

    def test_https_no_host_returns_invalid_url(self) -> None:
        result = _parse_toml_and_validate(_input(base_url="https://"))
        assert result.errors.get(CONF_BASE_URL) == "invalid_url"

    def test_http_url_valid(self) -> None:
        result = _parse_toml_and_validate(_input(base_url="http://localhost:8080"))
        assert not result.errors
        assert "localhost" in result.base_url

    def test_http_url_exact_value_preserved(self) -> None:
        """A valid HTTP URL must be stored verbatim (port included) in result.base_url.

        test_http_url_valid uses a substring check ('localhost' in base_url)
        which passes even if the port ':8080' is stripped or the scheme is
        changed to 'https'.  Exact equality ensures the full URL survives
        _parse_toml_and_validate without modification."""
        result = _parse_toml_and_validate(_input(base_url="http://localhost:8080"))
        assert result.base_url == "http://localhost:8080", (
            f"Expected 'http://localhost:8080', got {result.base_url!r} — "
            "the URL must be preserved exactly (including port) by _parse_toml_and_validate"
        )

    def test_base_url_with_surrounding_whitespace_stripped(self) -> None:
        """A manually pasted URL with extra leading/trailing spaces must be
        accepted and stripped — a common paste-from-browser artifact."""
        result = _parse_toml_and_validate(_input(base_url="  https://proxy.example.com  "))
        assert not result.errors
        assert result.base_url == "https://proxy.example.com"


# ---------------------------------------------------------------------------
# Tests: TOML input
# ---------------------------------------------------------------------------


class TestTomlInput:
    def test_toml_provides_base_url(self) -> None:
        toml = """
[model_providers.p]
base_url = "https://from-toml.example.com"
"""
        result = _parse_toml_and_validate(_input(base_url="", toml=toml))
        assert not result.errors
        assert result.base_url == "https://from-toml.example.com"

    def test_toml_overrides_manual_base_url(self) -> None:
        toml = """
[model_providers.p]
base_url = "https://from-toml.example.com"
"""
        result = _parse_toml_and_validate(
            _input(base_url="https://manual.example.com", toml=toml)
        )
        assert not result.errors
        assert result.base_url == "https://from-toml.example.com"

    def test_toml_sets_model(self) -> None:
        toml = 'model = "gpt-5.6"\n[model_providers.p]\nbase_url = "https://x.com"\n'
        result = _parse_toml_and_validate(_input(base_url="", toml=toml))
        assert not result.errors
        assert result.model == "gpt-5.6"

    def test_toml_sets_reasoning_effort(self) -> None:
        toml = (
            'model_reasoning_effort = "medium"\n[model_providers.p]\nbase_url = "https://x.com"\n'
        )
        result = _parse_toml_and_validate(_input(base_url="", toml=toml))
        assert not result.errors
        assert result.reasoning_effort == "medium"

    def test_toml_sets_store_responses_false(self) -> None:
        toml = 'disable_response_storage = true\n[model_providers.p]\nbase_url = "https://x.com"\n'
        result = _parse_toml_and_validate(_input(base_url="", toml=toml))
        assert not result.errors
        assert result.store_responses is False

    def test_toml_no_base_url_returns_error(self) -> None:
        toml = 'model = "gpt-5.5"\n'  # no model_providers table
        result = _parse_toml_and_validate(_input(base_url="", toml=toml))
        assert result.errors.get("base") == "toml_no_base_url"

    def test_bad_toml_returns_bad_toml_error(self) -> None:
        result = _parse_toml_and_validate(
            _input(base_url="", toml="this [ is not [ valid toml")
        )
        assert result.errors.get("base") == "bad_toml"

    def test_toml_trailing_slash_stripped(self) -> None:
        toml = '[model_providers.p]\nbase_url = "https://x.example.com/"\n'
        result = _parse_toml_and_validate(_input(base_url="", toml=toml))
        assert not result.errors
        assert not result.base_url.endswith("/")

    def test_defaults_preserved_when_toml_empty_string(self) -> None:
        result = _parse_toml_and_validate(
            _input(base_url="https://proxy.example.com", toml="")
        )
        assert not result.errors
        assert result.reasoning_effort == DEFAULT_REASONING_EFFORT
        assert result.store_responses == DEFAULT_STORE

    def test_invalid_reasoning_effort_from_toml_uses_default(self) -> None:
        """A TOML with an unrecognised model_reasoning_effort value must not
        be stored; the default effort should be used instead and no error
        should be returned (the flow continues with a warning logged)."""
        toml = (
            'model_reasoning_effort = "turbo"\n'
            '[model_providers.p]\nbase_url = "https://proxy.example.com"\n'
        )
        result = _parse_toml_and_validate(_input(base_url="", toml=toml))
        assert not result.errors
        assert result.reasoning_effort == DEFAULT_REASONING_EFFORT

    def test_valid_reasoning_effort_from_toml_used(self) -> None:
        """Known effort values from TOML are accepted without any error."""
        from custom_components.codex_proxy.const import REASONING_EFFORTS  # noqa: E402

        for effort in REASONING_EFFORTS:
            toml = (
                f'model_reasoning_effort = "{effort}"\n'
                '[model_providers.p]\nbase_url = "https://proxy.example.com"\n'
            )
            result = _parse_toml_and_validate(_input(base_url="", toml=toml))
            assert not result.errors, f"unexpected error for effort={effort}: {result.errors}"
            assert result.reasoning_effort == effort


# ---------------------------------------------------------------------------
# Tests: api_key whitespace stripping
# ---------------------------------------------------------------------------


class TestApiKeyStripping:
    def test_api_key_leading_whitespace_stripped(self) -> None:
        """A key pasted with a leading space must be silently trimmed so the
        user doesn't receive a cryptic 'invalid_auth' from the proxy."""
        result = _parse_toml_and_validate(_input(api_key="  sk-abc"))
        assert result.api_key == "sk-abc"

    def test_api_key_trailing_whitespace_stripped(self) -> None:
        """Trailing whitespace (common when copy-pasting from a terminal) must
        be stripped before the key is stored or used in the probe."""
        result = _parse_toml_and_validate(_input(api_key="sk-abc  "))
        assert result.api_key == "sk-abc"

    def test_api_key_surrounding_whitespace_stripped(self) -> None:
        """Both leading and trailing whitespace stripped in one pass."""
        result = _parse_toml_and_validate(_input(api_key="  sk-abc  "))
        assert result.api_key == "sk-abc"

    def test_api_key_no_whitespace_unchanged(self) -> None:
        """A key without whitespace is returned as-is — strip is a no-op."""
        result = _parse_toml_and_validate(_input(api_key="sk-abc-123"))
        assert result.api_key == "sk-abc-123"

    def test_api_key_internal_whitespace_preserved(self) -> None:
        """strip() must NOT remove internal spaces (unusual but possible in
        custom proxy keys). Only leading/trailing whitespace is removed."""
        result = _parse_toml_and_validate(_input(api_key=" sk abc "))
        assert result.api_key == "sk abc"


# ---------------------------------------------------------------------------
# Tests: _ParseResult NamedTuple named attribute access
# ---------------------------------------------------------------------------


class TestParseResultNamedAccess:
    """Verify that callers can use named field access instead of positional
    unpacking — guards the ``_ParseResult`` NamedTuple contract."""

    def test_errors_attribute(self) -> None:
        result = _parse_toml_and_validate(_input())
        assert not result.errors

    def test_api_key_attribute(self) -> None:
        result = _parse_toml_and_validate(_input(api_key="sk-named"))
        assert result.api_key == "sk-named"

    def test_base_url_attribute(self) -> None:
        result = _parse_toml_and_validate(_input(base_url="https://named.example.com"))
        assert result.base_url == "https://named.example.com"

    def test_model_attribute(self) -> None:
        result = _parse_toml_and_validate(_input(model="gpt-named"))
        assert result.model == "gpt-named"

    def test_reasoning_effort_attribute(self) -> None:
        result = _parse_toml_and_validate(_input())
        assert result.reasoning_effort == DEFAULT_REASONING_EFFORT

    def test_store_responses_attribute(self) -> None:
        result = _parse_toml_and_validate(_input())
        assert isinstance(result.store_responses, bool)

    def test_positional_unpacking_still_works(self) -> None:
        """NamedTuple is a tuple subclass — positional unpacking must not break."""
        errors, api_key, base_url, model, reasoning_effort, store_responses = (
            _parse_toml_and_validate(_input(api_key="sk-pos"))
        )
        assert api_key == "sk-pos"
        assert isinstance(store_responses, bool)
