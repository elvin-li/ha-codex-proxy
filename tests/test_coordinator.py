"""Tests for CodexModelCoordinator data processing logic.

These tests exercise the pure data-transformation code extracted from
_async_update_data. They have no HA runtime dependency.
"""

from __future__ import annotations

import os
import sys
from typing import Any

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


def _process_models(payload_data: list) -> list[dict[str, Any]]:
    """Replicate coordinator._async_update_data model-processing loop."""
    seen_ids: set[str] = set()
    models: list[dict[str, Any]] = []
    for m in payload_data:
        if not isinstance(m, dict):
            continue
        mid = m.get("id")
        if not mid or mid in seen_ids:
            continue
        seen_ids.add(mid)
        try:
            created = int(m.get("created") or 0)
        except (ValueError, TypeError):
            created = 0
        models.append(
            {
                "id": mid,
                "created": created,
                "owned_by": str(m.get("owned_by") or ""),
                "display_name": str((m.get("display_name") or "").strip() or mid),
            }
        )
    models.sort(key=lambda x: (-x["created"], x["id"]))
    return models


def _filter_chat(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replicate coordinator.chat_models filter."""
    return [m for m in models if not any(m["id"].startswith(p) for p in IMAGE_MODEL_ID_PREFIXES)]


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

    def test_numeric_string_created_is_accepted(self) -> None:
        """Some proxies return created as a string — int() should convert it."""
        data = [{"id": "gpt-5.5", "created": "1700000000"}]
        models = _process_models(data)
        assert models[0]["created"] == 1_700_000_000

    def test_non_numeric_string_created_falls_back_to_zero(self) -> None:
        """A non-numeric created field (e.g. ISO date) must not crash the
        coordinator — it should silently fall back to 0 so sorting still works."""
        data = [{"id": "gpt-5.5", "created": "2024-01-01"}]
        models = _process_models(data)
        assert models[0]["created"] == 0
        assert models[0]["id"] == "gpt-5.5"

    def test_none_created_is_zero(self) -> None:
        """Explicit None on the created field falls back to 0."""
        data = [{"id": "gpt-5.5", "created": None}]
        models = _process_models(data)
        assert models[0]["created"] == 0

    def test_same_created_sorted_alphabetically_by_id(self) -> None:
        """When two models have the same created timestamp (e.g. both 0 from
        a local proxy), the sort must be deterministic: alphabetical by id.

        This guards against non-deterministic ordering after coordinator
        updates, which could cause spurious ``update available`` flicker when
        the 'latest' model id changes between polls despite the proxy returning
        the same models.
        """
        data = [
            _make_model("gpt-z-model", created=0),
            _make_model("gpt-a-model", created=0),
            _make_model("gpt-m-model", created=0),
        ]
        models = _process_models(data)
        ids = [m["id"] for m in models]
        assert ids == ["gpt-a-model", "gpt-m-model", "gpt-z-model"]

    def test_empty_string_display_name_falls_back_to_id(self) -> None:
        """An empty-string display_name (falsy, like None) must fall back to
        the model id — guards the `str(m.get("display_name") or mid)` branch."""
        data = [{"id": "gpt-5.5", "created": 0, "owned_by": "", "display_name": ""}]
        models = _process_models(data)
        assert models[0]["display_name"] == "gpt-5.5"

    def test_whitespace_only_display_name_falls_back_to_id(self) -> None:
        """A display_name that is whitespace-only (e.g. '   ') must fall back
        to the model id after stripping — guards the `.strip() or mid` branch."""
        data = [{"id": "gpt-5.5", "created": 0, "owned_by": "", "display_name": "   "}]
        models = _process_models(data)
        assert models[0]["display_name"] == "gpt-5.5"

    def test_display_name_surrounding_whitespace_stripped(self) -> None:
        """Surrounding whitespace on a non-empty display_name must be stripped
        so the dropdown doesn't show '  GPT 5.5  ' with padding."""
        data = [{"id": "gpt-5.5", "created": 0, "owned_by": "", "display_name": "  GPT 5.5 Preview  "}]
        models = _process_models(data)
        assert models[0]["display_name"] == "GPT 5.5 Preview"

    def test_non_dict_entries_in_list_are_skipped(self) -> None:
        """Some non-standard proxies mix bare strings or other non-dict types
        into the model list.  The loop must skip them rather than raising
        AttributeError on .get().  Guards the `isinstance(m, dict)` check."""
        data: list = [
            _make_model("gpt-5.5"),
            "some-bare-string-entry",  # str — .get() would raise AttributeError
            None,                       # NoneType — same
            42,                         # int — same
        ]
        models = _process_models(data)
        # Only the valid dict entry should appear in the result
        assert len(models) == 1
        assert models[0]["id"] == "gpt-5.5"


class TestChatModelFilter:
    def test_excludes_gpt_image_prefix(self) -> None:
        models = _process_models([_make_model("gpt-image-1", 100), _make_model("gpt-5.5", 50)])
        chat = _filter_chat(models)
        assert len(chat) == 1
        assert chat[0]["id"] == "gpt-5.5"

    def test_excludes_dall_e_prefix(self) -> None:
        models = _process_models([_make_model("dall-e-3"), _make_model("gpt-5.5")])
        chat = _filter_chat(models)
        assert all(m["id"] != "dall-e-3" for m in chat)
        assert any(m["id"] == "gpt-5.5" for m in chat)

    def test_excludes_dall_e_prefix_exact_result(self) -> None:
        """dall-e-3 filter must leave exactly ['gpt-5.5'] — not an empty list
        or a list with unexpected extras.

        test_excludes_dall_e_prefix uses ``all`` and ``any`` without checking
        len; a filter that returned [] would pass the ``all`` check (vacuously
        true) and fail the ``any`` check, but a filter returning [gpt-5.5,
        dall-e-3] would pass both.  Exact list equality catches all of these
        edge cases in a single assertion.  Mirrors the pattern in
        test_coordinator_properties.py (v0.2.125)."""
        models = _process_models([_make_model("dall-e-3"), _make_model("gpt-5.5")])
        chat = _filter_chat(models)
        ids = [m["id"] for m in chat]
        assert ids == ["gpt-5.5"], (
            f"Expected exactly ['gpt-5.5'] after dall-e filter, got {ids!r}"
        )

    def test_excludes_image_prefix(self) -> None:
        models = _process_models([_make_model("image-alpha-001"), _make_model("gpt-5.5")])
        chat = _filter_chat(models)
        assert all(not m["id"].startswith("image-") for m in chat)

    def test_excludes_image_prefix_exact_result(self) -> None:
        """image-alpha-001 filter must leave exactly ['gpt-5.5'].

        test_excludes_image_prefix uses only ``all(...)`` which is vacuously
        True on an empty list — a filter that returns [] passes the assertion.
        Exact list equality verifies the filter is surgical."""
        models = _process_models([_make_model("image-alpha-001"), _make_model("gpt-5.5")])
        chat = _filter_chat(models)
        ids = [m["id"] for m in chat]
        assert ids == ["gpt-5.5"], (
            f"Expected exactly ['gpt-5.5'] after image- filter, got {ids!r}"
        )

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

    def test_contains_exactly_three_prefixes(self) -> None:
        """IMAGE_MODEL_ID_PREFIXES must contain exactly the three expected
        prefixes — no more, no less.

        test_required_prefixes_present uses ``in`` checks that pass even if
        extra prefixes are accidentally added.  An extra prefix like ``"gpt-"``
        would silently exclude all GPT models from chat_models, making the
        integration appear to have zero models after every fetch.  Exact set
        equality catches that before it reaches production."""
        assert set(IMAGE_MODEL_ID_PREFIXES) == {"gpt-image", "dall-e", "image-"}, (
            f"Unexpected prefixes in IMAGE_MODEL_ID_PREFIXES: "
            f"{set(IMAGE_MODEL_ID_PREFIXES) - {'gpt-image', 'dall-e', 'image-'}}"
        )
