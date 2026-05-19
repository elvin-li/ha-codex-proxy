"""Tests for constants in custom_components/codex_proxy/const.py.

Guards against accidental changes to values that other code (and the live
HA integration) depends on.
"""

from __future__ import annotations

import os
import sys
from datetime import timedelta

# Bootstrap HA stubs — importing from the package loads __init__.py which needs HA
import tests.ha_stubs  # noqa: F401, E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.codex_proxy.const import (
    CODEX_OPENAI_BETA,
    CODEX_ORIGINATOR,
    CODEX_USER_AGENT,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_INSTALLATION_ID,
    COORDINATOR_MAX_RETRIES,
    COORDINATOR_RETRY_DELAYS,
    COORDINATOR_TIMEOUT_S,
    DATA_COORDINATOR,
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_STORE,
    DOMAIN,
    IMAGE_MODEL_ID_PREFIXES,
    LLM_BEARING_SUBENTRY_TYPES,
    MODEL_REFRESH_INTERVAL,
    PROBE_TIMEOUT_S,
    REASONING_EFFORTS,
    SUBENTRY_TYPE_AI_TASK,
    SUBENTRY_TYPE_CONVERSATION,
)


class TestDomain:
    def test_domain_value(self) -> None:
        assert DOMAIN == "codex_proxy"


class TestConfKeys:
    def test_conf_api_key(self) -> None:
        assert CONF_API_KEY == "api_key"

    def test_conf_base_url(self) -> None:
        assert CONF_BASE_URL == "base_url"

    def test_conf_installation_id(self) -> None:
        assert CONF_INSTALLATION_ID == "codex_installation_id"

    def test_data_coordinator_key(self) -> None:
        assert DATA_COORDINATOR == "coordinator"


class TestSubentryTypes:
    def test_conversation_type(self) -> None:
        assert SUBENTRY_TYPE_CONVERSATION == "conversation"

    def test_ai_task_type(self) -> None:
        assert SUBENTRY_TYPE_AI_TASK == "ai_task_data"

    def test_llm_bearing_contains_both_types(self) -> None:
        assert SUBENTRY_TYPE_CONVERSATION in LLM_BEARING_SUBENTRY_TYPES
        assert SUBENTRY_TYPE_AI_TASK in LLM_BEARING_SUBENTRY_TYPES

    def test_llm_bearing_is_tuple(self) -> None:
        assert isinstance(LLM_BEARING_SUBENTRY_TYPES, tuple)

    def test_llm_bearing_contains_exactly_both_types(self) -> None:
        """LLM_BEARING_SUBENTRY_TYPES must contain *exactly* the two expected
        types — no more, no less.

        test_llm_bearing_contains_both_types uses ``in`` checks which pass even
        if an extra type is accidentally added (e.g. ``"light"`` from a misapplied
        copy-paste).  An extra type would cause every 'light' subentry to produce
        a model-select and update entity, flooding the device registry with
        spurious entities.  Exact set equality catches that without needing to
        enumerate every possible platform name."""
        assert set(LLM_BEARING_SUBENTRY_TYPES) == {
            SUBENTRY_TYPE_CONVERSATION,
            SUBENTRY_TYPE_AI_TASK,
        }, (
            f"LLM_BEARING_SUBENTRY_TYPES contains unexpected values: "
            f"{set(LLM_BEARING_SUBENTRY_TYPES) - {SUBENTRY_TYPE_CONVERSATION, SUBENTRY_TYPE_AI_TASK}}"
        )


class TestDefaults:
    def test_default_model_is_non_empty(self) -> None:
        assert DEFAULT_MODEL and isinstance(DEFAULT_MODEL, str)

    def test_default_model_value(self) -> None:
        """DEFAULT_MODEL is used as the subentry fallback when no model has been
        explicitly configured.  Changing it without a migration would silently
        revert users' configurations, so we pin the exact value here."""
        assert DEFAULT_MODEL == "gpt-5.5"

    def test_default_reasoning_effort_in_reasoning_efforts(self) -> None:
        assert DEFAULT_REASONING_EFFORT in REASONING_EFFORTS

    def test_default_reasoning_effort_value(self) -> None:
        """Pin the exact DEFAULT_REASONING_EFFORT value.

        Changing it would silently alter inference cost and latency for every
        new subentry created after the change, so we guard it explicitly here.
        """
        assert DEFAULT_REASONING_EFFORT == "xhigh"

    def test_reasoning_efforts_contains_expected_values(self) -> None:
        for effort in ("none", "medium", "high", "xhigh"):
            assert effort in REASONING_EFFORTS

    def test_reasoning_efforts_is_tuple(self) -> None:
        """REASONING_EFFORTS must be a tuple, not a list.

        voluptuous schemas and HA's SelectSelector both accept
        an iterable of strings, but pinning the type to tuple documents
        the intent that this constant is immutable and catches any accidental
        conversion to a mutable list that could introduce subtle ordering
        or mutation bugs at runtime.
        """
        assert isinstance(REASONING_EFFORTS, tuple)

    def test_default_store_is_false(self) -> None:
        assert DEFAULT_STORE is False

    def test_default_prompt_is_empty_string(self) -> None:
        """DEFAULT_PROMPT must be empty — users set their own system prompts via
        the subentry reconfigure flow; the empty string tells upstream to use its
        built-in assistant prompt rather than overriding it with something opaque."""
        from custom_components.codex_proxy.const import DEFAULT_PROMPT

        assert DEFAULT_PROMPT == ""


class TestIntervals:
    def test_model_refresh_interval_is_6h(self) -> None:
        assert timedelta(hours=6) == MODEL_REFRESH_INTERVAL

    def test_probe_timeout_positive(self) -> None:
        assert PROBE_TIMEOUT_S > 0

    def test_coordinator_timeout_positive(self) -> None:
        assert COORDINATOR_TIMEOUT_S > 0

    def test_coordinator_max_retries_positive(self) -> None:
        assert COORDINATOR_MAX_RETRIES > 0

    def test_probe_timeout_less_than_coordinator_timeout(self) -> None:
        """The probe timeout is intentionally shorter than the coordinator timeout:
        the probe runs in the UI-blocking config flow, so speed matters more.
        The coordinator runs in the background where a longer wait is acceptable."""
        assert PROBE_TIMEOUT_S < COORDINATOR_TIMEOUT_S

    def test_coordinator_retry_delays_length_consistent(self) -> None:
        """Delay table must have exactly (max_retries - 1) entries.

        Using == (not >=) so that adding an extra delay without bumping
        COORDINATOR_MAX_RETRIES is caught immediately rather than silently
        leaving dead entries in the table.
        """
        assert len(COORDINATOR_RETRY_DELAYS) == COORDINATOR_MAX_RETRIES - 1

    def test_coordinator_retry_delays_is_tuple(self) -> None:
        """COORDINATOR_RETRY_DELAYS must be a tuple so it is immutable — the
        coordinator indexes it directly by attempt number; a mutable list
        could be accidentally modified at runtime and silently change retry
        behaviour."""
        assert isinstance(COORDINATOR_RETRY_DELAYS, tuple)

    def test_coordinator_retry_delays_all_positive_ints(self) -> None:
        """Every delay must be a positive integer so asyncio.sleep receives a
        valid argument; a non-positive or non-integer delay would either be a
        no-op sleep or raise TypeError at runtime."""
        for i, delay in enumerate(COORDINATOR_RETRY_DELAYS):
            assert isinstance(delay, int), f"COORDINATOR_RETRY_DELAYS[{i}] is not int: {delay!r}"
            assert delay > 0, f"COORDINATOR_RETRY_DELAYS[{i}] is not positive: {delay}"

    def test_coordinator_max_retries_exact_value(self) -> None:
        """Pin COORDINATOR_MAX_RETRIES to exactly 3.

        test_coordinator_max_retries_positive only checks > 0 — any positive
        integer passes.  COORDINATOR_MAX_RETRIES drives the retry loop bound in
        the coordinator and the length invariant of COORDINATOR_RETRY_DELAYS;
        changing it without a deliberate review would alter retry behaviour and
        break the delay-table length assertion at import time.  Exact equality
        makes the intent explicit and catches an accidental bump (e.g. 4) that
        would require a matching COORDINATOR_RETRY_DELAYS entry."""
        assert COORDINATOR_MAX_RETRIES == 3, (
            f"COORDINATOR_MAX_RETRIES must be 3, got {COORDINATOR_MAX_RETRIES!r} — "
            "changing this alters the coordinator retry loop bound and requires a "
            "matching update to COORDINATOR_RETRY_DELAYS"
        )

    def test_coordinator_retry_delays_exact_values(self) -> None:
        """Pin COORDINATOR_RETRY_DELAYS to exactly (5, 30).

        test_coordinator_retry_delays_all_positive_ints only checks that every
        element is a positive int — (1, 1) or (999, 999) both pass.  The delays
        directly control how long the coordinator waits between transient-error
        retries; making them too short hammers the proxy on flaky networks, too
        long makes the integration appear unresponsive after startup.  Pinning
        the exact tuple catches an accidental edit (e.g. swapping 5 and 30 or
        inflating both values) before it reaches production."""
        assert COORDINATOR_RETRY_DELAYS == (5, 30), (
            f"COORDINATOR_RETRY_DELAYS must be (5, 30), got {COORDINATOR_RETRY_DELAYS!r} — "
            "these are the inter-attempt sleep durations; changing them alters retry "
            "backoff behaviour without a corresponding protocol review"
        )


class TestImageModelPrefixes:
    def test_gpt_image_prefix_present(self) -> None:
        assert any(p.startswith("gpt-image") for p in IMAGE_MODEL_ID_PREFIXES)

    def test_dall_e_prefix_present(self) -> None:
        assert any(p.startswith("dall-e") for p in IMAGE_MODEL_ID_PREFIXES)

    def test_image_prefix_present(self) -> None:
        assert any(p == "image-" for p in IMAGE_MODEL_ID_PREFIXES)

    def test_is_tuple(self) -> None:
        assert isinstance(IMAGE_MODEL_ID_PREFIXES, tuple)

    def test_no_empty_prefix(self) -> None:
        """An empty-string prefix would cause every model to be filtered out
        (since every string starts with ``""``). Guard against accidental
        introduction of an empty prefix."""
        assert all(len(p) > 0 for p in IMAGE_MODEL_ID_PREFIXES), (
            "IMAGE_MODEL_ID_PREFIXES must not contain an empty string"
        )

    def test_all_prefixes_are_lowercase(self) -> None:
        """``startswith`` is case-sensitive and real OpenAI/proxy model IDs
        use lowercase.  An uppercase prefix (e.g. ``"GPT-Image"``) would
        silently fail to filter the intended models."""
        assert all(p == p.lower() for p in IMAGE_MODEL_ID_PREFIXES), (
            "All IMAGE_MODEL_ID_PREFIXES must be lowercase"
        )


class TestCodexHeaders:
    def test_user_agent_contains_codex(self) -> None:
        assert "codex" in CODEX_USER_AGENT.lower()

    def test_openai_beta_references_responses(self) -> None:
        assert "responses" in CODEX_OPENAI_BETA

    def test_openai_beta_exact_value(self) -> None:
        """CODEX_OPENAI_BETA must equal exactly 'responses=experimental'.

        test_openai_beta_references_responses only checks that 'responses' is a
        substring — it passes if the value is 'responses=v2' or even just
        'responses'.  The OpenAI-Beta header is a fixed API contract; changing it
        silently breaks the proxy integration.  Pinning the exact value catches a
        refactor that updates the string without a corresponding protocol review."""
        assert CODEX_OPENAI_BETA == "responses=experimental", (
            f"CODEX_OPENAI_BETA must be 'responses=experimental', got {CODEX_OPENAI_BETA!r} — "
            "this is a fixed OpenAI API header value; changing it breaks the proxy protocol"
        )

    def test_originator_is_non_empty(self) -> None:
        assert CODEX_ORIGINATOR and isinstance(CODEX_ORIGINATOR, str)

    def test_originator_exact_value(self) -> None:
        """CODEX_ORIGINATOR must equal exactly 'codex_cli_rs'.

        test_originator_is_non_empty only checks type and truthiness — any
        non-empty string would pass.  The originator header identifies requests as
        coming from the codex CLI; a typo or rename here would break proxy-side
        routing rules that filter on this header.  Exact value equality catches
        that in the test suite before it reaches production."""
        assert CODEX_ORIGINATOR == "codex_cli_rs", (
            f"CODEX_ORIGINATOR must be 'codex_cli_rs', got {CODEX_ORIGINATOR!r} — "
            "this identifies the request originator to the proxy; changing it "
            "may break proxy-side routing rules"
        )
