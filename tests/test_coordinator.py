"""Tests for CodexModelCoordinator data processing logic.

These tests exercise the pure data-transformation code extracted from
_async_update_data. They have no HA runtime dependency.
"""
from __future__ import annotations

import sys
import os
from typing import Any

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_image_prefixes() -> tuple[str, ...]:
    """Import IMAGE_MODEL_ID_PREFIXES by loading const directly."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "codex_proxy_const",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "custom_components",
            "codex_proxy",
            "const.py",
        ),
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.IMAGE_MODEL_ID_PREFIXES  # type: ignore[attr-defined]


IMAGE_MODEL_ID_PREFIXES = _get_image_prefixes()


# ---------------------------------------------------------------------------
# Helper: replicate coordinator's inner processing loop
# ---------------------------------------------------------------------------


def _make_model(model_id: str, created: int = 0) -> dict[str, Any]:
    return {"id": model_id, "created": created, "object": "model", "owned_by": "openai"}


def _process_models(payload_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replicate coordinator._async_update_data model-processing loop."""
    seen_ids: set[str] = set()
    models: list[dict[str, Any]] = []
    for m in payload_data:
        mid = m.get("id")
        if not mid or mid in seen_ids:
            continue
        seen_ids.add(mid)
        models.append(
            {
                "id": mid,
                "created": int(m.get("created") or 0),
                "owned_by": str(m.get("owned_by") or ""),
                "display_name": str(m.get("display_name") or mid),
            }
        )
    models.sort(key=lambda x: x["created"], reverse=True)
    return models


def _filter_chat(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replicate coordinator.chat_models filter."""
    return [
        m
        for m in models
        if not any(m["id"].startswith(p) for p in IMAGE_MODEL_ID_PREFIXES)
    ]


# ---------------------------------------------------------------------------
# Model processing
# ---------------------------------------------------------------------------


class TestModelProcessing:
    def test_deduplicates_by_id(self) -> None:
        data = [
            _make_model("gpt-5.5", created=100),
            _make_model("gpt-5.5", created=100),  # duplicate
            _make_model("gpt-5.4", created=50),
        ]
        models = _process_models(data)
        ids = [m["id"] for m in models]
        assert ids.count("gpt-5.5") == 1
        assert len(models) == 2

    def test_sorted_newest_first(self) -> None:
        data = [
            _make_model("gpt-5.4", created=50),
            _make_model("gpt-5.5", created=100),
            _make_model("gpt-5.3", created=10),
        ]
        models = _process_models(data)
        assert [m["id"] for m in models] == ["gpt-5.5", "gpt-5.4", "gpt-5.3"]

    def test_skips_entries_without_id(self) -> None:
        data = [{"created": 100}, _make_model("gpt-5.5")]
        models = _process_models(data)
        assert len(models) == 1
        assert models[0]["id"] == "gpt-5.5"

    def test_display_name_falls_back_to_id(self) -> None:
        data = [_make_model("gpt-5.5")]
        models = _process_models(data)
        assert models[0]["display_name"] == "gpt-5.5"

    def test_custom_display_name_preserved(self) -> None:
        data = [{"id": "gpt-5.5", "created": 0, "display_name": "GPT-5.5 Preview"}]
        models = _process_models(data)
        assert models[0]["display_name"] == "GPT-5.5 Preview"


class TestChatModelFilter:
    def test_excludes_gpt_image_prefix(self) -> None:
        models = _process_models(
            [_make_model("gpt-image-1", 100), _make_model("gpt-5.5", 50)]
        )
        chat = _filter_chat(models)
        assert len(chat) == 1
        assert chat[0]["id"] == "gpt-5.5"

    def test_excludes_dall_e_prefix(self) -> None:
        models = _process_models([_make_model("dall-e-3"), _make_model("gpt-5.5")])
        chat = _filter_chat(models)
        assert all(m["id"] != "dall-e-3" for m in chat)
        assert any(m["id"] == "gpt-5.5" for m in chat)

    def test_excludes_image_prefix(self) -> None:
        models = _process_models(
            [_make_model("image-alpha-001"), _make_model("gpt-5.5")]
        )
        chat = _filter_chat(models)
        assert all(not m["id"].startswith("image-") for m in chat)

    def test_all_chat_models_pass_through(self) -> None:
        data = [_make_model(f"gpt-5.{i}", i) for i in range(5)]
        models = _process_models(data)
        chat = _filter_chat(models)
        assert len(chat) == 5

    def test_empty_list(self) -> None:
        assert _filter_chat([]) == []


class TestImageModelIdPrefixes:
    def test_required_prefixes_present(self) -> None:
        assert "gpt-image" in IMAGE_MODEL_ID_PREFIXES
        assert "dall-e" in IMAGE_MODEL_ID_PREFIXES
        assert "image-" in IMAGE_MODEL_ID_PREFIXES
