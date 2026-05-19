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

    def test_reasoning_efforts_contains_expected_values(self) -> None:
        for effort in ("none", "medium", "high", "xhigh"):
            assert effort in REASONING_EFFORTS

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

    def test_coordinator_retry_delays_length_consistent(self) -> None:
        """Delay table must have exactly (max_retries - 1) entries.

        Using == (not >=) so that adding an extra delay without bumping
        COORDINATOR_MAX_RETRIES is caught immediately rather than silently
        leaving dead entries in the table.
        """
        assert len(COORDINATOR_RETRY_DELAYS) == COORDINATOR_MAX_RETRIES - 1


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

    def test_originator_is_non_empty(self) -> None:
        assert CODEX_ORIGINATOR and isinstance(CODEX_ORIGINATOR, str)
