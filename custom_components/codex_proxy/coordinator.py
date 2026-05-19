"""Periodic /v1/models polling for the Codex Token Pool integration.

We bypass `openai.AsyncOpenAI.models.list()` and call the endpoint with raw
httpx because the openai SDK 2.x cursor-page parser fails on this proxy's
response (`'str' object has no attribute '_set_private_attributes'`).
"""

from __future__ import annotations

import asyncio
import json
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
        entry: ConfigEntry,
        installation_id: str,
    ) -> None:
        """Initialise the coordinator.

        Builds and caches the invariant HTTP request components (URL and
        headers) so that ``_async_update_data`` only needs to issue the GET
        request without reconstructing them on every poll.

        Args:
            hass: The Home Assistant instance.
            entry: The config entry that holds ``api_key`` and ``base_url``.
            installation_id: A stable UUID assigned to this HA instance,
                sent as ``x-codex-installation-id`` to help proxy operators
                distinguish traffic from different HA installations.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_models_{entry.entry_id}",
            update_interval=MODEL_REFRESH_INTERVAL,
        )
        api_key: str = entry.data[CONF_API_KEY]
        base_url: str = entry.data[CONF_BASE_URL].rstrip("/")
        self._http: httpx.AsyncClient = get_async_client(hass)
        # Pre-build invariant request parts so _async_update_data stays lean.
        self._url: str = f"{base_url}/v1/models"
        self._headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": CODEX_USER_AGENT,
            "OpenAI-Beta": CODEX_OPENAI_BETA,
            "originator": CODEX_ORIGINATOR,
            "x-codex-installation-id": installation_id,
            "Accept": "application/json",
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch ``/v1/models`` and return a normalised ``{"models": [...]}`` dict.

        Retry behaviour (controlled by ``COORDINATOR_MAX_RETRIES`` and
        ``COORDINATOR_RETRY_DELAYS``):
        - HTTP 5xx and ``httpx.TimeoutException`` are transient — the request is
          retried after the configured delay.
        - HTTP 4xx and ``httpx.HTTPError`` (connection refused, DNS failure) are
          non-transient — ``UpdateFailed`` is raised immediately without retrying.
        - ``json.JSONDecodeError`` (proxy returned non-JSON) is non-transient.

        The normalised model list is sorted by ``(-created, id)`` so it is
        deterministic even when multiple models share the same timestamp.
        """
        last_err: Exception | None = None
        for attempt in range(COORDINATOR_MAX_RETRIES):
            try:
                r = await self._http.get(
                    self._url, headers=self._headers, timeout=COORDINATOR_TIMEOUT_S
                )
                r.raise_for_status()
                payload = r.json()
                break  # success
            except httpx.HTTPStatusError as err:
                if err.response.status_code < 500:
                    # Client error (4xx) — non-transient, fail immediately
                    raise UpdateFailed(
                        f"Client error fetching {self._url}: HTTP {err.response.status_code}"
                    ) from err
                last_err = err  # 5xx — fall through to retry logic below
            except httpx.TimeoutException as err:
                last_err = err  # Transient — fall through to retry logic below
            except httpx.HTTPError as err:
                # Non-transient (connection refused, DNS) — fail immediately
                raise UpdateFailed(
                    f"Failed to fetch {self._url}: {type(err).__name__}: {err}"
                ) from err
            except json.JSONDecodeError as err:
                raise UpdateFailed(f"Bad JSON from {self._url}: {err}") from err

            # Transient error — sleep before next attempt (not after the last one)
            if attempt < COORDINATOR_MAX_RETRIES - 1:
                # The module-level assertion in const.py guarantees
                # len(COORDINATOR_RETRY_DELAYS) == COORDINATOR_MAX_RETRIES - 1,
                # so `attempt` is always a valid index here.
                delay = COORDINATOR_RETRY_DELAYS[attempt]
                _LOGGER.debug(
                    "Transient error on attempt %d/%d (%s) — retrying in %ds",
                    attempt + 1,
                    COORDINATOR_MAX_RETRIES,
                    type(last_err).__name__,
                    delay,
                )
                await asyncio.sleep(delay)
        else:
            raise UpdateFailed(
                f"Failed to fetch {self._url} after {COORDINATOR_MAX_RETRIES} attempts"
                f" (last error: {type(last_err).__name__}: {last_err})"
            )

        # Some proxies return the model list at the top level ("data" key
        # missing); others follow the OpenAI convention {"object":"list","data":[...]}.
        # Handle both gracefully.
        raw_list: list[Any] = payload.get("data", payload) if isinstance(payload, dict) else payload
        if not isinstance(raw_list, list):
            raw_list = []

        seen_ids: set[str] = set()
        models: list[dict[str, Any]] = []
        for m in raw_list:
            # Skip non-dict elements — some proxies include bare strings or
            # other scalars in the list; calling .get() on them would raise
            # AttributeError and crash the entire coordinator update.
            if not isinstance(m, dict):
                continue
            mid = m.get("id")
            if not mid or mid in seen_ids:
                continue
            seen_ids.add(mid)
            # Defensive int() — some proxies return created as a string
            # (e.g. "1700000000") or an unexpected type; fall back to 0
            # rather than crashing the entire coordinator update.
            try:
                created = int(m.get("created") or 0)
            except (ValueError, TypeError):
                created = 0
            models.append(
                {
                    "id": mid,
                    "created": created,
                    "owned_by": str(m.get("owned_by") or ""),
                    # Strip surrounding whitespace before the falsy-fallback so a
                    # proxy returning "  " (spaces only) still falls back to mid.
                    "display_name": str((m.get("display_name") or "").strip() or mid),
                }
            )
        models.sort(key=lambda x: (-x["created"], x["id"]))
        if _LOGGER.isEnabledFor(logging.DEBUG):
            chat_count = sum(
                1 for m in models if not any(m["id"].startswith(p) for p in IMAGE_MODEL_ID_PREFIXES)
            )
            _LOGGER.debug(
                "Fetched %d models from %s (%d chat-capable after filtering)",
                len(models),
                self._url,
                chat_count,
            )
        return {"models": models}

    @property
    def chat_models(self) -> list[dict[str, Any]]:
        """Chat-capable models (image-only excluded), in stored order.

        This property only **filters** — it does not sort.  The list is
        returned in the same order as ``self.data["models"]``, which
        ``_async_update_data`` always stores sorted by ``(-created, id)``:
        newest first, alphabetical ``id`` as a tiebreaker for equal timestamps.

        Returns an empty list when:

        * ``self.data`` is ``None`` or ``{}`` (coordinator not yet populated), or
        * ``self.data["models"]`` is not a ``list`` (defensive guard — should
          never happen because ``_async_update_data`` always writes a list, but
          guards against silent corruption or unexpected test fixtures), or
        * every model in ``self.data["models"]`` matches an
          ``IMAGE_MODEL_ID_PREFIXES`` prefix.
        """
        if not self.data:
            return []
        models = self.data.get("models", [])
        if not isinstance(models, list):
            # Defensive: _async_update_data always writes a list, but an
            # unexpected value (dict, string, etc.) would cause the list
            # comprehension below to raise TypeError / AttributeError.
            return []
        return [
            m for m in models if not any(m["id"].startswith(p) for p in IMAGE_MODEL_ID_PREFIXES)
        ]

    @property
    def latest_chat_model_id(self) -> str | None:
        """Id of the newest chat-capable model, or ``None`` if none are known.

        "Newest" follows the ``(-created, id)`` sort applied by
        ``_async_update_data`` — highest timestamp first, alphabetical id as a
        tiebreaker.  Returns ``None`` when:

        * the coordinator has not yet completed its first successful poll, or
        * the proxy only advertises image-generation models.
        """
        chat = self.chat_models
        return chat[0]["id"] if chat else None
