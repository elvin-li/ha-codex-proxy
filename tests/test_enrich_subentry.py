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

    def test_base_none_exact_key_set(self) -> None:
        """When base=None and a single-key user_input is passed, the returned
        dict must contain exactly three keys: the user-supplied key, 'service_tier'
        (always pinned to None), and 'llm_hass_api' (defaulted to []).

        test_base_none_returns_clean_dict checks only that two keys are *present*
        using 'in'; it passes even if extra keys leak into the dict (e.g. a stray
        debug key or a future default added without updating tests).  Exact set
        equality here catches both omissions and accidental additions in one
        assertion, mirroring the exact-key pattern in test_coordinator_init.py
        and test_diagnostics.py."""
        result = _enrich_subentry_data({"chat_model": "gpt-5.5"}, base=None)
        expected_keys = {"chat_model", "service_tier", "llm_hass_api"}
        actual_keys = set(result.keys())
        assert actual_keys == expected_keys, (
            f"Unexpected keys: {actual_keys - expected_keys}. "
            f"Missing: {expected_keys - actual_keys}."
        )

    def test_user_input_overrides_base_chat_model(self) -> None:
        base = {"chat_model": "gpt-5.5"}
        result = _enrich_subentry_data({"chat_model": "gpt-5.6"}, base=base)
        assert result["chat_model"] == "gpt-5.6"

    def test_base_dict_not_mutated(self) -> None:
        """The caller's ``base`` dict must not be mutated by _enrich_subentry_data.

        The function creates a copy (``dict(base)``) before applying updates;
        callers typically pass a live subentry's ``.data`` dict as ``base`` when
        reconfiguring.  A refactor that removed the copy (writing directly into
        ``base``) would silently persist service_tier=None and the new model
        into the caller's dict between calls — caught here, invisible to
        test_user_input_overrides_base_chat_model which only checks the return
        value."""
        base = {"chat_model": "gpt-5.5", "reasoning_effort": "high"}
        original_base_copy = dict(base)
        _enrich_subentry_data({"chat_model": "gpt-5.6"}, base=base)
        assert base == original_base_copy, (
            "base dict was mutated — _enrich_subentry_data must copy base "
            "before applying updates so the caller's original data is preserved"
        )


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

    def test_upstream_keys_exact_key_set(self) -> None:
        """_upstream_keys() must return a dict with exactly the five expected
        logical keys — no more, no less.

        test_returns_dict_with_expected_keys uses a for-loop with five ``in``
        checks that pass even if a sixth unexpected key is accidentally added
        (e.g. ``"chat_model_id"`` from a copy-paste of a newer HA const).
        An extra key would propagate into the subentry data dict on every
        reconfigure, silently injecting unknown fields into HA's config storage.
        Exact set equality catches that before it reaches users."""
        self._reset_cache()
        keys = _upstream_keys()
        expected_keys = {
            "chat_model",
            "prompt",
            "reasoning_effort",
            "store_responses",
            "service_tier",
        }
        assert set(keys.keys()) == expected_keys, (
            f"Unexpected _upstream_keys keys: {set(keys.keys()) - expected_keys}. "
            f"Missing: {expected_keys - set(keys.keys())}."
        )

    def test_all_values_are_non_empty_strings(self) -> None:
        self._reset_cache()
        keys = _upstream_keys()
        for k, v in keys.items():
            assert isinstance(v, str) and v, f"Key {k!r} has empty/non-string value: {v!r}"

    def test_upstream_keys_exact_values(self) -> None:
        """Each logical key must map to the exact HA const value (or the
        fallback literal) that the integration uses to read subentry data.

        test_all_values_are_non_empty_strings only checks ``isinstance(v, str)
        and v`` — any non-empty string passes, including a swapped or typo'd
        value.  Pinning the exact mapping ensures that if the HA upstream const
        ever renames e.g. ``CONF_CHAT_MODEL`` from 'chat_model' to 'model', the
        test fails immediately rather than silently writing data under the wrong
        key and producing a broken conversation entity."""
        self._reset_cache()
        keys = _upstream_keys()
        # Under ha_stubs the fallback literals are used; each key maps to itself.
        assert keys["chat_model"] == "chat_model", (
            f"Expected keys['chat_model'] == 'chat_model', got {keys['chat_model']!r}"
        )
        assert keys["prompt"] == "prompt", (
            f"Expected keys['prompt'] == 'prompt', got {keys['prompt']!r}"
        )
        assert keys["reasoning_effort"] == "reasoning_effort", (
            f"Expected keys['reasoning_effort'] == 'reasoning_effort', "
            f"got {keys['reasoning_effort']!r}"
        )
        assert keys["store_responses"] == "store_responses", (
            f"Expected keys['store_responses'] == 'store_responses', "
            f"got {keys['store_responses']!r}"
        )
        assert keys["service_tier"] == "service_tier", (
            f"Expected keys['service_tier'] == 'service_tier', got {keys['service_tier']!r}"
        )

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
