"""Tests for the codex_proxy config flow helpers.

These tests exercise _pure_helpers.py which has no HA runtime dependency,
so they run without a full HA install (great for CI / local dev).
"""

from __future__ import annotations

import importlib.util
import os
import tomllib

import pytest

# ---------------------------------------------------------------------------
# Load _pure_helpers.py directly by file path so we bypass the package
# __init__.py (which would fail without HA installed).
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HELPERS_PATH = os.path.join(_REPO_ROOT, "custom_components", "codex_proxy", "_pure_helpers.py")

_spec = importlib.util.spec_from_file_location("_pure_helpers", _HELPERS_PATH)
assert _spec and _spec.loader
_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helpers)  # type: ignore[union-attr]

parse_codex_toml = _helpers.parse_codex_toml
validate_base_url = _helpers.validate_base_url


# ---------------------------------------------------------------------------
# parse_codex_toml
# ---------------------------------------------------------------------------


class TestParseCodexToml:
    def test_full_config(self) -> None:
        toml = """
model = "gpt-5.5"
model_reasoning_effort = "xhigh"
disable_response_storage = true

[model_providers.myproxy]
base_url = "https://proxy.example.com"
wire_api = "responses"
"""
        result = parse_codex_toml(toml)
        assert result["model"] == "gpt-5.5"
        assert result["reasoning_effort"] == "xhigh"
        assert result["store_responses"] is False
        assert result["base_url"] == "https://proxy.example.com"

    def test_no_provider_table(self) -> None:
        toml = 'model = "gpt-5.5"\n'
        result = parse_codex_toml(toml)
        assert result["model"] == "gpt-5.5"
        assert "base_url" not in result

    def test_disable_response_storage_false(self) -> None:
        toml = "disable_response_storage = false\n"
        result = parse_codex_toml(toml)
        assert result["store_responses"] is True

    def test_strips_whitespace_from_model(self) -> None:
        toml = 'model = "  gpt-5.5  "\n'
        result = parse_codex_toml(toml)
        assert result["model"] == "gpt-5.5"

    def test_base_url_trailing_slash_stripped(self) -> None:
        toml = """
[model_providers.p]
base_url = "https://proxy.example.com/"
"""
        result = parse_codex_toml(toml)
        assert result["base_url"] == "https://proxy.example.com"

    def test_invalid_toml_raises(self) -> None:
        with pytest.raises(tomllib.TOMLDecodeError):
            parse_codex_toml("this is [not valid toml ][[[")

    def test_non_string_model_ignored(self) -> None:
        toml = "model = 42\n"
        result = parse_codex_toml(toml)
        assert "model" not in result

    def test_empty_string_returns_empty_dict(self) -> None:
        result = parse_codex_toml("")
        assert result == {}

    def test_base_url_takes_first_provider(self) -> None:
        toml = """
[model_providers.a]
base_url = "https://first.example.com"

[model_providers.b]
base_url = "https://second.example.com"
"""
        result = parse_codex_toml(toml)
        assert result["base_url"] in (
            "https://first.example.com",
            "https://second.example.com",
        )

    def test_base_url_is_first_not_second_provider(self) -> None:
        """When multiple model_providers tables are present, parse_codex_toml
        must return the URL from the *first* provider, not the second.

        test_base_url_takes_first_provider uses an ``in`` check that also
        passes if the second provider's URL is returned — which would accept
        a dict-iteration-order change that silently breaks users who configure
        multiple providers and expect the first one to take precedence.

        test_pure_helpers.py::test_base_url_takes_first_provider already pins
        this with exact equality; this test closes the same gap in test_config_flow.py
        which historically tested the same function under a different import path."""
        toml = """
[model_providers.a]
base_url = "https://first.example.com"

[model_providers.b]
base_url = "https://second.example.com"
"""
        result = parse_codex_toml(toml)
        assert result["base_url"] == "https://first.example.com", (
            f"Expected first provider URL, got {result['base_url']!r} — "
            "parse_codex_toml must use the first model_providers entry"
        )


# ---------------------------------------------------------------------------
# validate_base_url
# ---------------------------------------------------------------------------


class TestValidateBaseUrl:
    def test_valid_https(self) -> None:
        assert validate_base_url("https://proxy.example.com") is None

    def test_valid_http(self) -> None:
        assert validate_base_url("http://localhost:8080") is None

    def test_ftp_rejected(self) -> None:
        assert validate_base_url("ftp://proxy.example.com") == "invalid_url_scheme"

    def test_no_scheme_bare_hostname_rejected(self) -> None:
        assert validate_base_url("proxy.example.com") == "invalid_url_scheme"

    def test_empty_string_rejected(self) -> None:
        err = validate_base_url("")
        assert err is not None

    def test_scheme_only_rejected(self) -> None:
        assert validate_base_url("https://") == "invalid_url"

    def test_https_with_path(self) -> None:
        assert validate_base_url("https://proxy.example.com/v1") is None

    def test_https_with_port(self) -> None:
        assert validate_base_url("https://proxy.example.com:8443") is None
