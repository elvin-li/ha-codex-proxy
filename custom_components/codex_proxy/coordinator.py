"""Periodic /v1/models polling for the Codex Token Pool integration.

We bypass `openai.AsyncOpenAI.models.list()` and call the endpoint with raw
httpx because the openai SDK 2.x cursor-page parser fails on this proxy's
response (`'str' object has no attribute '_set_private_attributes'`).
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import httpx
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CODEX_OPENAI_BETA,
    CODEX_ORIGINATOR,
    CODEX_USER_AGENT,
    CONF_API_KEY,
    CONF_BASE_URL,
    COORDINATOR_MAX_RETRIES,
    COORDINATOR_RETRY_DELAYS,
    COORDINATOR_TIMEOUT_S,
    DOMAIN,
    IMAGE_MODEL_ID_PREFIXES,
    MODEL_REFRESH_INTERVAL,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class CodexModelCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the proxy's /v1/models endpoint and surface the result."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: "ConfigEntry",
        installation_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_models_{entry.entry_id}",
            update_interval=MODEL_REFRESH_INTERVAL,
        )
        self._api_key: str = entry.data[CONF_API_KEY]
        self._base_url: str = entry.data[CONF_BASE_URL].rstrip("/")
        self._installation_id = installation_id
        self._http: httpx.AsyncClient = get_async_client(hass)

    async def _async_update_data(self) -> dict[str, Any]:
        url = f"{self._base_url}/v1/models"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": CODEX_USER_AGENT,
            "OpenAI-Beta": CODEX_OPENAI_BETA,
            "originator": CODEX_ORIGINATOR,
            "x-codex-installation-id": self._installation_id,
            "Accept": "application/json",
        }
        last_err: Exception | None = None
        for attempt in range(COORDINATOR_MAX_RETRIES):
            try:
                r = await self._http.get(
                    url, headers=headers, timeout=COORDINATOR_TIMEOUT_S
                )
                r.raise_for_status()
                payload = r.json()
                break  # success
            except (httpx.HTTPStatusError, httpx.TimeoutException) as err:
                # Transient errors (5xx, timeout) — retry with back-off
                last_err = err
                if attempt < COORDINATOR_MAX_RETRIES - 1:
                    await asyncio.sleep(COORDINATOR_RETRY_DELAYS[attempt])
            except httpx.HTTPError as err:
                # Non-transient (connection refused, DNS) — fail immediately
                raise UpdateFailed(
                    f"Failed to fetch {url}: {type(err).__name__}: {err}"
                ) from err
            except ValueError as err:
                raise UpdateFailed(
                    f"Bad JSON from {url}: {err}"
                ) from err
        else:
            raise UpdateFailed(
                f"Failed to fetch {url} after {COORDINATOR_MAX_RETRIES} attempts"
                f" (last error: {type(last_err).__name__}: {last_err})"
            )

        seen_ids: set[str] = set()
        models: list[dict[str, Any]] = []
        for m in payload.get("data", []):
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
        return {"models": models}

    @property
    def chat_models(self) -> list[dict[str, Any]]:
        """Chat-capable models (image-only excluded), newest first."""
        if not self.data:
            return []
        return [
            m
            for m in self.data.get("models", [])
            if not any(m["id"].startswith(p) for p in IMAGE_MODEL_ID_PREFIXES)
        ]

    @property
    def latest_chat_model_id(self) -> str | None:
        chat = self.chat_models
        return chat[0]["id"] if chat else None
