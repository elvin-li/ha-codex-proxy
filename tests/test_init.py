"""Tests for pure helpers and constants in codex_proxy/__init__.py.

Covers _build_codex_headers and verifies the PLATFORMS list contains all
expected platform strings. Runs without a full HA install.
"""

from __future__ import annotations

import os
import sys

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.ha_stubs  # noqa: F401, E402
from custom_components.codex_proxy.const import (  # noqa: E402
    CODEX_OPENAI_BETA,
    CODEX_ORIGINATOR,
    CODEX_USER_AGENT,
    CONF_INSTALLATION_ID,
)

# ---------------------------------------------------------------------------
# _build_codex_headers
# ---------------------------------------------------------------------------


def _build_codex_headers(installation_id: str) -> dict[str, str]:
    """Import and call via the module's own function."""
    from custom_components.codex_proxy import _build_codex_headers as _fn

    return _fn(installation_id)


class TestBuildCodexHeaders:
    def test_user_agent_present(self) -> None:
        headers = _build_codex_headers("test-id-1")
        assert headers["User-Agent"] == CODEX_USER_AGENT

    def test_openai_beta_present(self) -> None:
        headers = _build_codex_headers("test-id-1")
        assert headers["OpenAI-Beta"] == CODEX_OPENAI_BETA

    def test_originator_present(self) -> None:
        headers = _build_codex_headers("test-id-1")
        assert headers["originator"] == CODEX_ORIGINATOR

    def test_installation_id_in_header(self) -> None:
        iid = "00000000-0000-0000-0000-000000000042"
        headers = _build_codex_headers(iid)
        assert headers["x-codex-installation-id"] == iid

    def test_different_installation_ids_produce_different_headers(self) -> None:
        h1 = _build_codex_headers("id-a")
        h2 = _build_codex_headers("id-b")
        assert h1["x-codex-installation-id"] != h2["x-codex-installation-id"]

    def test_all_required_keys_present(self) -> None:
        headers = _build_codex_headers("test-id")
        required = {"User-Agent", "OpenAI-Beta", "originator", "x-codex-installation-id"}
        assert required.issubset(headers.keys())


# ---------------------------------------------------------------------------
# PLATFORMS list
# ---------------------------------------------------------------------------


class TestPlatforms:
    def test_platform_count(self) -> None:
        """Should have exactly 7 platforms registered."""
        from custom_components.codex_proxy import PLATFORMS

        assert len(PLATFORMS) == 7

    def test_platforms_is_list(self) -> None:
        from custom_components.codex_proxy import PLATFORMS

        assert isinstance(PLATFORMS, list)

    def test_all_platforms_unique(self) -> None:
        """No platform should appear twice."""
        from custom_components.codex_proxy import PLATFORMS

        # Use identity comparison (MagicMock children are cached, so same attr → same object)
        seen = []
        for p in PLATFORMS:
            assert p not in seen, f"Duplicate platform: {p}"
            seen.append(p)

    def test_binary_sensor_registered(self) -> None:
        """Platform.BINARY_SENSOR must appear in PLATFORMS."""
        from homeassistant.const import Platform  # type: ignore[attr-defined]

        from custom_components.codex_proxy import PLATFORMS

        assert Platform.BINARY_SENSOR in PLATFORMS

    def test_conversation_registered(self) -> None:
        from homeassistant.const import Platform  # type: ignore[attr-defined]

        from custom_components.codex_proxy import PLATFORMS

        assert Platform.CONVERSATION in PLATFORMS

    def test_sensor_registered(self) -> None:
        from homeassistant.const import Platform  # type: ignore[attr-defined]

        from custom_components.codex_proxy import PLATFORMS

        assert Platform.SENSOR in PLATFORMS


# ---------------------------------------------------------------------------
# Constants sanity checks
# ---------------------------------------------------------------------------


class TestConstants:
    def test_codex_user_agent_contains_version(self) -> None:
        assert "codex_cli_rs/" in CODEX_USER_AGENT

    def test_openai_beta_is_responses(self) -> None:
        assert "responses" in CODEX_OPENAI_BETA

    def test_conf_installation_id_key(self) -> None:
        assert CONF_INSTALLATION_ID == "codex_installation_id"
