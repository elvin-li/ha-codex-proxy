"""Tests for CodexModelCoordinator's @property methods.

chat_models filters image-only models; latest_chat_model_id returns the
first result from chat_models.  Runs without a full HA install.
"""

from __future__ import annotations

import os
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402  — must precede codex_proxy imports
from custom_components.codex_proxy.coordinator import CodexModelCoordinator  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coordinator(models: list[dict[str, Any]]) -> CodexModelCoordinator:
    coord = object.__new__(CodexModelCoordinator)
    coord.data = {"models": models}
    return coord


def _m(mid: str, created: int = 0) -> dict[str, Any]:
    return {"id": mid, "created": created, "owned_by": "openai", "display_name": mid}


# ---------------------------------------------------------------------------
# chat_models property
# ---------------------------------------------------------------------------


class TestChatModelsProperty:
    def test_empty_when_no_data(self) -> None:
        coord = object.__new__(CodexModelCoordinator)
        coord.data = None
        assert coord.chat_models == []

    def test_empty_data_dict(self) -> None:
        coord = object.__new__(CodexModelCoordinator)
        coord.data = {}
        assert coord.chat_models == []

    def test_all_chat_models_pass_through(self) -> None:
        models = [_m("gpt-5.5"), _m("gpt-5.4")]
        coord = _make_coordinator(models)
        assert len(coord.chat_models) == 2

    def test_filters_gpt_image_prefix(self) -> None:
        models = [_m("gpt-image-1"), _m("gpt-5.5")]
        coord = _make_coordinator(models)
        ids = [m["id"] for m in coord.chat_models]
        assert "gpt-image-1" not in ids
        assert "gpt-5.5" in ids

    def test_filters_dall_e_prefix(self) -> None:
        models = [_m("dall-e-3"), _m("gpt-5.5")]
        coord = _make_coordinator(models)
        ids = [m["id"] for m in coord.chat_models]
        assert "dall-e-3" not in ids

    def test_filters_image_prefix(self) -> None:
        models = [_m("image-alpha-001"), _m("gpt-5.5")]
        coord = _make_coordinator(models)
        ids = [m["id"] for m in coord.chat_models]
        assert "image-alpha-001" not in ids

    def test_preserves_order(self) -> None:
        models = [_m("gpt-5.6", 200), _m("gpt-5.5", 100)]
        coord = _make_coordinator(models)
        ids = [m["id"] for m in coord.chat_models]
        assert ids == ["gpt-5.6", "gpt-5.5"]

    def test_filter_does_not_reorder_chat_models(self) -> None:
        """chat_models must preserve the order of self.data['models'] after
        filtering — it must NOT sort independently.  The sort invariant is
        maintained by _async_update_data; chat_models only filters."""
        models = [
            _m("gpt-z", 100),  # higher timestamp but alphabetically last
            _m("gpt-a", 50),
            _m("gpt-image-1", 200),  # image model — should be excluded
        ]
        coord = _make_coordinator(models)
        ids = [m["id"] for m in coord.chat_models]
        assert ids == ["gpt-z", "gpt-a"]  # order from data preserved; image excluded

    def test_chat_models_returns_empty_when_models_key_absent(self) -> None:
        """data dict present but lacking a 'models' key — must return [].

        A coordinator update that returns an unexpected payload shape (e.g.
        {"status": "ok"} with no "models" key) must not raise; the property
        should degrade gracefully to an empty list.
        """
        coord = object.__new__(CodexModelCoordinator)
        coord.data = {"status": "ok"}  # valid dict but no 'models' key
        assert coord.chat_models == []


# ---------------------------------------------------------------------------
# latest_chat_model_id property
# ---------------------------------------------------------------------------


class TestLatestChatModelId:
    def test_none_when_no_data(self) -> None:
        coord = object.__new__(CodexModelCoordinator)
        coord.data = None
        assert coord.latest_chat_model_id is None

    def test_none_when_only_image_models(self) -> None:
        coord = _make_coordinator([_m("gpt-image-1"), _m("dall-e-3")])
        assert coord.latest_chat_model_id is None

    def test_returns_first_chat_model(self) -> None:
        coord = _make_coordinator([_m("gpt-5.6", 200), _m("gpt-5.5", 100)])
        assert coord.latest_chat_model_id == "gpt-5.6"

    def test_returns_only_chat_model(self) -> None:
        coord = _make_coordinator([_m("gpt-5.5")])
        assert coord.latest_chat_model_id == "gpt-5.5"

    def test_image_model_skipped_to_find_chat(self) -> None:
        coord = _make_coordinator([_m("gpt-image-1"), _m("gpt-5.5")])
        assert coord.latest_chat_model_id == "gpt-5.5"

    def test_alphabetically_first_returned_when_timestamps_equal(self) -> None:
        """When all models carry the same created timestamp (e.g. 0) the stable
        (-created, id) sort in _async_update_data means data is stored in
        alphabetical order.  latest_chat_model_id must return the first element
        of chat_models — which is the alphabetically-first id in this case.

        Note: _make_coordinator bypasses _async_update_data, so we pre-sort the
        input to match the invariant that _async_update_data guarantees.
        """
        # Pre-sorted as (-created, id): gpt-a, gpt-m, gpt-z all have created=0
        coord = _make_coordinator([_m("gpt-a", 0), _m("gpt-m", 0), _m("gpt-z", 0)])
        assert coord.latest_chat_model_id == "gpt-a"
