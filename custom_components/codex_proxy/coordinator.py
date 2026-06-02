"""Periodic /v1/models polling for the Codex Token Pool integration.

We bypass `openai.AsyncOpenAI.models.list()` and call the endpoint with raw
httpx because the openai SDK 2.x cursor-page parser fails on this proxy's
response (`'str' object has no attribute '_set_private_attributes'`).
"""

from __future__ import annotations

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
    DOMAIN,
    MODEL_REFRESH_INTERVAL,
    MODELS_FETCH_TIMEOUT_S,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class CodexModelCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the proxy's /v1/models endpoint and surface the result.

    Attributes
    ----------
    config_entry : ConfigEntry
        The config entry this coordinator belongs to.  Exposed as a public
        attribute so HA's coordinator infrastructure can link diagnostics.
    """

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        installation_id: str,
    ) -> None:
        """Initialize the model coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_models_{entry.entry_id}",
            update_interval=MODEL_REFRESH_INTERVAL,
            config_entry=entry,
        )
        self._base_url: str = entry.data[CONF_BASE_URL].rstrip("/")
        self._headers: dict[str, str] = {
            "Authorization": f"Bearer {entry.data[CONF_API_KEY]}",
            "User-Agent": CODEX_USER_AGENT,
            "OpenAI-Beta": CODEX_OPENAI_BETA,
            "originator": CODEX_ORIGINATOR,
            "x-codex-installation-id": installation_id,
            "Accept": "application/json",
        }
        self._http: httpx.AsyncClient = get_async_client(hass)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch models from the proxy."""
        url = f"{self._base_url}/v1/models"
        try:
            response = await self._http.get(
                url, headers=self._headers, timeout=MODELS_FETCH_TIMEOUT_S
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as err:
            raise UpdateFailed(
                f"Timeout fetching {url} after {MODELS_FETCH_TIMEOUT_S}s"
            ) from err
        except httpx.HTTPStatusError as err:
            raise UpdateFailed(
                f"HTTP {err.response.status_code} from {url}"
            ) from err
        except httpx.HTTPError as err:
            raise UpdateFailed(f"Failed to fetch {url}: {err}") from err
        except ValueError as err:
            raise UpdateFailed(f"Bad JSON from {url}: {err}") from err

        models = self._parse_models(payload)
        return {"models": models}

    @staticmethod
    def _parse_models(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract and normalize model entries from the API response."""
        models: list[dict[str, Any]] = []
        for m in payload.get("data", []):
            mid = m.get("id")
            if not mid:
                continue
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

    # --- Public API ---

    @property
    def chat_models(self) -> list[dict[str, Any]]:
        """Chat-capable models (excluding image-only), newest first."""
        if not self.data:
            return []
        return [
            m
            for m in self.data.get("models", [])
            if not m["id"].startswith("gpt-image")
        ]

    @property
    def latest_chat_model_id(self) -> str | None:
        """ID of the most recently created chat model, or None."""
        chat = self.chat_models
        return chat[0]["id"] if chat else None
