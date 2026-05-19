"""Direct tests for _pure_helpers.parse_codex_toml and validate_base_url.

These functions are pure Python with no HA dependencies, so we test them
directly here.  The package import still loads __init__.py, so ha_stubs must
be bootstrapped first.
"""
from __future__ import annotations

import sys
import os

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402

from custom_components.codex_proxy._pure_helpers import (  # noqa: E402
    parse_codex_toml,
    validate_base_url,
)


# ---------------------------------------------------------------------------
# parse_codex_toml
# ---------------------------------------------------------------------------


class TestParseCodexToml:
    def test_full_config(self) -> None:
        toml = """
model = "gpt-5.5"
model_reasoning_effort = "high"
disable_response_storage = true

[model_providers.codex]
base_url = "https://proxy.example.com/api"
"""
        result = parse_codex_toml(toml)
        assert result["model"] == "gpt-5.5"
        assert result["reasoning_effort"] == "high"
        assert result["store_responses"] is False
        assert result["base_url"] == "https://proxy.example.com/api"

    def test_no_provider_table_returns_no_base_url(self) -> None:
        toml = 'model = "gpt-5.5"\n'
        result = parse_codex_toml(toml)
        assert "base_url" not in result
        assert result["model"] == "gpt-5.5"

    def test_disable_response_storage_false_means_store_true(self) -> None:
        toml = "disable_response_storage = false\n"
        result = parse_codex_toml(toml)
        assert result["store_responses"] is True

    def test_strips_whitespace_from_model(self) -> None:
        toml = 'model = "  gpt-5.5  "\n'
        result = parse_codex_toml(toml)
        assert result["model"] == "gpt-5.5"

    def test_base_url_trailing_slash_stripped(self) -> None:
        toml = """
[model_providers.x]
base_url = "https://example.com/"
"""
        result = parse_codex_toml(toml)
        assert result["base_url"] == "https://example.com"

    def test_invalid_toml_raises(self) -> None:
        with pytest.raises(Exception):
            parse_codex_toml("not = valid [ toml")

    def test_non_string_model_ignored(self) -> None:
        toml = "model = 42\n"
        result = parse_codex_toml(toml)
        assert "model" not in result

    def test_empty_string_returns_empty_dict(self) -> None:
        result = parse_codex_toml("")
        assert result == {}

    def test_base_url_takes_first_provider(self) -> None:
        toml = """
[model_providers.alpha]
base_url = "https://first.example.com"

[model_providers.beta]
base_url = "https://second.example.com"
"""
        result = parse_codex_toml(toml)
        assert result["base_url"] == "https://first.example.com"


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
        assert validate_base_url("") == "invalid_url_scheme"

    def test_scheme_only_rejected(self) -> None:
        # "https://" has no netloc
        assert validate_base_url("https://") == "invalid_url"

    def test_https_with_path(self) -> None:
        assert validate_base_url("https://example.com/v1") is None

    def test_https_with_port(self) -> None:
        assert validate_base_url("https://example.com:9443") is None
