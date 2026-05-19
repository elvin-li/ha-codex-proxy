"""Tests for _model_select_options in config_flow.py.

Exercises the dropdown building logic: coordinator models, custom values,
deduplication, and fallback when coordinator has no data.

Note: ha_stubs already provides a real dict-based SelectOptionDict so
option["value"] / option["label"] return plain strings in every test.
No per-test patching is required.
"""

# isort: skip_file
from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Bootstrap HA stubs
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402  — must precede codex_proxy imports

from custom_components.codex_proxy.config_flow import _model_select_options  # noqa: E402
from custom_components.codex_proxy.const import DEFAULT_MODEL  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coord(models: list[dict[str, Any]]) -> MagicMock:
    c = MagicMock()
    c.chat_models = models
    return c


def _m(mid: str, display: str | None = None) -> dict[str, Any]:
    return {"id": mid, "created": 0, "owned_by": "", "display_name": display or mid}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestModelSelectOptions:
    def test_none_coordinator_returns_default(self) -> None:
        opts = _model_select_options(None, None)
        assert len(opts) == 1
        assert opts[0]["value"] == DEFAULT_MODEL

    def test_empty_coordinator_returns_default(self) -> None:
        opts = _model_select_options(_coord([]), None)
        assert len(opts) == 1
        assert opts[0]["value"] == DEFAULT_MODEL

    def test_coordinator_models_listed(self) -> None:
        opts = _model_select_options(_coord([_m("gpt-5.5"), _m("gpt-5.4")]), None)
        values = [o["value"] for o in opts]
        assert "gpt-5.5" in values
        assert "gpt-5.4" in values

    def test_current_model_prepended_if_not_in_coordinator(self) -> None:
        opts = _model_select_options(_coord([_m("gpt-5.5")]), "gpt-5.3-turbo")
        assert opts[0]["value"] == "gpt-5.3-turbo"

    def test_current_model_label_equals_id_when_prepended(self) -> None:
        """When the current model is prepended (it is not in the coordinator's
        list), its dropdown label must equal its model id.

        The existing test_current_model_prepended_if_not_in_coordinator only
        checks the *value*; without this test a refactor that sets a blank label
        or raises for the prepended option (no display_name lookup) would produce
        an empty label in the UI dropdown — invisible to the operator but caught
        by checking both value and label here."""
        opts = _model_select_options(_coord([_m("gpt-5.5")]), "gpt-5.3-turbo")
        assert opts[0]["label"] == "gpt-5.3-turbo", (
            "Prepended current model must use model id as label — "
            "the proxy hasn't seen this model so no display_name is available"
        )

    def test_current_model_not_duplicated_if_already_present(self) -> None:
        opts = _model_select_options(_coord([_m("gpt-5.5"), _m("gpt-5.4")]), "gpt-5.5")
        values = [o["value"] for o in opts]
        assert values.count("gpt-5.5") == 1

    def test_display_name_used_as_label(self) -> None:
        opts = _model_select_options(_coord([_m("gpt-5.5", "GPT-5.5 Preview")]), None)
        gpt55 = next(o for o in opts if o["value"] == "gpt-5.5")
        assert gpt55["label"] == "GPT-5.5 Preview"

    def test_id_used_as_label_when_no_display_name(self) -> None:
        opts = _model_select_options(_coord([_m("gpt-5.5")]), None)
        assert opts[0]["label"] == "gpt-5.5"

    def test_null_display_name_falls_back_to_id(self) -> None:
        """Explicit None for display_name (not just absent key) must still fall
        back to the model id as label — tests the `or mid` branch."""
        opts = _model_select_options(
            _coord([{"id": "gpt-5.5", "created": 0, "owned_by": "", "display_name": None}]),
            None,
        )
        assert opts[0]["label"] == "gpt-5.5"

    def test_empty_string_display_name_falls_back_to_id(self) -> None:
        """An empty-string display_name is falsy — the label must fall back to
        the model id rather than rendering a blank dropdown option."""
        opts = _model_select_options(
            _coord([{"id": "gpt-5.5", "created": 0, "owned_by": "", "display_name": ""}]),
            None,
        )
        assert opts[0]["label"] == "gpt-5.5"

    def test_deduplication_by_id(self) -> None:
        # Two entries with same id — should only appear once
        opts = _model_select_options(_coord([_m("gpt-5.5"), _m("gpt-5.5")]), None)
        values = [o["value"] for o in opts]
        assert values.count("gpt-5.5") == 1

    def test_none_current_model_no_prepend(self) -> None:
        opts = _model_select_options(_coord([_m("gpt-5.5")]), None)
        assert len(opts) == 1

    def test_empty_string_current_model_no_prepend(self) -> None:
        opts = _model_select_options(_coord([_m("gpt-5.5")]), "")
        # Empty string is falsy — should not prepend
        assert len(opts) == 1
