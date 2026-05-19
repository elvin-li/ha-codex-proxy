# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/).

---

## [0.2.3] – 2026-05-19

### Added

- **Proxy-reachable binary sensor** (`binary_sensor.*_proxy_reachable`) — a
  `CONNECTIVITY`-class diagnostic entity that is `ON` when the coordinator's
  last `/v1/models` poll succeeded and `OFF` when it failed. Enables HA
  automations and dashboard badges for proxy health monitoring.
- **Binary sensor translations** — entity name translated to English
  ("Proxy reachable") and Simplified Chinese ("反代可达") in all three
  string files.
- **10 new tests** in `tests/test_binary_sensor.py` covering `is_on` True/False,
  truthy/falsy coercion, unique-id suffix, translation key, device class, and
  `has_entity_name`.

---

## [0.2.2] – 2026-05-19

### Added

- **Refresh models button** (`button.*_refresh_models`) — pressing it triggers
  an immediate out-of-schedule `/v1/models` refresh without waiting 6 hours.
- **`tests/ha_stubs.py`** — shared HA module bootstrap used by test files that
  import coordinator-dependent modules; eliminates the sys.modules ordering
  fragility that caused 22 tests to fail when run in certain orders.

### Changed

- Coordinator now handles both OpenAI-convention `{"object":"list","data":[...]}`
  and bare `[...]` response formats from non-standard proxy implementations.

---

## [0.2.1] – 2026-05-19

### Added

- **Model select entity** (`select.*_active_model`, disabled by default) — dropdown
  per LLM subentry showing all chat-capable models from the proxy; selecting one
  updates the subentry and reloads the config entry immediately.
- `CONTRIBUTING.md` — dev setup, project layout, architecture notes.

### Changed

- Coordinator error messages now include the full URL and exception type
  (e.g. `"Failed to fetch https://proxy/v1/models: ConnectError: ..."`) for
  faster triage in HA logs.

### Tests (86 → 130)

- `test_parse_toml_validate.py`: 18 tests for `_parse_toml_and_validate`
- `test_coordinator_properties.py`: 12 tests for `chat_models` and
  `latest_chat_model_id` properties
- `test_select.py`: 12 tests for `CodexModelSelectEntity`
- `test_update_entity.py`: +2 tests for `_handle_coordinator_update` (live
  subentry refresh from `entry.subentries`)

---

## [0.2.0] – 2026-05-19

### Added

- **Reconfigure flow** — change API Key or proxy URL without deleting the entry
  and losing all subentries (Settings → Devices & Services → Codex Token Pool → ··· → Reconfigure).
- **AI Task subentry** — a `Codex 号池 AI Task` subentry is now created automatically
  on first install alongside the conversation subentry; its own add / reconfigure
  UI allows independent model, reasoning effort, and system prompt settings.
- **Paste config.toml** — paste your existing Codex CLI `config.toml` on the setup
  form and `base_url`, `model`, reasoning effort, and store flag are extracted
  automatically.
- **Diagnostics** — `async_get_config_entry_diagnostics` redacts the API key and
  exports coordinator health, model list, and subentry config for easy bug reports.
- **Diagnostic sensors** (disabled by default):
  - `sensor.*_chat_model_count` — number of chat-capable models on the proxy.
  - `sensor.*_last_model_refresh` — timestamp of the last successful model poll.
- **Coordinator retry / back-off** — transient 5xx errors and timeouts are retried
  up to 3 times with 5 s → 30 s back-off before raising `UpdateFailed`.
- **URL scheme validation** — `ftp://` or bare hostnames now show a clear
  `invalid_url_scheme` / `invalid_url` error instead of falling through to
  `cannot_connect`.
- **TOML no-base_url feedback** — pasting a stock Codex CLI config with no
  `model_providers` table now shows `toml_no_base_url` instead of a cryptic
  `required` error on the base URL field.
- **`release_url` property** on the update entity — links to the OpenAI model
  documentation page for the latest discovered model.
- **`_pure_helpers.py`** — pure-Python TOML parser and URL validator, importable
  without the HA runtime (makes testing trivial).
- **`entity_utils.py`** — shared `build_codex_device_info()` helper used by both
  `conversation.py` and `ai_task.py`.
- **Test suite** — 48 unit tests covering config flow helpers, coordinator model
  processing / deduplication / image filter, update entity logic, and
  `_enrich_subentry_data`; runs on Python 3.12 and 3.13 via GitHub Actions.
- **`pyproject.toml`** with `pytest` and `ruff` configuration.
- **GitHub Actions CI** (`.github/workflows/tests.yml`) — runs on every push and PR.

### Changed

- `async_get_supported_subentry_types` now returns both `conversation` and
  `ai_task_data` handlers.
- Config flow probe code extracted to `_probe_proxy()` — eliminates ~50 lines of
  duplicate exception-handling between the `user` and `reconfigure` steps.
- `_upstream_keys()` result cached at module level; was re-imported on every
  form submission.
- `coordinator.py`: image filter generalised via `IMAGE_MODEL_ID_PREFIXES` tuple
  (was a single hard-coded `gpt-image` prefix check); model deduplication added.
- `manifest.json`: `version` bumped to `0.2.0`; `codeowners` and `homeassistant`
  minimum version added.

### Fixed

- Bare `except Exception` in `__init__.py:96` replaced with
  `except (httpx.HTTPError, UpdateFailed)`.
- Bare `except Exception` in config flow probe replaced with
  `except (TimeoutError, OSError)`.

### Removed

- Dead `_LOGGER` in `conversation.py` and `ai_task.py`.
- Dead `DATA_INSTALLATION_ID` constant from `const.py`.

---

## [0.1.0] – 2025-12-01

### Added

- Initial release.
- Thin shim subclassing `openai_conversation.OpenAIConversationEntity` and
  `OpenAITaskEntity`; routes all requests through a Codex-compatible reverse proxy.
- Required Codex headers on every request (`User-Agent`, `OpenAI-Beta`,
  `originator`, `x-codex-installation-id`).
- `service_tier = None` pinned to avoid proxy 502 on upstream default of `"auto"`.
- `CodexModelCoordinator` — polls `/v1/models` every 6 hours with raw httpx
  (bypasses openai SDK 2.x cursor-page parser incompatibility).
- `CodexModelUpdate` — HA `update` entity showing installed vs latest chat model.
- Config flow with TOML paste support, conversation and AI task subentries.
- Chinese (Simplified) and English translations.
- HACS custom repository support.
