"""Direct tests for _pure_helpers.parse_codex_toml and validate_base_url.

These functions are pure Python with no HA dependencies, so we test them
directly here.  The package import still loads __init__.py, so ha_stubs must
be bootstrapped first.
"""

from __future__ import annotations

import os
import sys

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

    def test_store_responses_absent_when_key_missing(self) -> None:
        """When ``disable_response_storage`` is absent from the TOML,
        ``store_responses`` must NOT appear in the returned dict.

        The caller (``_parse_toml_and_validate``) falls back to
        ``DEFAULT_STORE`` via ``parsed.store_responses`` — which is set to the
        default before TOML values are applied.  If ``parse_codex_toml``
        unconditionally added ``store_responses=True`` here, it would silently
        override a user's manual form selection whenever they also pasted a TOML
        snippet that lacked the key.

        Complements test_disable_response_storage_false_means_store_true which
        pins the mapping *when the key is present*; this test pins the *absence*
        of the key when it should be absent."""
        toml = '[model_providers.p]\nbase_url = "https://x.com"\n'
        result = parse_codex_toml(toml)
        assert "store_responses" not in result, (
            "store_responses must be absent when disable_response_storage is "
            "not in the TOML — its presence would override the caller's default"
        )

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
        import tomllib

        with pytest.raises(tomllib.TOMLDecodeError):
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

    def test_integer_base_url_coerced_to_string(self) -> None:
        """If a provider has a non-string base_url (TOML allows integers), it
        must be str()-coerced rather than crashing."""
        toml = """
[model_providers.p]
base_url = 42
"""
        result = parse_codex_toml(toml)
        assert result["base_url"] == "42"

    def test_provider_missing_base_url_skipped(self) -> None:
        """A provider table without base_url must not produce a base_url key;
        iteration continues to the next provider if any."""
        toml = """
[model_providers.no_url]
api_key = "sk-xxx"
"""
        result = parse_codex_toml(toml)
        assert "base_url" not in result

    def test_base_url_with_surrounding_whitespace_stripped(self) -> None:
        """base_url values with leading/trailing whitespace in TOML must be
        stripped so downstream URL validation does not reject them with an
        'invalid_url_scheme' error (a URL starting with a space has no scheme).
        """
        toml = """
[model_providers.p]
base_url = "  https://proxy.example.com  "
"""
        result = parse_codex_toml(toml)
        assert result["base_url"] == "https://proxy.example.com"

    def test_non_dict_model_providers_value_ignored(self) -> None:
        """If model_providers is a non-dict type (e.g. a bare string from a
        hand-edited TOML), parse_codex_toml must not crash and must omit
        base_url rather than raising AttributeError on a non-dict iteration."""
        toml = 'model_providers = "not_a_table"\n'
        result = parse_codex_toml(toml)
        assert "base_url" not in result

    def test_reasoning_effort_with_whitespace_stripped(self) -> None:
        """model_reasoning_effort values with extra whitespace must be stripped
        (consistent with how model is handled).
        Note: model_reasoning_effort is a top-level TOML key, so it must appear
        before any section header in the test fixture."""
        toml = (
            'model_reasoning_effort = "  high  "\n[model_providers.p]\nbase_url = "https://x.com"\n'
        )
        result = parse_codex_toml(toml)
        assert result["reasoning_effort"] == "high"


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

    def test_ipv4_address_accepted(self) -> None:
        """Bare IP address hosts must be valid (common on local networks)."""
        assert validate_base_url("http://192.168.1.100:11434") is None

    def test_ipv6_address_accepted(self) -> None:
        """IPv6 bracket notation must be accepted."""
        assert validate_base_url("http://[::1]:8080") is None
