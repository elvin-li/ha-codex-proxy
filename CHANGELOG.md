# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

<!-- Add new changes here. Move to a versioned section on release. -->

---

## [0.2.33] – 2026-05-19

### Changed

- **`coordinator.py`** — The bare `except ValueError` around `r.json()` is
  narrowed to `except json.JSONDecodeError`.  `json.JSONDecodeError` is a
  subclass of `ValueError` and is the only exception `httpx` raises from
  `.json()`.  Using the specific type documents intent and avoids accidentally
  swallowing unrelated `ValueError`s (e.g. from a future refactor that adds
  value parsing inside the same try block).  Requires `import json` added at
  the top of the module.

### Added (tests)

- `test_model_select.py` — `test_null_display_name_falls_back_to_id`: passes a
  model dict with `display_name=None` explicitly (not just a missing key) to
  verify the `or mid` fallback in `_model_select_options`.
- `test_diagnostics.py` — `test_models_empty_when_coordinator_data_is_empty_dict`:
  verifies `coordinator.data = {}` (dict present, `"models"` key absent) returns
  `models == []` instead of a `KeyError`.
- `test_translations.py` — `test_no_empty_data_description_values`: iterates
  all `config_subentries.<type>.step.<step>.data_description.*` values across all
  three translation files and asserts none are empty strings.
- `test_coordinator_retry.py` — `test_bad_json_raises_immediately` updated to
  use `json.JSONDecodeError("bad json", "", 0)` instead of plain `ValueError` to
  match the narrowed `except` clause and document real httpx behaviour.

---

## [0.2.32] – 2026-05-19

### Fixed (stubs)

- **`tests/ha_stubs.py`** — `SelectOptionDict` is now a real dict factory
  (`**kwargs → dict`) instead of a `MagicMock`.  The old stub caused
  `o["value"]` to return another `MagicMock`, making any test that inspects
  option values silently pass even when the wrong options were produced.

### Changed (tests)

- `test_subentry_flow.py` — Added `_make_coordinator_with_models` helper and
  updated `_make_flow` to accept an optional `coordinator` argument that wires
  it into `hass.data`.  New class `TestBuildSchemaWithCoordinator` covers:
  - Form shown when coordinator has models (smoke test)
  - `_model_select_options` returns options whose `value` fields match the
    coordinator model IDs (catches the now-working `SelectOptionDict` stub)
  - Empty coordinator falls back to DEFAULT_MODEL (no crash)

---

## [0.2.31] – 2026-05-19

### Fixed

- **`config_flow.py`** — `openai.RateLimitError` (HTTP 429) during the proxy
  probe now returns the new `"rate_limited"` error key instead of
  `"cannot_connect"`.  The old message ("Cannot reach the proxy…") was
  misleading — the proxy is reachable, but the API quota is exhausted.
  New message: "The proxy returned HTTP 429 — your API quota is exhausted.
  Wait before retrying."

- **`entity_utils.py`** — `build_codex_device_info` (subentry-level devices)
  now includes `sw_version=_INTEGRATION_VERSION`, matching the entry-level
  helper.  Both device cards in HA's UI now show the installed version.

- **`config_flow.py`** — Added inline comment explaining why `reasoning_effort`
  and `store_responses` from a pasted TOML are intentionally discarded in the
  main-entry reconfigure step (they belong to subentry-level config).

### Changed (tests)

- `test_probe_proxy.py` — `test_rate_limit_returns_cannot_connect` renamed to
  `test_rate_limit_returns_rate_limited` and assertion updated to `"rate_limited"`.
- `test_binary_sensor.py` — `_make_sensor()` now explicitly sets
  `coord.last_update_success_time` to a datetime so the post-poll branch of
  `is_on` is actually exercised (not the "unknown before first poll" guard via a
  truthy `MagicMock()`).
- `test_const.py` — `test_coordinator_retry_delays_length_consistent` now uses
  `==` instead of `>=`; any future drift between the delay table and retry count
  is caught immediately rather than silently leaving dead entries.
- `test_update_entity.py` — `test_install_updates_subentry_and_reloads` now
  inspects the `data` kwarg passed to `async_update_subentry` and asserts
  `data[UPSTREAM_CONF_CHAT_MODEL] == "gpt-5.6"`.
- `test_coordinator_retry.py` — `test_raises_update_failed_after_max_retries`
  now asserts `coord._http.get.call_count == COORDINATOR_MAX_RETRIES`.
- `test_subentry_flow.py` — Added `test_llm_hass_api_defaults_to_empty_list`
  and three `TestAITaskReconfigure` smoke tests covering the AI Task subentry
  reconfigure path (form display, submit, service_tier=None invariant).
- `test_entity_utils.py` — `test_sw_version_is_present` added to
  `TestBuildCodexDeviceInfo`.

### Added (strings)

- `"rate_limited"` error key in `strings.json`, `translations/en.json`, and
  `translations/zh-Hans.json`.

---

## [0.2.30] – 2026-05-19

### Fixed

- **`coordinator.py`** — `NameError` in debug log: after moving URL construction
  into `__init__`, the `_LOGGER.debug` call inside `_async_update_data` still
  referenced the now-deleted local variable `url`.  Fixed to use `self._url`.

- **`coordinator.py`** — URL and headers are now pre-built in `__init__` as
  `self._url` and `self._headers` instead of being reconstructed on every poll.
  Removes three now-unused instance attributes (`_api_key`, `_base_url`,
  `_installation_id`) from the coordinator.

- **`update.py`** — `release_summary` and `title` properties now return English
  strings instead of Chinese.  `release_url` always returns `None` (proxy model
  IDs are not necessarily OpenAI model IDs, so a platform.openai.com URL would
  be misleading).

- **`__init__.py`** — Removed the dead `_async_update_listener` function and its
  `entry.add_update_listener(…)` registration call.  The listener was never
  reachable because no options flow exists; removing it eliminates a misleading
  code path.

- **`const.py`** — Added coupling comment documenting the invariant between
  `COORDINATOR_MAX_RETRIES` and `COORDINATOR_RETRY_DELAYS`.

### Changed (tests)

- `test_coordinator_init.py` — updated to test `_url` and `_headers` instead of
  the removed `_api_key`, `_base_url`, `_installation_id` attributes; added
  coverage for all six header keys.
- `test_coordinator_retry.py`, `test_coordinator_logging.py`,
  `test_coordinator_request.py` — `_make_coordinator()` helpers updated to set
  `coord._url` and `coord._headers` directly (matching the new `__init__`
  contract) instead of the removed per-component attributes.
- `test_setup_unload.py` — removed import and tests for the deleted
  `_async_update_listener` function.
- `test_update_entity.py` — updated `TestReleaseSummary`, `TestReleaseUrl`, and
  `TestTitle` to match the new English strings and the `release_url = None`
  policy.

---

## [0.2.29] – 2026-05-19

### Fixed

- **`select.py`** — `current_option` now returns `DEFAULT_MODEL` when the
  stored value is explicitly `None` (not just when the key is absent).  An
  older version of the integration could write `None` into subentry data; with
  this fix the entity will never surface `None` as `current_option`, which
  would cause HA to log a "current option not in options" warning.
  Return type is narrowed from `str | None` to `str`.

- **`entity_utils.py`** — The broad `except Exception` guard around the
  manifest-version read is now `except (OSError, ValueError, KeyError)`.
  This still catches all realistic file-I/O and JSON-parse failures while
  avoiding suppression of unexpected errors (e.g. `MemoryError`, `SystemExit`).

### Added (tests)

- **`tests/test_select.py`** — `test_falls_back_to_default_when_value_is_none`
  verifies that `current_option` returns `DEFAULT_MODEL` when the subentry
  stores an explicit `None`.

- **`tests/test_setup_entry.py`** — `test_httpx_http_error_is_non_fatal`
  verifies that `httpx.HTTPError` during `async_config_entry_first_refresh` is
  caught by the `except (httpx.HTTPError, UpdateFailed)` clause in
  `async_setup_entry` and does not prevent the entry from loading.  (Only
  `UpdateFailed` was covered before.)

---

## [0.2.28] – 2026-05-19

### Fixed

- **`binary_sensor.py`** — `is_on` now returns `None` (HA "unknown" state)
  before the coordinator has completed any successful poll.  Previously, HA's
  `DataUpdateCoordinator` initialises `last_update_success = True` even before
  the first network call completes, so the sensor would transiently report
  "connected" during HA startup even when the proxy has never been reached.
  The fix checks `last_update_success_time is None` as the sentinel for
  "not yet polled".  Return type is widened from `bool` to `bool | None` to
  match HA's interface.

- **`config_flow.py`** — TOML `model_reasoning_effort` values that are not in
  `REASONING_EFFORTS` (e.g. `"turbo"`, `"ultra"`) are now silently ignored
  with a `_LOGGER.warning` and the default effort is used.  Previously the
  invalid string was stored verbatim in the config entry, which the UI would
  later reject when showing the subentry settings.

- **`diagnostics.py`** — Subentry `data` dicts are now passed through
  `async_redact_data` before being included in the diagnostics bundle.
  Previously, if a future refactor stored a sensitive value (e.g. an
  `api_key`) inside a subentry, it would be leaked in the diagnostics
  download.

### Added (tests)

- **`tests/test_binary_sensor.py`** — 2 new `TestIsOn` cases:
  `test_is_none_before_first_successful_poll` and
  `test_is_on_after_first_successful_poll`.
- **`tests/test_parse_toml_validate.py`** — 2 new cases:
  `test_invalid_reasoning_effort_from_toml_uses_default` (verifies the
  warning path) and `test_valid_reasoning_effort_from_toml_used` (iterates all
  four valid efforts).
- **`tests/test_diagnostics.py`** — 2 new `TestDiagnosticsSubentryRedaction`
  cases: `test_subentry_data_api_key_redacted` and
  `test_subentry_non_sensitive_data_preserved`.

---

## [0.2.27] – 2026-05-19

### Fixed

- **`config_flow.py:_probe_proxy`** — Four additional `openai` exception types
  that previously propagated uncaught (crashing the config flow UI) are now
  handled:
  - `openai.PermissionDeniedError` (HTTP 403) → `"invalid_auth"`
  - `openai.RateLimitError` (HTTP 429) → `"cannot_connect"`
  - `openai.InternalServerError` (HTTP 500) → `"cannot_connect"`
  - `openai.UnprocessableEntityError` (HTTP 422) → `"unknown_model"` if
    "model" appears in the error message, else `"unknown"`

- **`coordinator.py:_async_update_data`** — HTTP 4xx responses (e.g. 401
  Unauthorized, 403 Forbidden) are no longer retried three times (which
  previously wasted up to 35 seconds).  Only genuine transient errors — HTTP
  5xx and connection/timeout exceptions — trigger the retry/back-off loop;
  4xx errors now raise `UpdateFailed` immediately.  The retry logic was also
  refactored to eliminate the duplicated delay-sleep block.

### Added (tests)

- **`tests/test_probe_proxy.py`** — 6 new test classes covering the previously
  unhandled exception paths: `TestProbeProxyPermissionDenied`,
  `TestProbeProxyRateLimit`, `TestProbeProxyInternalServerError`,
  `TestProbeProxyUnprocessableEntity` (2 cases).
- **`tests/test_coordinator_retry.py`** — 3 new tests:
  `test_4xx_raises_immediately_without_retry` (401),
  `test_403_raises_immediately`, `test_5xx_still_retried`.  The
  `_make_response` helper also fixed to properly set `response.status_code`
  (integer, not `MagicMock`) on the `httpx.HTTPStatusError` so the `< 500`
  guard in production code works correctly under test.
- **`tests/test_coordinator_logging.py`** — Same `_make_response` fix applied.

---

## [0.2.26] – 2026-05-19

### Fixed

- **`select.py`** — `async_select_option` now captures `old_model` from
  `current_option` *before* calling `async_update_subentry`.  Previously the
  log message "changed from X to Y" could show the new model for both
  positions if the mock/implementation updated the subentry data in-place
  before the log line executed.

### Improved (tests)

- **`tests/test_select.py`** — `test_info_logged_on_model_change` now
  asserts that the *old* model id appears in the log call-args in addition to
  the new one, confirming the capture-before-update fix is exercised.
- **`tests/ha_stubs.py`** — `UpdateFailed` is now a proper `Exception`
  subclass (`_UpdateFailed(Exception)`) rather than an alias of bare
  `Exception`.  This lets tests use `pytest.raises(UpdateFailed)` without
  triggering the `B017` ruff rule and makes `except UpdateFailed` in
  production code behave correctly in the test environment.
- **`tests/test_coordinator_retry.py`** — All `pytest.raises(Exception)` calls
  replaced with `pytest.raises(UpdateFailed)`; nested `with` statements
  combined into single parenthesised `with` blocks (`SIM117`); unused `hass`
  variable removed (`F841`); `# isort: skip_file` added to preserve
  bootstrapping-required import order.
- **`tests/test_setup_entry.py`** — `first_refresh_side_effect` changed from
  bare `Exception(...)` to `UpdateFailed(...)` so the `except UpdateFailed`
  branch in `async_setup_entry` is correctly exercised.
- **`tests/test_pure_helpers.py`** — `test_invalid_toml_raises` now uses
  `pytest.raises(tomllib.TOMLDecodeError)` instead of bare `Exception`.
- Across all test files: 116 ruff auto-fixes applied (unused imports, import
  sorting, `timezone.utc` → `UTC`, etc.).

---

## [0.2.25] – 2026-05-19

### Added

- **`binary_sensor.py`** — `extra_state_attributes` now includes
  `latest_model` (the newest chat-capable model id known to the coordinator)
  alongside the existing `last_checked` timestamp.  Previously, automations
  that wanted to act on the current model had to enable the select or update
  entity; now the reachability sensor itself carries that information.

  Both attributes are omitted individually when the coordinator doesn't have
  data yet (`last_checked` absent before first successful poll;
  `latest_model` absent when there are no chat models).  The property returns
  `None` only when both would be absent.

### Added (tests)

- **`tests/test_binary_sensor.py`** — 5 new `TestExtraStateAttributes` cases
  replacing the old 3: `test_latest_model_present_when_coordinator_has_model`,
  `test_latest_model_absent_when_coordinator_has_no_model`,
  `test_both_attributes_present_after_successful_poll`,
  `test_only_latest_model_when_no_timestamp`,
  `test_none_when_both_time_and_model_are_none`.

  Also extracted a shared `_make_sensor_with_coord()` helper to eliminate
  per-test boilerplate.

---

## [0.2.24] – 2026-05-19

### Added

- **`diagnostics.py`** — The diagnostics download now includes
  `"integration_version"` at the top level (read from `manifest.json` via the
  existing `_INTEGRATION_VERSION` constant in `entity_utils.py`).  Previously,
  maintainers had to ask reporters which version they had installed; now it
  appears verbatim in every diagnostics bundle.
- **`tests/test_diagnostics.py`** — 2 new `TestDiagnosticsIntegrationVersion`
  tests: `test_integration_version_present` and
  `test_integration_version_matches_manifest`.
- **`CHANGELOG.md`** — Added `[Unreleased]` section at the top per the PR
  template reference to `[Unreleased]`.
- **`.github/pull_request_template.md`** — Checklist now includes explicit
  `pytest --cov` and `ruff format --check` steps; removed the ambiguous
  "new code is covered by tests" line in favour of the quantitative 100%
  criterion.

---

## [0.2.23] – 2026-05-19

### Added (tests)

- **`tests/test_reconfigure_flow.py`** — 7 new tests covering three
  previously uncovered paths in `config_flow.py`:
  - `TestReconfigureInitialForm`: `async_step_reconfigure(None)` shows the
    form pre-filled with current entry values (line 312) without probing the
    proxy.
  - `TestReconfigureValidationErrors`: invalid URL scheme and malformed TOML
    trigger the validation-error re-show path (line 326) without calling the
    probe.
  - `TestAsyncGetSupportedSubentryTypes`: the `@classmethod` on
    `CodexConfigFlow` registers `conversation` → `ConversationSubentryFlowHandler`
    and `ai_task_data` → `AITaskSubentryFlowHandler` (line 354).
- **`tests/test_select.py`** — 1 new `TestOptions` case:
  `test_fallback_to_default_when_current_is_none_and_coordinator_empty` covers
  `select.py:112` — the `result.append(DEFAULT_MODEL)` fallback when
  `current_option` returns `None` (explicit `None` stored in subentry data)
  and the coordinator has no models.
- **`entity_utils.py`** — added `# pragma: no cover` to the module-level
  `except Exception` fallback block (lines 18-19); the block only runs when
  `manifest.json` cannot be read at import time, which is untestable without
  complex module-reimport machinery.

**Coverage:** 100% (601 statements, 0 missed) across all 14 source files.

---

## [0.2.22] – 2026-05-19

### Changed

- **`sensor.py`** — Both `SensorEntityDescription` objects now carry
  `translation_key=` matching their `key=` value.  Previously only `name=`
  (hard-coded English) was set; adding `translation_key` lets HA resolve entity
  names from `strings.json` / `translations/` when a non-English locale is active.

### Added (tests / CI)

- **`tests/test_sensor.py`** — 3 new `TestEntityDescriptions` cases:
  `test_chat_model_count_translation_key`,
  `test_last_refresh_translation_key`,
  `test_translation_keys_match_strings_json` (cross-checks `translation_key`
  values against `strings.json entity.sensor`).
- **`pytest-cov>=5.0`** added to `requirements_test.txt` and
  `[tool.coverage]` section added to `pyproject.toml`.
- **`.github/workflows/tests.yml`** — test step now runs with
  `--cov=custom_components/codex_proxy --cov-report=term-missing` and
  uploads `coverage.xml` as a CI artefact (Python 3.13 matrix only).

### Refactored (tests)

- **`tests/test_coordinator_logging.py`** — migrated from 35-line inline
  HA-module stub to `import tests.ha_stubs`, matching all other test files.
  The outdated comment "use the same inline-stub pattern as
  test_coordinator_retry.py" has been corrected (both files now use
  `ha_stubs`).

---

## [0.2.21] – 2026-05-19

### Fixed

- **`coordinator.py`** — `_async_update_data` now wraps `int(m["created"] or 0)`
  in a `try/(ValueError, TypeError)` guard. Previously, a proxy returning
  `"created": "2024-01-01"` (ISO date string) would raise `ValueError` outside
  the retry try/except block and crash the entire coordinator update; now it
  falls back gracefully to `created=0` so sorting still works.

### Added (tests)

- **`tests/test_coordinator.py`** — 3 new `TestModelProcessing` cases:
  `test_numeric_string_created_is_accepted`,
  `test_non_numeric_string_created_falls_back_to_zero`,
  `test_none_created_is_zero`.
- **`tests/test_coordinator_retry.py`** — 2 new `TestPayloadFormats` cases:
  `test_non_numeric_created_field_does_not_crash` (end-to-end via the actual
  `_async_update_data` method),
  `test_numeric_string_created_is_parsed` (verifies sort order still correct).

---

## [0.2.20] – 2026-05-19

### Added (tests)

- **`tests/test_translations.py`** — 2 new tests:
  - `test_config_subentries_keys_consistent_across_all_files`: verifies that
    `config_subentries` subentry types and step keys are identical across
    `strings.json`, `en.json`, and `zh-Hans.json`.
  - `test_all_translation_keys_in_sync`: deep structural check — flattens all
    three translation files into dotted key paths and asserts they are
    identical, catching any key added to one file but forgotten in the others
    at any nesting depth.

---

## [0.2.19] – 2026-05-19

### Changed (CI + code style)

- **All source and test files** reformatted with `ruff format` for consistent
  style (blank lines after docstrings, trailing comma normalisation, etc.).
  Logic is unchanged — purely mechanical.
- **`.github/workflows/tests.yml`** — added `ruff format --check
  custom_components/codex_proxy/ tests/` step in the `lint` job so the CI
  gate catches format drift on every push/PR.
- **`CONTRIBUTING.md`** — updated project-layout table to list all 13 source
  files and all 30 test files accurately; bumped test count to 380+.

---

## [0.2.18] – 2026-05-19

### Changed

- **`entity_utils.py`** — `build_codex_entry_device_info` now populates
  `sw_version` from `manifest.json` (read once at import time with a
  graceful fallback), so the HA device card always shows the installed
  integration version without manual maintenance.
- **`const.py`** — removed two dead constants that were defined but never
  imported anywhere: `DEFAULT_CONTEXT_WINDOW = 1_000_000` and
  `DEFAULT_BASE_URL = ""`.

### Added (tests)

- **`tests/test_entity_utils.py`** — 2 new tests:
  `test_sw_version_is_populated` and `test_sw_version_matches_manifest`,
  verifying that the device card `sw_version` is non-empty and matches
  the manifest exactly.

---

## [0.2.17] – 2026-05-19

### Added (tests)

- **`tests/test_main_flow.py`** (12 tests) — direct unit tests for
  `CodexConfigFlow.async_step_user`: form displayed on initial load,
  form with errors on bad URL / failed probe, and entry creation on
  success (correct data, title, 2 subentries, both with
  `service_tier=None`).

---

## [0.2.16] – 2026-05-19

### Added (tests + CI)

- **`tests/test_subentry_flow.py`** (12 tests) — unit tests for
  `ConversationSubentryFlowHandler` and `AITaskSubentryFlowHandler`:
  class attributes, `async_step_user` (form + entry creation with
  `service_tier=None`), and `async_step_reconfigure` (form pre-fill,
  `async_update_and_abort` call, preservation of existing keys like
  `llm_hass_api`).
- **`.github/workflows/tests.yml`** — `test` job now declares
  `needs: lint`, so the test matrix only runs if linting passes, saving
  CI minutes on style regressions.

---

## [0.2.15] – 2026-05-19

### Fixed

- **`config_flow.py` — `async_step_reconfigure` preserves `CONF_INSTALLATION_ID`**:
  Previously, the reconfigure step passed only `{CONF_API_KEY: ..., CONF_BASE_URL: ...}`
  to `async_update_reload_and_abort`, silently dropping `CONF_INSTALLATION_ID`
  (and any other existing entry fields). On the next reload, `async_setup_entry`
  would generate a fresh UUID, resetting proxy-side quota/session tracking.
  Fixed by spreading `**entry.data` so all existing fields are preserved and
  only the changed keys are overwritten.

### Added (tests)

- **`tests/ha_stubs.py`** — added real `_ConfigFlow` and `_ConfigSubentryFlow`
  stub classes so that `class CodexConfigFlow(ConfigFlow, domain=DOMAIN)` in
  config_flow.py produces a genuine Python class (not a MagicMock), enabling
  direct unit tests of the flow methods.
- **`tests/test_reconfigure_flow.py`** (5 tests) — verifies that
  `async_step_reconfigure` passes `{**entry.data, api_key: ..., base_url: ...}`
  to HA, preserving `CONF_INSTALLATION_ID` and any other future entry fields.

---

## [0.2.14] – 2026-05-19

### Changed

- **`sensor.py`** — use `AddConfigEntryEntitiesCallback` instead of the
  deprecated `AddEntitiesCallback` for consistency with all other platform
  files (`button.py`, `select.py`, `update.py`, `conversation.py`,
  `ai_task.py`).

---

## [0.2.13] – 2026-05-19

### Added (tests)

- **`test_pure_helpers.py`** — 5 new tests:
  - `test_integer_base_url_coerced_to_string` — a provider with a non-string
    `base_url` (TOML allows integers) is coerced via `str()` rather than
    crashing.
  - `test_provider_missing_base_url_skipped` — a provider table with no
    `base_url` key doesn't produce a `base_url` entry in the output.
  - `test_ipv4_address_accepted` — `http://192.168.1.x:port` is valid.
  - `test_ipv6_address_accepted` — `http://[::1]:8080` is valid.
- **`test_button.py::TestRefreshModelsButton::test_press_emits_debug_log`**
  (1 test) — `async_press` must emit exactly one `DEBUG` log so operators can
  confirm the manual refresh was triggered.

---

## [0.2.12] – 2026-05-19

### Added (tests)

- **`TestTranslationKeyConsistency`** — 3 new tests in `test_translations.py`:
  - `test_entity_platform_keys_consistent_across_all_files` — verifies all
    three files declare the same entity platform keys.
  - `test_entity_keys_consistent_across_all_files` — within each platform,
    the entity keys must match across strings/en/zh-Hans.
  - `test_all_entity_keys_have_name_field` — every entity entry must have a
    non-empty `name` field so HA can render human-readable labels.

---

## [0.2.11] – 2026-05-19

### Changed

- **`_pure_helpers.py`**: moved `from urllib.parse import urlparse` from inside
  the `validate_base_url` function body to module-level — avoids a repeated
  local import on every URL validation call and follows Python convention.

### Added (tests)

- **`TestUpstreamKeys`** in `test_enrich_subentry.py` (4 tests):
  - `test_returns_dict_with_expected_keys` — verifies all 5 required keys
    (`chat_model`, `prompt`, `reasoning_effort`, `store_responses`,
    `service_tier`) are present in the returned dict.
  - `test_all_values_are_non_empty_strings` — guards against a stale fallback
    returning an empty or non-string value for any key.
  - `test_second_call_returns_same_object` — the caching contract: two calls
    must return the identical `dict` object (identity check with `is`).
  - `test_cache_is_not_none_after_first_call` — `_UPSTREAM_KEYS_CACHE` is
    populated after the first call.

---

## [0.2.10] – 2026-05-19

### Fixed (lint)

- **`__init__.py`**: removed unused `ConfigEntryAuthFailed` and
  `ConfigEntryNotReady` imports (F401 — they were carried over from an early
  draft before the exception handling was simplified to `httpx.HTTPError`).
- **`config_flow.py`**: moved relative imports (`._pure_helpers`) after
  third-party imports to satisfy isort/I001 ordering rules.
- **`coordinator.py`**: removed redundant quotes from `entry: "ConfigEntry"`
  annotation — redundant because `from __future__ import annotations` already
  makes all annotations lazy (UP037).
- **`select.py`**: removed unused `from typing import Any` import (F401).

### Added (CI)

- **Ruff lint job** added to `.github/workflows/tests.yml` — runs as a
  separate `lint` job on Python 3.13 before the test matrix so style issues
  are caught on every push/PR without duplicating effort across matrix legs.

### Added (test)

- **`test_select.py::TestClassAttributes::test_entity_category_is_config`**
  (1 test) — verifies `_attr_entity_category is EntityCategory.CONFIG`.

---

## [0.2.9] – 2026-05-19

### Fixed

- **`select.py` missing `config_subentry_id`** — `async_setup_entry` was calling
  `async_add_entities(entities)` once for all subentry entities without passing
  `config_subentry_id`. This meant HA could not automatically remove a select
  entity when its parent subentry was deleted. Changed to a per-subentry loop
  matching the pattern used in `update.py`, `conversation.py`, and `ai_task.py`.

### Added

- **`test_platform_setup.py::TestSelectSetup::test_select_config_subentry_id_passed`**
  (1 test) — regression guard verifying that both LLM subentries are registered
  with their correct `config_subentry_id` (never `None`).
- **`test_platform_setup.py::TestUpdateSetup::test_update_config_subentry_id_passed`**
  (1 test) — same coverage for the update platform.

---

## [0.2.8] – 2026-05-19

### Added

- **`tests/test_coordinator_init.py`** (7 tests) — exercises the actual
  `CodexModelCoordinator.__init__` code path (using the ha_stubs
  `DataUpdateCoordinator` base class) to verify `_api_key`, `_base_url`
  (including trailing-slash strip), `_installation_id`, `_http` client,
  `update_interval`, and coordinator `name` are wired correctly.
- **`TestRetryDelayClamping`** in `test_coordinator_retry.py` (1 test) —
  asserts both sleep calls use the exact delay values from
  `COORDINATOR_RETRY_DELAYS`; acts as a regression guard for the safe-access
  fix below.

### Fixed

- **Coordinator retry delay safe access** — `COORDINATOR_RETRY_DELAYS[attempt]`
  could `IndexError` if `COORDINATOR_MAX_RETRIES` were ever increased beyond
  `len(COORDINATOR_RETRY_DELAYS) + 1`. Changed to
  `COORDINATOR_RETRY_DELAYS[min(attempt, len(COORDINATOR_RETRY_DELAYS) - 1)]`
  so the last delay value is reused for any extra retries.

### Added (class-attribute tests)

- `test_button.py` — `TestClassAttributes` (4 tests): `has_entity_name`,
  `translation_key`, `entity_category=DIAGNOSTIC`, `device_class=UPDATE`.
- `test_sensor.py` — `TestClassAttributes` (1) + `TestEntityDescriptions` (6):
  description keys, `entity_registry_enabled_default=False`, `state_class=
  MEASUREMENT`, `device_class=TIMESTAMP`.

---

## [0.2.7] – 2026-05-19

### Added

- **`tests/test_pure_helpers.py`** (17 tests) — direct coverage for
  `parse_codex_toml` and `validate_base_url` from `_pure_helpers.py`,
  complementing the existing `test_config_flow.py` indirect tests; uses the
  standard package import path (with ha_stubs bootstrap) rather than
  `importlib.util.spec_from_file_location`.
- **`tests/test_coordinator_request.py`** (10 tests) — verifies that
  `_async_update_data` sends the correct URL (`base_url + /v1/models`),
  all required headers (`Authorization`, `User-Agent`, `OpenAI-Beta`,
  `originator`, `x-codex-installation-id`, `Accept`), and
  `timeout=COORDINATOR_TIMEOUT_S` on each poll.

### Fixed

- **Coordinator debug-log eagerness** — the `sum(...)` computing chat-capable
  model count was evaluated unconditionally even when DEBUG logging was
  disabled. Guarded behind `if _LOGGER.isEnabledFor(logging.DEBUG):` to
  avoid the list scan on every successful poll in production (where the log
  level is typically INFO).

### Changed

- `test_coordinator_logging.py::TestSuccessLogging::test_success_log_shows_zero_for_image_only`
  — updated to mock the full `_LOGGER` (setting `isEnabledFor.return_value =
  True`) so the guard is exercised correctly; assertion now checks the
  third positional arg of the `"Fetched … models"` call directly.

---

## [0.2.6] – 2026-05-19

### Added

- **`build_codex_entry_device_info(entry)`** in `entity_utils.py` — shared helper
  for entry-level device info (binary_sensor, button, sensor). Removes the
  identical 5-line DeviceInfo block that was duplicated across all three files.
- **`LLM_BEARING_SUBENTRY_TYPES`** in `const.py` — canonical tuple replacing private
  `_LLM_BEARING_SUBENTRY_TYPES` defined identically in `select.py` and `update.py`.
- **21 new tests** (231 total):
  - `test_conversation_entity.py` (8) — `CodexConversationEntity` and `CodexAITaskEntity`
    device_info wiring; required adding `_OpenAIConversationEntity` / `_OpenAITaskEntity`
    real stubs to `ha_stubs.py` so the shim subclasses can be imported in tests.
  - `test_platform_setup.py` (+6) — conversation and ai_task `async_setup_entry` entity
    type, subentry filtering, and `config_subentry_id` forwarding.
  - `test_entity_utils.py` (+5) — `build_codex_entry_device_info` identifier, name,
    manufacturer, no-model-key, and uniqueness.
  - `test_update_entity.py` (+2) — `CodexModelUpdate.title` property.

### Fixed

- **Dead `TYPE_CHECKING` import** and empty `if TYPE_CHECKING: pass` block removed
  from `sensor.py`.

### Changed

- `binary_sensor.py`, `button.py`, `sensor.py` — use
  `build_codex_entry_device_info` instead of inline DeviceInfo construction;
  redundant `dr` imports and the private `_device_info()` function in `sensor.py`
  removed.
- `ha_stubs.py` — added `_OpenAIConversationEntity` and `_OpenAITaskEntity` real
  Python classes; wired `openai_conversation.{conversation,ai_task,const}` submodule
  attributes onto parent mock so attribute-lookup and `sys.modules` resolve the same
  configured object.

---

## [0.2.5] – 2026-05-19

### Added

- **20 new tests** across 3 new test files:
  `test_migrate_entry.py` (4), `test_setup_unload.py` (6), `test_setup_entry.py` (7),
  plus 3 edge-case additions to `test_diagnostics.py` — suite now at 210 tests.
  New coverage: `async_migrate_entry`, `async_unload_entry`, `_async_update_listener`,
  `async_setup_entry` installation-id generation/reuse, non-fatal coordinator
  first-refresh failure, and `diagnostics.py` `coordinator.data=None` path.

### Changed

- **`test_coordinator_retry.py`** — migrated from 40-line inline stub block (which
  unconditionally overwrote `DataUpdateCoordinator` and could poison test ordering)
  to `import tests.ha_stubs`. All 14 tests continue to pass.
- **`test_parse_toml_validate.py`** — migrated from 43-line inline stub block to
  `import tests.ha_stubs`. All 18 tests continue to pass.

---

## [0.2.4] – 2026-05-19

### Added

- **`select.py` stale-subentry fix** — `_handle_coordinator_update` override
  re-reads `_subentry` from the live entry registry on each coordinator poll,
  so `current_option` stays correct after external config-flow edits.
- **Coordinator debug logging** — retry attempts now log `(attempt N/M,
  error type, sleep delay)`; success logs total model count + chat-capable
  count. Useful for diagnosing sporadic proxy connectivity issues.
- **README entity reference table** — complete table of all 6 entities split
  into default-enabled (binary_sensor, button, update) and default-disabled
  (sensor×2, select); documents `last_checked` attribute on binary_sensor.
- **42 new tests** across 5 new test files:
  `test_entity_utils.py` (7), `test_init.py` (15), `test_coordinator_logging.py`
  (5), `test_platform_setup.py` (10), `test_binary_sensor.py` extras (3 new),
  `test_select.py` extras (2 new).

### Fixed

- **`@callback` guard bug** in `ha_stubs.py` — guard `if not callable(...)`
  never fired (MagicMock is callable), so `@callback` decorated methods in
  `select.py` and `update.py` were silently replaced by MagicMock instances.
  Now always assigns `_CORE.callback = lambda f: f`.
- **Test ordering fragility** — migrated all remaining inline-stub test files
  (`test_select.py`, `test_coordinator_properties.py`, `test_model_select.py`,
  `test_update_entity.py`) to `ha_stubs.py`; fixed `_CoordinatorEntityBase`
  missing `__init__` that caused `test_platform_setup.py` to fail in the full
  suite.

### Changed

- `ha_stubs.py`: wire parent→submodule attributes so `from homeassistant.helpers
  import device_registry as dr` resolves to the configured mock (not a fresh
  auto-generated child mock); add `_SensorEntityDescription` real class;
  wire all `homeassistant.components.*` and `homeassistant.helpers.*` submodule
  attributes onto parent mocks.
- `tests/conftest.py`: add `title` field to `_FakeEntry` (required by platform
  `async_setup_entry` functions that build `DeviceInfo`).

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
