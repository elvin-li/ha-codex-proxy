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
    normalize_base_url,
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

    def test_full_config_exact_key_set(self) -> None:
        """A fully-populated TOML must produce exactly four keys in the result dict.

        test_full_config checks the four expected values but does not pin the key
        set.  An implementation that accidentally added a fifth key (e.g. an
        intermediate 'model_providers' dump or a debug key) would pass the per-value
        tests but leak unexpected data into the config-flow step.  Exact set equality
        catches that regression in one assertion."""
        toml = """
model = "gpt-5.5"
model_reasoning_effort = "high"
disable_response_storage = true

[model_providers.codex]
base_url = "https://proxy.example.com/api"
"""
        result = parse_codex_toml(toml)
        expected_keys = {"model", "reasoning_effort", "store_responses", "base_url"}
        assert set(result.keys()) == expected_keys, (
            f"Unexpected keys: {set(result.keys()) - expected_keys}. "
            f"Missing: {expected_keys - set(result.keys())}."
        )

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

    def test_url_with_query_rejected(self) -> None:
        """A base URL with a query string is almost always a copy-paste
        artefact (the user pasted a deep-linked URL from their browser).
        Leaving the query in place would corrupt the URL after
        ``normalize_base_url`` appends ``/v1`` — ``https://host?x=1`` becomes
        ``https://host?x=1/v1`` and the OpenAI SDK emits requests to
        ``https://host?x=1/v1/responses`` (404 against any sane proxy).
        Reject upfront so the user sees an inline form error."""
        assert validate_base_url("https://proxy.example.com?token=abc") == "invalid_url"

    def test_url_with_fragment_rejected(self) -> None:
        """Same reasoning as the query-string case — fragments are a paste
        artefact and corrupt the URL after ``/v1`` appending."""
        assert validate_base_url("https://proxy.example.com#section") == "invalid_url"

    def test_url_with_both_query_and_fragment_rejected(self) -> None:
        assert validate_base_url("https://proxy.example.com?x=1#y") == "invalid_url"

    def test_url_with_userinfo_rejected(self) -> None:
        """Round-3 audit Critical finding regression.

        ``https://user:pass@proxy.example.com`` is technically a valid URL
        but the userinfo part is a credential that would silently flow into:
        - ``entry.data["base_url"]`` (persisted in core.config_entries)
        - ``self._url`` in coordinator exception messages
        - The debug log line ``Probing proxy at %s with model %s``
        - The unredacted ``entry_data`` block of diagnostics downloads
        - The ``binary_sensor.proxy_reachable.last_error`` state attribute

        Token-pool proxies frequently document credentialed URLs in
        onboarding pages, so a user pasting from such a doc would
        unknowingly exfiltrate their password into HA's persistent storage
        and any bug report that includes the downloadable diagnostics
        file.  Reject upfront."""
        assert validate_base_url("https://user:pass@proxy.example.com") == "invalid_url", (
            "URLs with userinfo must be rejected — credentials in the URL "
            "would silently flow into HA storage, logs, and diagnostics"
        )

    def test_url_with_username_only_rejected(self) -> None:
        """A bare username (no password) is also userinfo — common in
        proxies that use a single-token auth scheme embedded in the URL.
        Must be rejected for the same reason as full user:pass."""
        assert validate_base_url("https://token@proxy.example.com") == "invalid_url"

    def test_url_with_empty_password_rejected(self) -> None:
        """``https://user:@host`` is parsed as username=user, password=''.
        urlparse exposes password as the empty string (not None) in this
        case — verify the rejection still fires (we check ``is not None``,
        not truthiness)."""
        assert validate_base_url("https://user:@proxy.example.com") == "invalid_url"


# ---------------------------------------------------------------------------
# normalize_base_url
# ---------------------------------------------------------------------------


class TestNormalizeBaseUrl:
    def test_bare_host_gets_v1_appended(self) -> None:
        """https://proxy.example.com → https://proxy.example.com/v1.

        Without the /v1 suffix the OpenAI SDK hits /responses instead of
        /v1/responses; strict proxies return their HTML landing page (HTTP 200
        text/html) and HA surfaces it as 'Last content in chat log is not an
        AssistantContent' — extremely hard to diagnose without packet capture.
        """
        assert normalize_base_url("https://proxy.example.com") == "https://proxy.example.com/v1"

    def test_already_normalised_unchanged(self) -> None:
        """An already-normalised URL must round-trip verbatim — no double /v1."""
        assert normalize_base_url("https://proxy.example.com/v1") == "https://proxy.example.com/v1"

    def test_trailing_slash_on_bare_host_stripped_before_append(self) -> None:
        assert normalize_base_url("https://proxy.example.com/") == "https://proxy.example.com/v1"

    def test_trailing_slash_on_v1_stripped(self) -> None:
        """https://proxy.example.com/v1/ → strip trailing slash, leave /v1."""
        assert normalize_base_url("https://proxy.example.com/v1/") == "https://proxy.example.com/v1"

    def test_vendor_prefix_with_v1_preserved(self) -> None:
        """Path-prefixed proxies (e.g. ``/api/v1``) must be left alone — the
        suffix detection looks only at the *last* path segment."""
        assert (
            normalize_base_url("https://proxy.example.com/api/v1")
            == "https://proxy.example.com/api/v1"
        )

    def test_v1_substring_in_path_not_match(self) -> None:
        """A path ending in something like 'v1beta' must not be treated as
        already-normalised — only an exact 'v1' final segment counts.

        Without this guard, ``https://proxy.example.com/v1beta`` would be
        returned unchanged and the SDK would hit
        ``https://proxy.example.com/v1beta/responses`` (probably 404).
        """
        assert (
            normalize_base_url("https://proxy.example.com/v1beta")
            == "https://proxy.example.com/v1beta/v1"
        )

    def test_http_localhost_with_port(self) -> None:
        """Local dev proxies (no /v1) must still get /v1 appended."""
        assert normalize_base_url("http://localhost:8080") == "http://localhost:8080/v1"

    def test_idempotent(self) -> None:
        """Applying normalize_base_url twice must return the same value as
        applying it once.  This guarantees that lazy migration in
        async_setup_entry doesn't keep rewriting entry.data on every restart."""
        once = normalize_base_url("https://proxy.example.com")
        twice = normalize_base_url(once)
        assert once == twice, f"normalize_base_url is not idempotent: {once!r} != {twice!r}"

    def test_bare_hostname_v1_not_mistaken_for_path(self) -> None:
        """Round-4 audit regression: ``https://v1`` has ``v1`` as the
        HOSTNAME, not a path segment.

        The pre-v0.2.175 implementation did ``url.rstrip("/").rsplit("/", 1)``
        on the raw URL string — for ``https://v1`` that returns
        ``["https:", "", "v1"]`` and last == "v1", so the URL was treated as
        already-normalised and returned unchanged.  The coordinator would
        then build ``https://v1/models`` instead of ``https://v1/v1/models``,
        and a strict proxy would 404.

        Vanishingly unlikely in practice (who names their server ``v1``?)
        but a real correctness bug.  The fix parses the URL with urlparse
        and looks only at the path component."""
        assert normalize_base_url("https://v1") == "https://v1/v1", (
            "A URL whose HOST is 'v1' must still get /v1 appended — only a "
            "PATH ending in /v1 should be left alone"
        )

    def test_bare_hostname_with_trailing_slash_v1_handled(self) -> None:
        """Edge case companion to test_bare_hostname_v1_not_mistaken_for_path
        — ``https://v1/`` (trailing slash) should also normalise to
        ``https://v1/v1``."""
        assert normalize_base_url("https://v1/") == "https://v1/v1"
