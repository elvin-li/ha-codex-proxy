"""Pure-Python helpers with no Home Assistant dependencies.

Isolated here so unit tests can import and exercise them without needing
a full HA runtime installed.
"""

from __future__ import annotations

import tomllib
from typing import Any
from urllib.parse import urlparse


def parse_codex_toml(text: str) -> dict[str, Any]:
    """Pull the values we care about out of a Codex CLI config.toml.

    Looks at top-level ``model``, ``model_reasoning_effort``,
    ``disable_response_storage``, and the first ``[model_providers.*]`` table
    that has a ``base_url``. Returns a dict with the keys we use; missing
    values are omitted.
    """
    cfg = tomllib.loads(text)
    out: dict[str, Any] = {}
    if isinstance(cfg.get("model"), str):
        out["model"] = cfg["model"].strip()
    if isinstance(cfg.get("model_reasoning_effort"), str):
        out["reasoning_effort"] = cfg["model_reasoning_effort"].strip()
    if "disable_response_storage" in cfg:
        # Codex CLI's disable_response_storage = true ↔ store_responses=False
        out["store_responses"] = not bool(cfg["disable_response_storage"])
    providers = cfg.get("model_providers")
    # TOML allows two forms for "a collection of provider tables":
    # - Named tables: ``[model_providers.mypool]`` → cfg["model_providers"] is dict
    # - Array of tables: ``[[model_providers]]`` → cfg["model_providers"] is list
    # Codex CLI uses the named-table form, but a user pasting from third-party
    # docs or hand-rolling their TOML could end up with the array form.  Pre-
    # v0.2.176 only the dict form was handled and the list form silently
    # produced an empty result that surfaced as ``toml_no_base_url`` with no
    # hint that the TOML structure itself was the issue.
    iter_providers: list = []
    if isinstance(providers, dict):
        iter_providers = list(providers.values())
    elif isinstance(providers, list):
        iter_providers = providers
    for provider in iter_providers:
        if isinstance(provider, dict) and provider.get("base_url"):
            out["base_url"] = str(provider["base_url"]).strip().rstrip("/")
            break
    return out


def validate_base_url(url: str) -> str | None:
    """Return an error key if *url* is not a valid http/https base URL.

    Rejects:
    * Non-http(s) schemes (``ftp://`` etc.)
    * URLs with no netloc (``https://``)
    * URLs carrying a query string (``?key=value``) or fragment (``#anchor``).
      A base URL with query/fragment is almost always a copy-paste artefact
      (the user pasted a deep-linked URL from their browser).  Leaving these
      in place would corrupt the URL after ``normalize_base_url`` appends
      ``/v1`` — e.g. ``https://host.com?x=1`` would become
      ``https://host.com?x=1/v1`` and the OpenAI SDK would emit requests
      to ``https://host.com?x=1/v1/responses`` (404 against any sane proxy).
    * URLs containing userinfo (``https://user:pass@host``).  Userinfo would
      silently flow into the persisted ``entry.data["base_url"]``, the
      coordinator's ``self._url`` exception messages, the debug log line in
      ``_probe_proxy``, the (unredacted) ``entry_data`` block of
      ``async_get_config_entry_diagnostics``, and the
      ``binary_sensor.proxy_reachable.last_error`` state attribute.  Token-
      pool proxies frequently document credentialed URLs in their onboarding
      pages, so a user pasting from such a doc would unknowingly exfiltrate
      their password into HA's persistent storage and downloadable
      diagnostics file — both of which are routinely shared in bug reports.
      The proxy's API key is supplied separately through ``CONF_API_KEY``;
      embedding credentials in the URL is never the right approach for this
      integration.
    """
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return "invalid_url_scheme"
    if not p.netloc:
        return "invalid_url"
    if p.query or p.fragment:
        # Treat both as the same user-visible error to keep the strings.json
        # surface area minimal — the message tells users to drop the query
        # and fragment from the URL.
        return "invalid_url"
    if p.username is not None or p.password is not None:
        # Same error key as query/fragment — both communicate "your URL has
        # parts that don't belong in a base URL".  A dedicated translation
        # key could be nicer UX but would require strings.json updates in
        # three files for a corner case most users will never hit.
        return "invalid_url"
    return None


def normalize_base_url(url: str) -> str:
    """Return *url* normalised to the OpenAI-compatible form (ends with ``/v1``).

    The OpenAI Python SDK treats ``base_url`` as the "OpenAI-compatible base"
    and appends path components like ``/responses``, ``/chat/completions``, and
    ``/models`` directly to it.  For OpenAI proper, ``base_url`` is
    ``https://api.openai.com/v1`` — note the trailing ``/v1``.

    Codex-style reverse proxies follow the same convention, but users
    frequently paste the bare host (``https://proxy.example.com``) into the
    config flow because the proxy's own UI shows the host without ``/v1``.
    Some lenient proxies silently accept both forms; stricter ones (e.g.
    ``tokenclub.top``) require the ``/v1`` and respond to ``/responses`` with
    the proxy's HTML landing page, producing the cryptic
    ``Last content in chat log is not an AssistantContent`` error in HA.

    This helper makes the two forms interchangeable from the user's
    perspective:

    * ``https://proxy.example.com``        → ``https://proxy.example.com/v1``
    * ``https://proxy.example.com/``       → ``https://proxy.example.com/v1``
    * ``https://proxy.example.com/v1``     → ``https://proxy.example.com/v1``
    * ``https://proxy.example.com/v1/``    → ``https://proxy.example.com/v1``
    * ``https://proxy.example.com/api/v1`` → ``https://proxy.example.com/api/v1``
      (already has ``/v1`` at the end of the path — left alone so vendor-
      specific prefixes like ``/api/v1`` continue to work)

    The caller still owns scheme/netloc validation — call ``validate_base_url``
    first.  This function does not raise; it always returns a string.
    """
    trimmed = url.rstrip("/")
    # Treat the URL as already-normalised iff the last segment **of the path**
    # (not the whole URL string) is exactly ``"v1"``.  We must parse the URL
    # before checking, otherwise an absurd-but-legal hostname like
    # ``https://v1`` would match by accident: ``"https://v1".rsplit("/", 1)``
    # returns ``["https:", "", "v1"]``, the last element is ``"v1"``, and the
    # old shortcut would return the URL unchanged — the coordinator would then
    # build ``https://v1/models`` (no ``/v1`` prefix) and strict proxies 404.
    parsed = urlparse(trimmed)
    path_tail = parsed.path.rsplit("/", 1)[-1] if parsed.path else ""
    if path_tail == "v1":
        return trimmed
    return f"{trimmed}/v1"
