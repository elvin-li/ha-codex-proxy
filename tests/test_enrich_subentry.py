"""Tests for _enrich_subentry_data and _upstream_keys in config_flow.py.

Exercises that service_tier=None is always pinned, llm_hass_api defaults to
[]), and that an existing base dict is preserved but overridden by new
user_input values.  Also covers the _upstream_keys() cache contract.
"""

from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# Bootstrap HA stubs before any codex_proxy import.
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402  — must precede codex_proxy imports

# Reset upstream key cache in case another test module already set it.
if "custom_components.codex_proxy.config_flow" in sys.modules:
    sys.modules["custom_components.codex_proxy.config_flow"]._UPSTREAM_KEYS_CACHE = None

from custom_components.codex_proxy.config_flow import (  # noqa: E402
    _enrich_subentry_data,
    _upstream_keys,
)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEnrichSubentryData:
    def test_service_tier_always_none(self) -> None:
        result = _enrich_subentry_data({"chat_model": "gpt-5.5"})
        assert result["service_tier"] is None

    def test_service_tier_overrides_caller_supplied_value(self) -> None:
        result = _enrich_subentry_data({"service_tier": "flex"})
        assert result["service_tier"] is None

    def test_llm_hass_api_defaults_to_empty_list(self) -> None:
        result = _enrich_subentry_data({"chat_model": "gpt-5.5"})
        assert result["llm_hass_api"] == []

    def test_existing_llm_hass_api_preserved(self) -> None:
        result = _enrich_subentry_data({"llm_hass_api": ["assist"]})
        assert result["llm_hass_api"] == ["assist"]

    def test_user_input_merged_into_base(self) -> None:
        base = {"chat_model": "gpt-5.5", "reasoning_effort": "medium"}
        new_input = {"reasoning_effort": "xhigh"}
        result = _enrich_subentry_data(new_input, base=base)
        assert result["chat_model"] == "gpt-5.5"
        assert result["reasoning_effort"] == "xhigh"

    def test_base_none_returns_clean_dict(self) -> None:
        result = _enrich_subentry_data({"chat_model": "gpt-5.5"}, base=None)
        assert "chat_model" in result
        assert "service_tier" in result

    def test_user_input_overrides_base_chat_model(self) -> None:
        base = {"chat_model": "gpt-5.5"}
        result = _enrich_subentry_data({"chat_model": "gpt-5.6"}, base=base)
        assert result["chat_model"] == "gpt-5.6"


# ---------------------------------------------------------------------------
# _upstream_keys caching
# ---------------------------------------------------------------------------


class TestUpstreamKeys:
    def _reset_cache(self) -> None:
        """Clear the module-level cache before each test."""
        import custom_components.codex_proxy.config_flow as cf

        cf._UPSTREAM_KEYS_CACHE = None

    def test_returns_dict_with_expected_keys(self) -> None:
        self._reset_cache()
        keys = _upstream_keys()
        for k in ("chat_model", "prompt", "reasoning_effort", "store_responses", "service_tier"):
            assert k in keys, f"Missing key: {k}"

    def test_all_values_are_non_empty_strings(self) -> None:
        self._reset_cache()
        keys = _upstream_keys()
        for k, v in keys.items():
            assert isinstance(v, str) and v, f"Key {k!r} has empty/non-string value: {v!r}"

    def test_second_call_returns_same_object(self) -> None:
        """Cache must be used — two calls must return the identical dict object."""
        self._reset_cache()
        first = _upstream_keys()
        second = _upstream_keys()
        assert first is second, "Cache miss: second call returned a different object"

    def test_cache_is_not_none_after_first_call(self) -> None:
        self._reset_cache()
        _upstream_keys()
        import custom_components.codex_proxy.config_flow as cf

        assert cf._UPSTREAM_KEYS_CACHE is not None
