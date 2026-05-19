# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

## [0.2.149] - 2026-05-19
### Tests
- `test_parse_toml_validate.py`: add `TestParseResultNamedAccess.test_store_responses_default_is_false` — pins `store_responses` default to exactly `False`, replacing the `isinstance(bool)` check that passes for either bool value

## [0.2.148] - 2026-05-19
### Tests
- `test_coordinator_retry.py`: add `TestCoordinatorRetry.test_exhausted_retries_message_exact_format` — pins the full `UpdateFailed` message after retry exhaustion to exact format, replacing three independent substring checks

## [0.2.147] - 2026-05-19
### Tests
- `test_coordinator_retry.py`: add `TestCoordinatorNonTransient.test_connection_error_message_exact_format` — pins `UpdateFailed` message to exact `"Failed to fetch {url}: ConnectError: {detail}"` format, replacing the URL substring check

## [0.2.146] - 2026-05-19
### Tests
- `test_update_entity.py`: add `TestReleaseSummary.test_update_available_exact_release_summary` — pins the update-available release_summary to the exact full sentence, replacing four separate substring/position checks that leave wording gaps

## [0.2.145] - 2026-05-19
### Tests
- `test_enrich_subentry.py`: add `TestUpstreamKeys.test_upstream_keys_exact_key_set` — exact set equality on `_upstream_keys()` result keys, catching accidental additions missed by the five-iteration `in` loop

## [0.2.144] - 2026-05-19
### Tests
- `test_select.py`: add `TestOptions.test_returns_coordinator_models_exact_list` — exact list equality for the happy-path case where current model is in coordinator list, replacing two `in` membership checks

## [0.2.143] - 2026-05-19
### Tests
- `test_coordinator_properties.py`: add `TestChatModelsProperty.test_gpt_image_filter_preserves_remaining_chat_models` — exact list equality after gpt-image filter, catching over-aggressive filtering missed by the `not in`/`in` pair

## [0.2.142] - 2026-05-19
### Tests
- `test_manifest.py`: add `test_homeassistant_min_version_exact_value` (pins to `"2024.10.0"`), `test_codeowners_exact_value` (pins to `["@elvin-li"]`), and `test_after_dependencies_exact_list` (pins to `["openai_conversation"]`) — replacing format/membership/type checks that accept incorrect values

## [0.2.141] - 2026-05-19
### Tests
- `test_manifest.py`: add `TestManifestValidity.test_name_exact_value` — pins `name` to exactly `"Codex Token Pool"`, replacing the type/truthiness check that passes for any non-empty string

## [0.2.140] - 2026-05-19
### Tests
- `test_update_entity.py`: add `TestReleaseSummary.test_up_to_date_exact_release_summary` — pins the up-to-date release_summary to exactly `"Already on the latest model from the proxy."`, replacing the substring check that passes for any message containing that phrase

## [0.2.139] - 2026-05-19
### Tests
- `test_update_entity.py`: add `TestTitle.test_title_exact_format_with_different_subentry_titles` — pins title to exact `"Proxy model ({subentry.title})"` format for parametric titles, replacing substring checks that pass for any format containing the title

## [0.2.138] - 2026-05-19
### Tests
- `test_button.py`: add `TestRefreshModelsButton.test_press_debug_log_exact_format_string` — pins the async_press debug log to exactly `"Manual /v1/models refresh requested"`, replacing the case-insensitive substring check

## [0.2.137] - 2026-05-19
### Tests
- `test_conversation_entity.py`: add `test_device_info_identifiers_exact_set` to both `TestCodexConversationEntity` and `TestCodexAITaskEntity` — exact set equality on `identifiers`, replacing the `in` check that passes with extra identifiers

## [0.2.136] - 2026-05-19
### Tests
- `test_main_flow.py`: add `TestEntryCreation.test_subentry_types_exact_set` — exact set equality on created subentry types, catching unexpected extras missed by two independent `in` checks

## [0.2.135] - 2026-05-19
### Tests
- `test_platform_setup.py`: add `TestBinarySensorSetup.test_entity_unique_id_exact_format` — pins binary sensor unique_id to exact `"<entry_id>_proxy_reachable"` format, replacing the `in` substring check that passes for any format containing the entry_id

## [0.2.134] - 2026-05-19
### Tests
- `test_platform_setup.py`: add `TestSensorSetup.test_sensor_types_exact_set` — exact set equality on sensor entity types, catching unexpected extras missed by two independent `in` checks

## [0.2.133] - 2026-05-19
### Tests
- `test_const.py`: add `TestDefaults.test_reasoning_efforts_exact_values` — exact tuple equality pins REASONING_EFFORTS to `("none", "medium", "high", "xhigh")`, catching accidental additions or renames missed by the four-`in` loop

## [0.2.132] - 2026-05-19
### Tests
- `test_const.py`: add `TestIntervals.test_coordinator_max_retries_exact_value` and `test_coordinator_retry_delays_exact_values` — exact equality pins the retry count to 3 and the delay tuple to (5, 30), replacing weak `> 0` and per-element type checks that would pass on any positive values

## [0.2.131] - 2026-05-19
### Tests
- `test_const.py`: add `TestCodexHeaders.test_openai_beta_exact_value` and `test_originator_exact_value` — exact string equality for both constants, replacing weak substring/type checks

## [0.2.130] - 2026-05-19
### Tests
- `test_coordinator.py`: add `TestChatModelFilter.test_excludes_dall_e_prefix_exact_result` and `test_excludes_image_prefix_exact_result` — exact list equality replaces vacuous `all/any` checks that pass on empty lists

## [0.2.129] - 2026-05-19
### Tests
- `test_coordinator_retry.py`: add `TestCoordinatorSuccess.test_return_dict_has_exactly_models_key` — exact set equality on `_async_update_data` return dict keys, catching accidental extra keys the `in` check would miss

## [0.2.128] - 2026-05-19
### Tests
- `test_pure_helpers.py`: add `TestParseCodexToml.test_full_config_exact_key_set` — exact set equality on parse result keys, catching accidental extra keys the per-value tests would miss

## [0.2.127] - 2026-05-19
### Tests
- `test_setup_entry.py`: add `test_hass_data_entry_contains_exactly_coordinator_key` — exact set equality on `hass.data[DOMAIN][entry_id]` keys, catching accidental additions the prior `in` check would miss

## [0.2.126] - 2026-05-19
### Tests
- `test_entity_utils.py`: add `test_identifiers_exact_set_for_subentry` and `test_identifiers_exact_set_for_entry` — exact set equality on DeviceInfo identifiers for both builders, catching accidental extra identifiers the prior `in` checks would miss

## [0.2.125] - 2026-05-19
### Tests
- `test_coordinator_properties.py`: add `test_dall_e_filter_preserves_remaining_chat_models` and `test_image_prefix_filter_preserves_remaining_chat_models` — exact list equality confirms filters are surgical

## [0.2.124] - 2026-05-19
### Tests
- `test_model_select.py`: add `TestModelSelectOptions.test_coordinator_models_exact_values_and_order` — exact list equality on options values, catching extra items or ordering changes the two prior `in` checks would miss

## [0.2.123] - 2026-05-19
### Tests
- `test_probe_proxy.py`: add `TestProbeProxySuccess.test_debug_log_model_as_format_arg` — pins model at `args[2]`, complementing the base_url pin at `args[1]` added in v0.2.99

## [0.2.122] - 2026-05-19
### Tests
- `test_subentry_flow.py`: add `TestAsyncStepReconfigure.test_update_and_abort_data_is_keyword_arg` — pins keyword calling convention for `async_update_and_abort`, replacing three OR-fallback patterns in the class

## [0.2.121] - 2026-05-19
### Tests
- `test_select.py`: add `test_update_subentry_data_passed_as_keyword` — pins `"data" in call_args.kwargs` so the keyword calling convention is enforced instead of silently accepting a positional fallback

## [0.2.120] - 2026-05-19
### Tests
- `test_coordinator_logging.py`: add `TestSuccessLogging.test_success_log_format_string_starts_with_fetched` — pins `args[0].startswith("Fetched")` replacing OR-condition check on combined call repr

## [0.2.119] - 2026-05-19
### Tests
- `test_enrich_subentry.py`: add `TestEnrichSubentryData.test_base_none_exact_key_set` — exact set equality on result keys, catching accidental additions that the prior two `in` checks would silently accept

## [0.2.118] - 2026-05-19
### Tests
- `test_coordinator_logging.py`: add `TestRetryLogging.test_retry_log_format_string_starts_with_transient_error_on_attempt` — checks `args[0]` starts with exact phrase instead of OR-condition substring search

## [0.2.117] - 2026-05-19
### Tests
- `test_diagnostics.py`: add `TestDiagnosticsSubentries.test_subentries_types_exact_set` — exact set equality on subentry types catches unexpected additions that the two prior `in` membership checks would miss

<!-- Add new changes here. Move to a versioned section on release. -->

---

## [0.2.116] – 2026-05-19

### Added (tests)

- **`tests/test_update_entity.py`** —
  `TestReleaseSummary.test_update_available_new_model_labeled_as_available`
  checks that the new model's string position comes before the old model's in the
  summary.  The existing `test_update_available` uses two `in` checks that pass
  even if the models are swapped in the message; the new test pins the order
  so `'available: <new>'` always precedes `'installed: <old>'`.

---

## [0.2.115] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator_init.py`** —
  `TestCoordinatorInit.test_headers_exact_key_set` pins the exact set of six
  header keys in `coord._headers` using set equality.  The per-header tests
  each check a single value; they pass even if extra keys are added.  This test
  catches extra or missing headers at construction time, complementing the
  request-level test added in v0.2.114.

---

## [0.2.114] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator_request.py`** —
  `TestRequestHeaders.test_exact_header_keys_sent_in_request` pins the exact set
  of 6 HTTP headers sent in the `/v1/models` request using exact set equality.
  The existing per-header tests verify individual values but pass even if extra
  headers are accidentally added; this test catches extra or missing headers in
  a single assertion.

---

## [0.2.113] – 2026-05-19

### Added (tests)

- **`tests/test_manifest.py`** —
  `TestManifestValidity.test_iot_class_is_cloud_polling` pins the exact
  `iot_class` value as `"cloud_polling"`.  The existing `test_iot_class_present`
  only checks key presence; a change to `"local_polling"` would pass that test
  while causing HA and HACS to display incorrect metadata about the integration's
  connectivity class.

---

## [0.2.112] – 2026-05-19

### Added (tests)

- **`tests/test_button.py`** —
  `TestRefreshModelsButton.test_press_debug_log_message_content` checks that
  the format string at `call_args.args[0]` contains `"refresh"` (case-insensitive).
  The existing `test_press_emits_debug_log` only asserts `assert_called_once()`;
  a refactor that changed the message to a generic `"OK"` would still pass that
  test but leave operators unable to identify manual-refresh events in HA logs.

---

## [0.2.111] – 2026-05-19

### Added (tests)

- **`tests/test_binary_sensor.py`** —
  `TestExtraStateAttributes.test_attrs_exact_keys_after_successful_poll` pins
  `set(attrs.keys()) == {"last_checked", "latest_model"}` using exact set
  equality for a healthy coordinator.  The existing
  `test_both_attributes_present_after_successful_poll` uses `in` checks that
  pass even if extra keys (e.g. `last_error: None`) leak into the attributes
  dict.

---

## [0.2.110] – 2026-05-19

### Added (tests)

- **`tests/test_diagnostics.py`** —
  `TestDiagnosticsCoordinatorInfo.test_coordinator_section_exact_keys` uses
  exact set equality to pin that the coordinator diagnostics section contains
  exactly seven keys: `last_update_success`, `last_update_success_time`,
  `chat_models_count`, `latest_chat_model`, `models`, `update_interval`, and
  `last_error`.  The existing `test_coordinator_section_present` only checked
  five keys with `in` tests; a dropped key or extra sensitive key would not be
  caught by the existing test.

---

## [0.2.109] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator.py`** —
  `TestImageModelIdPrefixes.test_contains_exactly_three_prefixes` asserts
  `set(IMAGE_MODEL_ID_PREFIXES) == {"gpt-image", "dall-e", "image-"}` using
  exact set equality.  The existing `test_required_prefixes_present` uses `in`
  checks — passes even if an extra prefix like `"gpt-"` is accidentally added,
  which would silently exclude all GPT models from `chat_models`.

---

## [0.2.108] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator_retry.py`** —
  `TestCoordinatorTransient.test_exhausted_retries_message_contains_attempt_count`
  verifies that `str(COORDINATOR_MAX_RETRIES)` appears in the `UpdateFailed`
  message after all retries are exhausted.  Existing tests only verified the URL
  and error-type portions; a refactor that hardcoded a different count or dropped
  the count entirely would still pass those tests.

---

## [0.2.107] – 2026-05-19

### Added (tests)

- **`tests/test_setup_entry.py`** —
  `TestInstallationId.test_installation_id_update_uses_keyword_data_arg`
  verifies that `async_update_entry` is called with `data` as a keyword
  argument.  The existing test uses a defensive `or` fallback that reads the
  second positional arg — dead code that would `IndexError` if the keyword path
  failed.  The new test pins the keyword-arg calling convention directly via
  `"data" in call_args.kwargs`.

---

## [0.2.106] – 2026-05-19

### Added (tests)

- **`tests/test_parse_toml_validate.py`** —
  `TestManualInput.test_http_url_exact_value_preserved` asserts
  `result.base_url == "http://localhost:8080"` using exact equality.  The
  existing `test_http_url_valid` uses `"localhost" in result.base_url` which
  passes even if the port is stripped or the scheme changed to `https`; the new
  test pins the full URL value including port.

---

## [0.2.105] – 2026-05-19

### Added (tests)

- **`tests/test_config_flow.py`** —
  `TestParseCodexToml.test_base_url_is_first_not_second_provider` uses exact
  equality to assert that `parse_codex_toml` returns the first provider's URL.
  The existing `test_base_url_takes_first_provider` uses `in (first, second)` —
  it passes even if the second provider's URL is returned, allowing a silent
  dict-iteration-order regression to go undetected.

---

## [0.2.104] – 2026-05-19

### Added (tests)

- **`tests/test_const.py`** —
  `TestSubentryTypes.test_llm_bearing_contains_exactly_both_types` asserts
  `set(LLM_BEARING_SUBENTRY_TYPES) == {conversation, ai_task_data}` using
  exact set equality.  The existing `test_llm_bearing_contains_both_types`
  uses `in` checks that pass even if an extra type is accidentally added;
  an extra entry would cause every subentry of that type to generate spurious
  model-select and update entities in the device registry.

---

## [0.2.103] – 2026-05-19

### Added (tests)

- **`tests/test_main_flow.py`** —
  `TestUserStep.test_entry_title_exact_format` asserts the full entry title is
  `"Codex 号池 (proxy.example.com)"` using exact equality.  The existing
  `test_entry_title_includes_host` uses a substring check that passes even if
  the format changes; the new test pins the `"Codex 号池 (<netloc>)"` pattern
  so renames or format changes are caught immediately.

---

## [0.2.102] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator_logging.py`** —
  `TestSuccessLogging.test_success_log_total_count_arg_is_len_models` pins
  `args[1] == 2` (total model count) for an image-only payload.  Existing tests
  only verified `args[3]` (chat-capable count); a refactor that passed
  `chat_count` twice (`debug(fmt, 0, url, 0)`) instead of `(len(models), url,
  chat_count)` would silently pass all prior tests but is caught here.

---

## [0.2.101] – 2026-05-19

### Added (tests)

- **`tests/test_update_entity.py`** —
  `TestAsyncInstall.test_install_log_model_positions_in_format_args` checks
  that the model-install info log passes `(target, title, installed_version)`
  as positional format args at indices 1, 2, and 3.  The existing string-based
  log tests would pass even if the args were reordered; the new test pins each
  position to match the format string
  `"Installing model '%s' on subentry '%s' (was '%s'); reloading entry"`.

---

## [0.2.100] – 2026-05-19

### Added (tests)

- **`tests/test_select.py`** —
  `TestSelectAsync.test_info_log_model_positions_in_format_args` checks that
  the model-change info log passes `(title, old_model, new_model)` as positional
  format args at indices 1, 2, and 3 respectively.  The existing
  `test_info_logged_on_model_change` uses `str(call_args)` which would pass
  even if the old and new model args were accidentally swapped; the new test
  pins the exact position of each value.

---

## [0.2.99] – 2026-05-19

### Added (tests)

- **`tests/test_probe_proxy.py`** —
  `TestProbeProxySuccess.test_debug_log_base_url_as_format_arg` checks that
  `base_url` is passed as a positional format argument at index 1 of the probe
  debug log call.  The existing `test_debug_log_emitted_at_probe_start` uses an
  OR condition (`_BASE_URL in logged or "proxy.example.com" in logged`) that
  passes even if only the hostname without scheme appears; the new test pins
  `call_args.args[1] == _BASE_URL` directly.

---

## [0.2.98] – 2026-05-19

### Added (tests)

- **`tests/test_init.py`** —
  `TestBuildCodexHeaders.test_returns_exactly_required_keys` uses exact set
  equality (`==`) instead of `issubset` to assert that `_build_codex_headers`
  returns *exactly* the four required headers and no extras.  The existing
  `test_all_required_keys_present` passes even if an extra header (e.g.
  `Authorization`) is accidentally added; an extra `Authorization` would
  silently override the api_key-derived Bearer token and break all LLM requests
  with HTTP 401.

---

## [0.2.97] – 2026-05-19

### Added (tests)

- **`tests/test_platform_setup.py`** —
  `TestBinarySensorSetup.test_binary_sensor_coordinator_reference` and
  `TestSensorSetup.test_sensor_coordinator_reference` verify that both
  entry-level coordinator entities reference `mock_coordinator` after setup.
  Parity with `TestButtonSetup.test_button_coordinator_reference` which already
  covered the button; the binary sensor and sensor classes were missing the
  equivalent check.

---

## [0.2.96] – 2026-05-19

### Added (tests)

- **`tests/test_pure_helpers.py`** — `TestParseCodexToml.test_store_responses_absent_when_key_missing`
  verifies that `store_responses` is absent from `parse_codex_toml`'s return
  dict when `disable_response_storage` is not in the TOML.  An unconditional
  `store_responses=True` in the output would silently override the caller's
  default whenever a TOML snippet lacked the key.

---

## [0.2.95] – 2026-05-19

### Added (tests)

- **`tests/test_enrich_subentry.py`** — `TestEnrichSubentryData.test_base_dict_not_mutated`
  verifies that the caller's `base` dict is not mutated when
  `_enrich_subentry_data` writes new keys.  Callers pass a live subentry's
  `.data` dict as `base` during reconfigure; a refactor that removed the
  `dict(base)` copy would silently persist changes back into the caller's dict.

---

## [0.2.94] – 2026-05-19

### Added (tests)

- **`tests/test_migrate_entry.py`** — `TestAsyncMigrateEntry.test_debug_log_version_passed_as_format_arg`
  checks that the entry version is passed as `call_args.args[1] == 42` (a
  dynamic positional format argument) rather than being hardcoded in the format
  string.  The existing `test_emits_debug_log_with_version` uses an OR: `"42"
  in str(call_args) or args[1] == 42` — the first branch passes even if 42 is
  in the format string literal, not a dynamic arg.

---

## [0.2.93] – 2026-05-19

### Added (tests)

- **`tests/test_model_select.py`** — `TestModelSelectOptions.test_current_model_label_equals_id_when_prepended`
  verifies that when the current model is prepended (not in the coordinator
  list), its dropdown `label` equals the model id string.  The existing
  `test_current_model_prepended_if_not_in_coordinator` only checks `value`;
  a refactor producing a blank label would be invisible to that test but
  obvious in the UI dropdown.

---

## [0.2.92] – 2026-05-19

### Added (tests)

- **`tests/test_conversation_entity.py`** — `TestCodexConversationEntity.test_device_info_entry_type_is_service`
  and `TestCodexAITaskEntity.test_device_info_entry_type_is_service` verify
  that both entity classes set `entry_type = DeviceEntryType.SERVICE` in their
  `_attr_device_info`.  `build_codex_device_info` already has this test at the
  builder level (v0.2.87); the entity-level tests catch a hypothetical refactor
  that swaps in a different builder that omits `entry_type`, independently for
  each entity class.

---

## [0.2.91] – 2026-05-19

### Added (tests)

- **`tests/test_setup_entry.py`** — `TestCoordinatorFailurePath.test_warning_log_includes_exception_message`
  verifies that the exception message (`"proxy unreachable"`) appears in the
  startup warning call.  `test_warning_log_prefix_is_initial_model_refresh_failed`
  (v0.2.82) covers the format prefix; `test_warning_logged_when_coordinator_refresh_fails`
  uses an OR condition covering either prefix or error text.  This test
  directly checks the exception-text half so a refactor that drops the `%s`
  argument (logging only the static prefix) is caught here.

---

## [0.2.90] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator_logging.py`** — `TestSuccessLogging.test_success_log_chat_count_when_all_are_chat_models`
  directly checks `call_args[3] == 2` when all fetched models are chat-capable.
  The companion `test_success_log_shows_zero_for_image_only` already pins
  `call_args[3] == 0` for image-only payloads; the only "positive" test was
  `test_debug_logged_on_success` which uses an OR condition (`"2" in str OR
  "model" in str`) that can pass even if the count arg is wrong.  Together
  the two positional-arg tests cover both ends of the chat-count range.

---

## [0.2.89] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator_retry.py`** — `TestCoordinatorTransient.test_exhausted_retries_message_contains_error_type`
  verifies that the `UpdateFailed` message raised after all retries are exhausted
  includes the exception type name (`"TimeoutException"`).  The existing
  `test_exhausted_retries_message_contains_url` only checks the URL portion;
  a refactor that dropped the `type(last_err).__name__` interpolation would
  produce an opaque `(last error: timed out)` with no type context yet pass
  the URL-only test.  Mirrors `test_retry_log_includes_error_type_for_timeout`
  which covers the same invariant for the intermediate retry debug log.

---

## [0.2.88] – 2026-05-19

### Added (tests)

- **`tests/test_binary_sensor.py`** — `TestMetadata.test_unique_id_exact_format_via_constructor`
  builds `CodexProxyReachableSensor` via its real `__init__` and asserts
  `_attr_unique_id == "pin-entry-bs-42_proxy_reachable"`.  The existing
  `test_unique_id_has_suffix` uses the `_make_sensor` helper which manually
  assigns the attribute — bypassing the constructor — so a refactor that changes
  the format in `__init__` would not be caught.  Matches the constructor-based
  exact-format pattern applied to button, sensor, select, and update entities.

---

## [0.2.87] – 2026-05-19

### Added (tests)

- **`tests/test_entity_utils.py`** — `TestBuildCodexDeviceInfo.test_entry_type_is_service`
  and `TestBuildCodexEntryDeviceInfo.test_entry_type_is_service` pin that both
  device-info builders set `entry_type=DeviceEntryType.SERVICE`.  Without this field
  HA shows an area picker for a cloud proxy device, which is meaningless.  Neither
  builder had an entry_type test before; a refactor removing the field would have
  passed all existing tests.

---

## [0.2.86] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator_logging.py`** — `TestRetryLogging.test_retry_log_includes_error_type_for_timeout`
  pins that `TimeoutException` appears in the retry debug log when the failure
  is a network timeout.  Companion to v0.2.85's `test_retry_log_includes_error_type_for_5xx`
  — together they verify the `(%s)` error-type placeholder is filled for both transient
  failure modes so operators can distinguish timeouts from HTTP 5xx in HA logs.

---

## [0.2.85] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator_logging.py`** — `TestRetryLogging.test_retry_log_includes_error_type_for_5xx`
  pins that the retry debug log includes `HTTPStatusError` as the exception type name.
  The retry format is `'Transient error on attempt N/M (ExcType) — retrying in Xs'`;
  the existing test only checks `'Transient'` OR `'attempt'` and neither verifies the
  `(%s)` placeholder is filled with the error class.  A refactor dropping the type arg
  would silently remove the operator-visible error classification.

---

## [0.2.84] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator_init.py`** — `TestCoordinatorInit.test_last_update_success_time_initially_none`
  guards the binary sensor's "unknown before first poll" invariant.
  `CodexProxyReachableSensor.is_on` returns `None` (unknown) until
  `last_update_success_time` is set; if the coordinator initialised with a truthy
  value the sensor would prematurely report 'connected' before any poll completed.
  Companion to the existing `test_last_exception_initially_none`.

---

## [0.2.83] – 2026-05-19

### Added (tests)

- **`tests/test_conversation_entity.py`** — `TestCodexAITaskEntity.test_device_info_model_uses_chat_model`
  fills the parity gap with `TestCodexConversationEntity`.  Both entities call
  `build_codex_device_info(subentry, UPSTREAM_CONF_CHAT_MODEL)` so the
  `device_info["model"]` field should reflect the subentry's chat_model; without
  this test a refactor passing the wrong key for the AI Task entity would be caught
  for Conversation but silently missed for AI Task.

---

## [0.2.82] – 2026-05-19

### Added (tests)

- **`tests/test_setup_entry.py`** — `TestCoordinatorFailurePath.test_warning_log_prefix_is_initial_model_refresh_failed`
  pins that the startup-failure warning always begins with
  `"Initial model refresh failed"`.  The existing
  `test_warning_logged_when_coordinator_refresh_fails` uses an OR condition
  (error text OR format prefix); without this companion test, renaming the
  format string would silently pass because the exception text appears in the
  call_args repr regardless.

---

## [0.2.81] – 2026-05-19

### Added (tests)

- **`tests/test_main_flow.py`** — `TestEntryCreation.test_probe_receives_stripped_api_key`
  verifies that `_probe_proxy` is called with the whitespace-stripped api_key, not the
  raw padded value the user submitted.  The existing
  `test_api_key_whitespace_stripped_in_flow` only checks the STORED key is stripped;
  a refactor that moves `strip()` to after the probe call would pass both old tests
  while silently sending padded credentials to the proxy.
- **`tests/test_reconfigure_flow.py`** — `TestReconfigurePreservesInstallationId.test_probe_receives_stripped_api_key_in_reconfigure`
  — same guard for the reconfigure path.

---

## [0.2.80] – 2026-05-19

### Added (tests)

- **`tests/test_select.py`** — `TestAsyncSelectOption.test_info_log_includes_subentry_title`
  pins that `async_select_option` includes the subentry title in its info log.
  The existing `test_info_logged_on_model_change` already checks both old and new
  model IDs; without this test a refactor that dropped the title arg would go
  undetected while those checks still passed. Mirrors the gap fixed for the update
  entity in v0.2.79 (`test_install_log_includes_subentry_title`).

---

## [0.2.79] – 2026-05-19

### Added (tests)

- **`tests/test_update_entity.py`** — two new `TestAsyncInstall` tests pinning
  the install info log format:
  - `test_install_log_includes_old_model` — the old model name (`"was …"`) must
    appear alongside the new model in the install log.  The existing
    `test_install_logs_on_change` only checked the new version; dropping the
    third format arg (installed_version) from the log call would have silently
    removed operator context. Mirrors the pattern from
    `test_select.py::test_info_logged_on_model_change` which already checks
    both old and new model.
  - `test_install_log_includes_subentry_title` — the subentry title must appear
    in the install log so operators with multiple subentries (conversation +
    ai_task) can identify which agent's model was upgraded. Without the title,
    simultaneous upgrades produce identical log lines with no distinguishing
    information.

---

## [0.2.78] – 2026-05-19

### Added (tests)

- **`tests/test_subentry_flow.py`** — two new tests verifying that the
  user-selected model is stored correctly in the subentry data:
  - `TestAsyncStepUser.test_chat_model_stored_in_entry_data` — the `chat_model`
    key from the submitted form must appear in the created entry data.
    Service tier, LLM API, and title were already pinned; the *primary* user-
    visible outcome (model stored) was not. A refactor dropping the model key
    from enrichment would have passed all existing tests silently.
  - `TestAsyncStepReconfigure.test_chat_model_updated_after_reconfigure` — the
    reconfigured model must overwrite the old value. Complements the existing
    `test_reconfigure_preserves_existing_data_keys` test (which verifies that
    *non-form* fields survive), by verifying that the *changed* primary field
    is actually updated.

---

## [0.2.77] – 2026-05-19

### Added (tests)

- **`tests/test_main_flow.py`** — two new `TestEntryCreation` tests mirroring the
  pattern from v0.2.76's reconfigure additions:
  - `test_probe_called_with_user_credentials` — asserts `_probe_proxy` receives
    the api_key and base_url from the submitted form, not hardcoded or default
    values. Guards the same class of regression: wrong credentials probed, right
    ones stored, runtime failure on first API call.
  - `test_unique_id_set_to_base_url` — asserts `async_set_unique_id` is called
    with the base_url so HA can detect duplicate entries pointing at the same
    proxy. Without this call a user could add the same proxy twice without any
    warning and produce duplicate entities in every subentry.

---

## [0.2.76] – 2026-05-19

### Added (tests)

- **`tests/test_reconfigure_flow.py`** — two new `TestReconfigurePreservesInstallationId`
  tests that verify the probe and unique_id arguments during the reconfigure success path:
  - `test_probe_called_with_new_credentials` — asserts `_probe_proxy` receives the
    new api_key and new base_url (not the stale entry values). A regression where old
    credentials were used for probing would accept a stale-but-still-valid token while
    storing the new (potentially invalid) one, producing a false success.
  - `test_unique_id_set_to_new_base_url` — asserts `async_set_unique_id` is called
    with the new base_url so HA can detect and prevent duplicate entries pointing at
    the same proxy URL. Without this call, two entries for the same proxy coexist
    silently and create duplicate entities in every subentry.

---

## [0.2.75] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator_logging.py`** — two new `TestSuccessLogging` tests:
  - `test_success_log_includes_proxy_url` — the "Fetched … models" debug message
    must include `self._url` so operators with multiple Codex entries can identify
    which proxy's fetch just succeeded from a single log line. The existing
    `test_debug_logged_on_success` only checked for the model count; this test
    pins that the URL is also present as the second positional format argument.
  - `test_coordinator_logs_never_leak_api_key` — security regression guard
    asserting the Authorization header value (`Bearer sk-…`) never appears in
    any log call emitted by `_async_update_data`. The current code does not log
    headers, but this test catches a future refactor that adds diagnostic
    header-dump logging before it reaches production. Matches the pattern from
    `test_probe_proxy.py::test_debug_log_does_not_leak_api_key` (v0.2.71).

---

## [0.2.74] – 2026-05-19

### Added (tests)

- **`tests/test_sensor.py`** — added `test_unique_id_exact_format` to both
  `TestChatModelCountSensor` and `TestLastRefreshSensor`:
  - `TestChatModelCountSensor.test_unique_id_exact_format` — pins
    `"{entry_id}_chat_model_count"` by calling the real `__init__`.
  - `TestLastRefreshSensor.test_unique_id_exact_format` — pins
    `"{entry_id}_last_model_refresh"` by calling the real `__init__`.

  Both sensors previously had only substring checks (`entry_id in unique_id`)
  via the `_make_count_sensor` / `_make_refresh_sensor` helpers, which bypass
  the constructor.  Exact-format pinning matches the pattern introduced in
  v0.2.73 for button, select, and update entities, and guards against
  EntityDescription key renames that would silently orphan existing sensor
  entities in the HA entity registry.

---

## [0.2.73] – 2026-05-19

### Added (tests)

- **`tests/test_button.py`** — `TestRefreshModelsButton.test_unique_id_exact_format`:
  pins the full unique_id format `"{entry_id}_refresh_models"` by calling the real
  `__init__`, not the helper that manually assigns the attribute. The existing
  substring check only verifies the entry_id is present; this test catches a suffix
  change that would silently create a duplicate entity in the HA entity registry.
- **`tests/test_select.py`** — `TestDeviceInfo.test_unique_id_exact_format`:
  pins `"{subentry_id}_model_select"`. No unique_id test existed at all for the
  select entity before this change.
- **`tests/test_update_entity.py`** — `TestDeviceInfo.test_unique_id_exact_format`:
  pins `"{subentry_id}_model_update"`. No unique_id test existed at all for the
  update entity before this change.

  All three tests exercise the real entity constructor (not test helpers) so any
  change to the `__init__` assignment is caught directly. Unique_id format changes
  are silent registry-breaking bugs: HA creates a new entity and orphans the old one
  without warning.

---

## [0.2.72] – 2026-05-19

### Added (tests)

- **`tests/test_button.py`**, **`tests/test_select.py`**, **`tests/test_binary_sensor.py`**,
  **`tests/test_update_entity.py`** — added `test_translation_key_in_strings_json` to each
  file's `TestClassAttributes` class. These bridge tests verify that each entity's
  `_attr_translation_key` class attribute actually maps to an existing key in
  `strings.json entity.<platform>`. Without this check, a rename in Python without a
  matching strings.json update would cause HA to render the raw key string in the UI
  (e.g., `"active_model"` instead of `"Active Model"`) — a silent regression that
  `test_translations.py`'s file-consistency checks cannot catch because they only
  compare JSON files to each other, not Python code to JSON. Closes the Python→JSON
  bridge gap that `test_sensor.py::test_translation_keys_match_strings_json` already
  covered for sensors but was missing for button, select, binary_sensor, and update
  platforms.

---

## [0.2.71] – 2026-05-19

### Added (tests)

- **`tests/test_probe_proxy.py`** — two new `TestProbeProxySuccess` tests:
  - `test_debug_log_contains_model` — the probe debug message must include the
    model being tested so operators can diagnose `unknown_model` errors from the
    log without re-running setup. Completes the format-string pin started by the
    existing URL-presence test.
  - `test_debug_log_does_not_leak_api_key` — security guard asserting the API key
    never appears in any log call emitted by `_probe_proxy`. HA log files are
    routinely shared in bug reports; this test catches any future refactor that
    accidentally logs the credential.

---

## [0.2.70] – 2026-05-19

### Added (tests)

- **`tests/test_init.py`** — four new `TestPlatforms` tests completing explicit
  per-platform registration coverage:
  - `test_button_registered` — `Platform.BUTTON` (Refresh Models button)
  - `test_ai_task_registered` — `Platform.AI_TASK` (AI Task entity)
  - `test_select_registered` — `Platform.SELECT` (model-select dropdown)
  - `test_update_registered` — `Platform.UPDATE` (model-update entity)

  Previously only `BINARY_SENSOR`, `CONVERSATION`, and `SENSOR` had explicit
  registration tests; the other 4 could have been silently removed from `PLATFORMS`
  without any test failing. 528 tests passing.

---

## [0.2.69] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator_init.py`** — `test_name_format_is_domain_models_entry_id`:
  pins the exact coordinator name format `"{DOMAIN}_models_{entry_id}"`.
  The previous `test_name_contains_entry_id` only verified the entry_id appeared
  anywhere in the name; the new test prevents a refactor that drops the domain prefix
  or changes the separator from silently making coordinator log lines unidentifiable
  when multiple Codex entries are configured in HA.

---

## [0.2.68] – 2026-05-19

### Changed / Added (tests)

- **`tests/test_entity_utils.py`**:
  - `TestIntegrationVersion.test_is_public_name` — replaced an always-true tautology
    (`assert x is not None or x is None`) with `assert INTEGRATION_VERSION is not None`,
    adding a meaningful failure message that explains what a `None` value means for the
    HA device card.
  - `TestBuildCodexDeviceInfo.test_sw_version_matches_manifest` — new test that pins
    `sw_version` against `manifest.json` for subentry-level device info, closing the parity
    gap with `TestBuildCodexEntryDeviceInfo.test_sw_version_matches_manifest` that already
    did this for entry-level device info.

---

## [0.2.67] – 2026-05-19

### Changed (tests)

- **`tests/test_binary_sensor.py`** — strengthened two `TestMetadata` tests from
  `hasattr`-only guards to exact enum-value assertions, matching the stricter pattern
  already used in `test_button.py` and `test_sensor.py`:
  - `test_device_class_is_connectivity` now asserts
    `_attr_device_class is BinarySensorDeviceClass.CONNECTIVITY` (was: `hasattr` check).
  - `test_entity_category_is_diagnostic` now asserts
    `_attr_entity_category is EntityCategory.DIAGNOSTIC` (was: `hasattr` check).
  Both tests previously passed for any non-None value; they now catch an accidental
  enum change that would cause HA to render the entity in the wrong section or with
  the wrong device-class icon.

---

## [0.2.66] – 2026-05-19

### Added (tests)

- **`tests/test_coordinator_retry.py`** — two new error-message contract tests:
  - `TestCoordinatorNonTransient.test_connection_error_message_contains_url` — verifies
    that `UpdateFailed` raised on a non-transient `ConnectError` includes the proxy URL
    in its message, so operators with multiple Codex entries can identify the failing
    endpoint from a single HA log line without cross-referencing entry IDs.
  - `TestCoordinatorRetry.test_exhausted_retries_message_contains_url` — same URL
    invariant for the exhausted-retries path; together the two tests guard both
    `UpdateFailed` raise sites in `_async_update_data` against silent message regression.

---

## [0.2.65] – 2026-05-19

### Added (tests)

- **`tests/test_const.py`** — three new constant-type contract tests:
  - `test_reasoning_efforts_is_tuple` — verifies `REASONING_EFFORTS` is `tuple`, not
    `list`; pins immutability intent and catches accidental conversion to mutable list.
  - `test_coordinator_retry_delays_is_tuple` — same guarantee for `COORDINATOR_RETRY_DELAYS`;
    the coordinator indexes it directly, so mutability would be a silent hazard.
  - `test_coordinator_retry_delays_all_positive_ints` — asserts every delay is a
    positive `int`, preventing `asyncio.sleep` from receiving a no-op or type-error
    argument if a future edit introduces a zero or float value.

---

## [0.2.64] – 2026-05-19

### Added (tests)

- **`tests/test_sensor.py`** — three new tests in `TestEntityDescriptions` that pin
  previously untested `SensorEntityDescription` fields:
  - `test_chat_model_count_entity_category_is_diagnostic` — verifies `_CHAT_MODEL_COUNT`
    belongs to `EntityCategory.DIAGNOSTIC` so it lands in the Diagnostic section of HA's
    device card rather than the primary card.
  - `test_last_refresh_entity_category_is_diagnostic` — same guarantee for `_LAST_REFRESH`.
  - `test_chat_model_count_icon` — pins `icon == "mdi:format-list-numbered"` so a future
    icon rename doesn't silently break the dashboard card visual identity.

---

## [0.2.63] – 2026-05-19

### Added (tests)

- **`tests/test_setup_entry.py`** — `test_warning_logged_when_coordinator_refresh_fails`
  added to `TestCoordinatorFailurePath`: patches `custom_components.codex_proxy._LOGGER`
  and asserts that `_LOGGER.warning` is called exactly once, carrying the failure reason,
  when `async_setup_entry`'s first-refresh catches an `UpdateFailed` exception.  Documents
  the operator-facing invariant that a failed startup refresh surfaces a warning in HA
  logs (useful for diagnosing transient proxy issues without enabling full DEBUG logging).

---

## [0.2.62] – 2026-05-19

### Added (tests)

- **`tests/test_update_entity.py`** — three additional `TestReleaseSummary` tests that
  pin user-visible strings in `CodexModelUpdate.release_summary`:
  - `test_no_coordinator_data_mentions_refresh_button` — verifies the summary includes
    "Refresh Models" when the model list hasn't loaded yet, guarding the v0.2.58 UX
    improvement that replaced opaque developer-speak with a named UI button.
  - `test_up_to_date_says_already_on_latest_model` — pins the "Already on the latest
    model" phrase so a future wording change is caught immediately.
  - `test_update_available_says_click_install` — verifies the actionable call-to-action
    "Click Install" appears in the update-available summary.

---

## [0.2.61] – 2026-05-19

### Added (tests)

- **`tests/test_migrate_entry.py`** — `test_emits_debug_log_with_version` added to
  `TestAsyncMigrateEntry`: patches `custom_components.codex_proxy._LOGGER` and
  asserts that `_LOGGER.debug` is called exactly once with the entry version during
  `async_migrate_entry`.  Documents the operator-facing invariant that the migration
  code path emits a debug log (useful for diagnosing startup issues) and catches any
  future refactor that silently drops or renames the log call.

---

## [0.2.60] – 2026-05-19

### Added (tests)

- **`tests/test_setup_unload.py`** — two new tests for `async_unload_entry`:
  - `test_unload_returns_false_when_platforms_fail` — verifies that when
    ``async_unload_platforms`` returns ``False``, ``async_unload_entry``
    propagates that ``False`` so HA keeps the entry in its registry.  Without
    this contract test, a future refactor that accidentally returned ``True``
    unconditionally would be silent.
  - `test_unload_safe_when_entry_absent_from_hass_data` — verifies that a
    double-unload race (entry already removed from ``hass.data[DOMAIN]``) does
    not raise ``KeyError``.  The implementation uses ``.pop(key, None)`` which
    is safe, but the test documents the invariant and catches any accidental
    regression to a direct ``del`` or ``[key]`` access.

---

## [0.2.59] – 2026-05-19

### Fixed (tests)

- **`tests/test_binary_sensor.py`** — renamed misleading test
  ``test_none_when_only_exception_and_no_timestamp_or_model`` to
  ``test_last_error_only_when_no_timestamp_or_model``.  The old name contained
  "none_when" but the test body asserted the result was **non-None** (because
  ``last_exception`` alone makes the attributes dict non-empty and
  ``extra_state_attributes`` returns it rather than ``None``).  This
  contradiction would cause confusion when reading a future test failure.
- Updated ``test_none_when_both_time_and_model_are_none`` docstring to
  explicitly state that all three optional attributes — including
  ``last_exception=None`` — must be absent for ``extra_state_attributes`` to
  return ``None``.  The previous docstring only mentioned the timestamp and
  model, omitting the requirement that ``last_exception`` is also ``None``.
- Strengthened the ``test_last_error_only_when_no_timestamp_or_model``
  assertion from checking ``attrs is not None`` + ``attrs["last_error"]``
  separately to ``attrs == {"last_error": "never polled"}`` — verifying the
  dict contains *exactly* the expected key and value, not just that the key is
  present.

---

## [0.2.58] – 2026-05-19

### Fixed

- **`tests/conftest.py`** — `mock_coordinator` fixture now explicitly sets
  ``coord.last_exception = None``.  Previously this attribute was omitted,
  causing ``MagicMock`` to auto-generate a truthy child mock for it.  Any
  future test that builds a ``CodexProxyReachableSensor`` using this fixture
  and calls ``extra_state_attributes`` would have seen a spurious ``last_error``
  key (the binary-sensor surfaces it when ``last_exception is not None``).

### Changed

- **`update.py`** — `release_summary` for the "model list not yet available"
  case now reads "use the Refresh Models button to force an immediate check"
  instead of the opaque "trigger manually via update_entity".  This matches
  the actual button entity exposed by the integration and is actionable for
  end-users who encounter the message in HA's update card.

---

## [0.2.57] – 2026-05-19

### Changed

- **`binary_sensor.py`** — module docstring and `extra_state_attributes`
  docstring updated to accurately document all three attributes
  (``last_checked``, ``latest_model``, ``last_error``) instead of only
  ``last_checked``.  The previous wording was written before
  ``latest_model`` (v0.2.x) and ``last_error`` (v0.2.55) were added.
- **`tests/ha_stubs.py`** — `_DataUpdateCoordinator.__init__` now initialises
  ``self.last_exception = None``, matching the attribute HA Core's real
  ``DataUpdateCoordinator`` exposes.  Without this, test code that creates a
  coordinator via ``__init__`` (instead of bypassing it with
  ``object.__new__``) would raise ``AttributeError`` when accessing
  ``coord.last_exception`` — the attribute accessed by ``binary_sensor.py``
  and ``diagnostics.py``.

### Changed (tests)

- `test_coordinator_init.py` — new test ``test_last_exception_initially_none``
  verifies the stub initialises ``last_exception`` to ``None``, documenting
  the invariant and catching any future regression where the stub drifts from
  the real HA class.

---

## [0.2.56] – 2026-05-19

### Changed

- **`coordinator.py`** — `chat_models` property now adds a defensive
  `isinstance(models, list)` guard before the list comprehension.
  `_async_update_data` always writes a proper list, but without the guard a
  malformed payload that stored a `dict` or `str` in `data["models"]` would
  silently iterate over dict keys / string characters and then crash with
  `AttributeError` / `TypeError` on `m["id"]`.  The new guard degrades
  gracefully to `[]` in that case.

### Changed (tests)

- `test_coordinator_properties.py` — 2 new tests added to
  ``TestChatModelsProperty``:
  ``test_chat_models_returns_empty_when_models_value_is_dict`` and
  ``test_chat_models_returns_empty_when_models_value_is_string``.
  Both verify the new defensive guard introduced above.
- `test_translations.py` — ``test_binary_sensor_state_attributes_documented``
  now also asserts that ``last_error`` is documented in all three translation
  files (``strings.json``, ``en.json``, ``zh-Hans.json``).  The key was added
  in v0.2.55 but the translation consistency test wasn't updated to reflect it,
  so a future regression removing it from one file would have gone undetected.

---

## [0.2.55] – 2026-05-19

### Added

- **`binary_sensor.py`** — ``extra_state_attributes`` now includes a
  ``last_error`` key when the most recent coordinator poll failed.  The value
  is ``str(coordinator.last_exception)`` — the error message without a stack
  trace.  This makes proxy failure reasons accessible from HA automations and
  template sensors (e.g.
  ``{{ state_attr('binary_sensor.proxy_reachable', 'last_error') }}``) without
  requiring a full diagnostics download.  The attribute is absent when the last
  poll succeeded.
- **Translations** — ``last_error`` state-attribute name added to
  ``strings.json``, ``translations/en.json`` ("Last error"), and
  ``translations/zh-Hans.json`` ("上次错误").

### Added (tests)

- `test_binary_sensor.py` — 4 new tests in ``TestExtraStateAttributes``:
  ``test_last_error_absent_when_no_exception``,
  ``test_last_error_present_when_exception_set``,
  ``test_last_error_is_string``,
  ``test_none_when_only_exception_and_no_timestamp_or_model``.

---

## [0.2.54] – 2026-05-19

### Changed (tests)

- `test_parse_toml_validate.py` — all test methods in ``TestManualInput``,
  ``TestTomlInput``, and ``TestApiKeyStripping`` now use named field access
  (``result.api_key``, ``result.errors``, etc.) instead of positional
  unpacking with ``_`` placeholders.  The backward-compat
  ``test_positional_unpacking_still_works`` test in
  ``TestParseResultNamedAccess`` is kept as the one explicit guard for that
  invariant.  The refactoring makes the test file consistent with the
  ``config_flow.py`` production-code changes landed in v0.2.53.

---

## [0.2.53] – 2026-05-19

### Changed

- **`config_flow.py`** — ``async_step_user`` and ``async_step_reconfigure`` now
  use named field access from the ``_ParseResult`` NamedTuple instead of
  positional unpacking.  The validation-errors variable is renamed
  ``parsed.errors`` and the probe-errors variable is renamed ``probe_errors``
  to make the two distinct error paths visually distinct.  In
  ``async_step_reconfigure`` the ``_, _`` placeholders for the unused
  ``reasoning_effort`` / ``store_responses`` fields are eliminated entirely —
  the comment explains they are not needed in this step.

### Added (tests)

- `test_pure_helpers.py` — ``test_non_dict_model_providers_value_ignored``:
  a ``model_providers`` key that contains a bare string (not a TOML table)
  must not crash ``parse_codex_toml`` — the ``isinstance(providers, dict)``
  guard should prevent AttributeError and omit ``base_url`` from the result.

---

## [0.2.52] – 2026-05-19

### Fixed

- **`coordinator.py`** — ``display_name`` is now stripped of surrounding
  whitespace before the falsy-fallback check:
  ``str((m.get("display_name") or "").strip() or mid)``.  Previously a proxy
  returning ``"  GPT 5.5  "`` would display with leading/trailing spaces in
  the model dropdown; returning only whitespace (``"   "``) would not fall back
  to the model id.  Both cases are now handled correctly.

### Changed

- **`coordinator.py`** — The retry delay lookup is simplified from
  ``COORDINATOR_RETRY_DELAYS[min(attempt, len-1)]`` to the direct
  ``COORDINATOR_RETRY_DELAYS[attempt]``.  The module-level assertion in
  ``const.py`` already guarantees the two constants are in sync, making the
  defensive ``min()`` a no-op.  Updated the comment in ``const.py`` to reflect
  this contract.

### Added (tests)

- `test_coordinator.py` — ``test_whitespace_only_display_name_falls_back_to_id``:
  a ``display_name`` of ``"   "`` (spaces only) must produce the model id as
  the label.
- `test_coordinator.py` — ``test_display_name_surrounding_whitespace_stripped``:
  ``"  GPT 5.5 Preview  "`` must be stored as ``"GPT 5.5 Preview"``.
- `test_reconfigure_flow.py` — ``test_api_key_whitespace_stripped_in_reconfigure``:
  end-to-end guard that a padded api_key is stripped before being passed to
  ``async_update_reload_and_abort`` (mirrors the main-flow guard added in
  v0.2.50).

---

## [0.2.51] – 2026-05-19

### Changed

- **`select.py`** — ``CodexModelSelectEntity.__init__`` now calls
  ``build_codex_device_info(subentry, UPSTREAM_CONF_CHAT_MODEL)`` instead of a
  bare ``dr.DeviceInfo(identifiers=...)`` stub.  The device card in HA now shows
  the correct name, manufacturer, model, and integration version for model-select
  entities, consistent with conversation and AI-task entities.  The redundant
  ``from homeassistant.helpers import device_registry as dr`` import is removed.
- **`update.py`** — same fix as ``select.py``: ``CodexModelUpdate.__init__``
  now uses ``build_codex_device_info`` so the update entity's device card is
  fully populated.  Dead ``dr`` import removed.

### Added (tests)

- `test_select.py` — ``TestDeviceInfo``: 3 tests verifying that the select
  entity's ``_attr_device_info`` contains ``manufacturer``, ``name`` (matching
  the subentry title), and ``sw_version`` after construction.
- `test_update_entity.py` — ``TestDeviceInfo``: same 3 tests for the update
  entity.

---

## [0.2.50] – 2026-05-19

### Added (tests)

- `test_probe_proxy.py` — ``test_debug_log_emitted_at_probe_start``: verifies
  that ``_probe_proxy`` emits exactly one ``DEBUG`` log referencing the proxy
  URL before attempting the API call.  Ensures the observability improvement
  from v0.2.49 has regression coverage.
- `test_main_flow.py` — ``test_api_key_whitespace_stripped_in_flow``: end-to-end
  guard for the v0.2.46 whitespace-stripping fix — confirms that a padded API
  key (``"  sk-test  "``) is stored as ``"sk-test"`` in the config entry.

---

## [0.2.49] – 2026-05-19

### Changed

- **`config_flow.py`** — ``CodexConfigFlow`` class docstring expanded to
  describe the three-flow architecture and the purpose of the reconfigure step.
  ``async_step_user`` now has a detailed two-phase docstring (show-form /
  process-submit) explaining the TOML parse, probe, and subentry-creation steps.
- **`config_flow.py`** — ``_probe_proxy`` now emits a ``DEBUG``-level log
  message at the start of the probe (``"Probing proxy at <url> with model <id>"``).
  This makes it easy to confirm what URL is being tested during setup without
  trawling the entire HA log.

### Added (tests)

- `test_model_select.py` — ``test_empty_string_display_name_falls_back_to_id``:
  an empty-string ``display_name`` is falsy and must produce the model id as
  the label, not a blank dropdown entry.  Covers the same ``or mid`` branch as
  the existing ``None`` test but makes the intent explicit for both falsy values.

---

## [0.2.48] – 2026-05-19

### Added

- **`diagnostics.py`** — Coordinator section now includes ``last_error``:
  the string representation of ``coordinator.last_exception`` when the most
  recent ``/v1/models`` poll failed, or ``null`` when it succeeded.
  ``DataUpdateCoordinator`` already tracks this; surfacing it in the
  diagnostics download means users can self-diagnose proxy connectivity issues
  without needing access to HA's log files.

### Added (tests)

- `test_diagnostics.py` — ``TestDiagnosticsLastError``: 4 tests verifying that
  ``last_error`` is ``None`` on success, carries the exception message on
  failure, is a ``str`` (JSON-serialisable), and is cleared after a successful
  poll.
- `test_diagnostics.py` — ``test_coordinator_section_includes_last_error_key``:
  verifies the key is always present in the coordinator section.

---

## [0.2.47] – 2026-05-19

### Added

- **`diagnostics.py`** — Coordinator section now includes ``update_interval``
  (e.g. ``"6:00:00"``), making it easy to confirm the model-refresh cadence
  from a downloaded diagnostics file without reading the source code.

### Changed

- **`const.py`** — Added a module-level ``assert`` that ``COORDINATOR_RETRY_DELAYS``
  has exactly ``COORDINATOR_MAX_RETRIES - 1`` entries.  The comment already
  documented the invariant, but there was no enforcement: a developer who
  changed one constant without updating the other would get silently wrong
  retry behaviour instead of an immediate ``AssertionError``.

### Added (tests)

- `test_diagnostics.py` — `test_update_interval_present_as_string`: verifies
  the new ``update_interval`` key is a human-readable string (``"6:00:00"``).
- `test_diagnostics.py` — `test_update_interval_non_default`: verifies the
  value is dynamic, not hardcoded.

---

## [0.2.46] – 2026-05-19

### Fixed

- **`config_flow.py`** — `api_key` is now stripped of leading/trailing
  whitespace before being used in the probe or stored in the config entry.
  Previously, a user who accidentally pasted their API key with surrounding
  spaces would receive a cryptic `invalid_auth` error.  `base_url` and `model`
  were already stripped; `api_key` was the only field that was not.

### Changed

- **`config_flow.py`** — `_parse_toml_and_validate` now returns a
  ``_ParseResult`` ``NamedTuple`` instead of a bare 6-tuple.  Existing callers
  using positional unpacking work without any change (``NamedTuple`` is a
  ``tuple`` subclass).  New callers can use named field access (``result.api_key``,
  ``result.base_url``, etc.) for clearer, index-independent code.

### Added (tests)

- `test_parse_toml_validate.py` — `TestApiKeyStripping`: 5 tests covering
  leading/trailing/surrounding whitespace stripping and no-op on clean keys.
- `test_parse_toml_validate.py` — `TestParseResultNamedAccess`: 7 tests
  verifying named attribute access and backward-compatible positional unpacking.

---

## [0.2.45] – 2026-05-19

### Changed

- **`config_flow.py`** — `async_step_user` in `CodexConfigFlow` now builds the
  initial subentry data via `_enrich_subentry_data()` (the same helper used by
  the subentry reconfigure flow) instead of constructing the dict manually.
  Removes a redundant literal assignment for `service_tier=None` /
  `llm_hass_api=[]` in the top-level flow, ensuring the two code-paths stay in
  sync automatically.
- **`config_flow.py`** — Added developer-facing docstrings to
  `_LLMSubentryFlowHandlerBase.async_step_user`, `async_step_reconfigure`, and
  `_build_schema` explaining the two-phase (show-form / submit) flow, the
  `_enrich_subentry_data` contract, and how defaults differ between *add* and
  *reconfigure* paths.

---

## [0.2.44] – 2026-05-19

### Fixed

- **`coordinator.py`** — The model-processing loop now skips non-dict entries
  (bare strings, ``None``, integers) in the proxy's model list with an
  ``isinstance(m, dict)`` guard.  Previously any non-dict element would raise
  ``AttributeError: 'str' object has no attribute 'get'`` and crash the
  entire coordinator update cycle.  Some non-standard reverse proxies return
  mixed-type lists; this makes the integration resilient against them.

### Added (tests)

- `test_coordinator.py` — `test_non_dict_entries_in_list_are_skipped`:
  exercises the helper with a mixed list (dict + str + None + int); guards the
  new ``isinstance`` check at the data-processing layer.
- `test_coordinator_retry.py` — `test_non_dict_entries_skipped_without_crash`:
  exercises ``_async_update_data`` end-to-end with a mixed-type payload from
  the proxy to ensure no ``AttributeError`` is raised.

---

## [0.2.43] – 2026-05-19

### Changed

- **`update.py`** (`title` property) — Changed from the generic `"Proxy chat
  model"` to `f"Proxy model ({subentry.title})"`.  Users with multiple
  subentries (conversation + AI Task) now see distinct update card titles in
  HA ("Proxy model (Codex 号池对话)" vs "Proxy model (Codex 号池 AI Task)")
  rather than two identical "Proxy chat model" cards.
- **`sensor.py`** — Added proper docstrings to `native_value` on both
  `CodexChatModelCountSensor` and `CodexLastRefreshSensor`, explaining the
  zero / ``None`` return conditions.

### Added (tests)

- `test_update_entity.py` — `test_title_includes_subentry_name` and
  `test_title_changes_with_subentry_title`: pin the new title format and
  guard the subentry-name disambiguating behaviour.
- `test_const.py` — `test_default_reasoning_effort_value`: pins
  `DEFAULT_REASONING_EFFORT == "xhigh"`; a silent change would alter
  inference cost for every new subentry.
- `test_const.py` — `test_probe_timeout_less_than_coordinator_timeout`:
  documents the design rationale (probe runs in UI-blocking flow, coordinator
  in background) and guards the ordering.

---

## [0.2.42] – 2026-05-19

### Changed

- **`coordinator.py`** (`chat_models` docstring) — Clarified that the property
  only **filters** (never sorts); the sort invariant is owned by
  `_async_update_data` and the returned list preserves stored order.
- **`update.py`** — Added proper docstrings to `installed_version` and
  `latest_version` properties, converting the existing inline comment
  on `latest_version`'s fallback behaviour into formal docstring text.

### Added (tests)

- `test_const.py` — `test_no_empty_prefix` and `test_all_prefixes_are_lowercase`
  for `IMAGE_MODEL_ID_PREFIXES`: guard against an accidental empty-string entry
  (would filter ALL models) or uppercase prefix (would silently fail to filter).
- `test_coordinator_properties.py` — `test_chat_models_returns_empty_when_models_key_absent`:
  verifies graceful degradation when `data` has no `"models"` key.

---

## [0.2.41] – 2026-05-19

### Changed

- **`coordinator.py`** (`latest_chat_model_id` docstring) — Added comprehensive
  docstring documenting the `(-created, id)` sort invariant, the two ``None``
  return conditions (coordinator unpopulated / image-only proxy), and the
  relationship to `_async_update_data`'s sort guarantee.

### Added (tests)

- `test_coordinator_properties.py` — `test_filter_does_not_reorder_chat_models`:
  verifies `chat_models` preserves input order and never re-sorts after filtering.
- `test_coordinator_properties.py` — `test_alphabetically_first_returned_when_timestamps_equal`:
  confirms `latest_chat_model_id` returns the first element of `chat_models` when
  all models carry the same `created` timestamp; input is pre-sorted to match the
  invariant `_async_update_data` guarantees.

---

## [0.2.40] – 2026-05-19

### Added

- **`strings.json` / `translations/en.json` / `translations/zh-Hans.json`** —
  `state_attributes` block added to `entity.binary_sensor.proxy_reachable`
  with human-readable names for `last_checked` and `latest_model`.  HA uses
  these to render proper labels in the More Info dialog and template editors.
- **`coordinator.py`** — Comprehensive docstring for `_async_update_data`
  documenting the retry policy (transient vs non-transient errors), the
  composite sort key, and the return shape.

### Added (tests)

- `test_translations.py` — `test_binary_sensor_state_attributes_documented`:
  verifies all three files declare `state_attributes` for `proxy_reachable`
  with `last_checked` and `latest_model`.

---

## [0.2.39] – 2026-05-19

### Changed

- **`coordinator.py`** (`chat_models` docstring) — Documents the alphabetical
  `id` tiebreaker introduced in v0.2.38 so the sort policy is visible without
  reading the implementation.

### Added (tests)

- `test_coordinator_retry.py` — `test_equal_timestamps_sorted_alphabetically`:
  exercises `_async_update_data` directly with same-timestamp models and
  confirms deterministic alphabetical ordering.
- `test_parse_toml_validate.py` — `test_base_url_with_surrounding_whitespace_stripped`:
  covers the `.strip()` call in `_parse_toml_and_validate` for manually
  entered base URLs (not from TOML).

---

## [0.2.38] – 2026-05-19

### Changed

- **`coordinator.py`** — Sort key changed from
  `sort(..., reverse=True)` (unstable when timestamps tie) to
  `sort(key=lambda x: (-x["created"], x["id"]))` (stable: highest
  timestamp first, alphabetical `id` as tiebreaker). Prevents spurious
  "update available" flicker on proxies that report `created=0` for all models.
- **`update.py`** — Converted inline comment on `_handle_coordinator_update`
  to a proper docstring matching the style used in `select.py`.
- **`sensor.py`** / **`binary_sensor.py`** / **`button.py`** — Added
  one-line docstrings to each `async_setup_entry` function.

### Added (tests)

- `test_coordinator.py` — `test_same_created_sorted_alphabetically_by_id`:
  pins the tiebreaker behaviour at the data-processing helper level.
- `test_const.py` — `test_default_model_value`: pins `DEFAULT_MODEL == "gpt-5.5"`;
  a silent change to this value would revert users' configurations.

---

## [0.2.37] – 2026-05-19

### Changed

- **`entity_utils.py`** — Renamed `_INTEGRATION_VERSION` → `INTEGRATION_VERSION`
  (removed leading underscore).  `diagnostics.py` imports this constant, so
  the underscore convention (private to module) was misleading; the public name
  is more accurate and avoids linter warnings about accessing private names
  from external modules.  All internal call-sites updated.

### Added (tests)

- `test_entity_utils.py` — `TestIntegrationVersion` class with three tests:
  `test_is_public_name`, `test_is_string_or_none`, and `test_matches_manifest`
  — directly exercises the renamed public constant and locks in its contract.

---

## [0.2.36] – 2026-05-19

### Changed

- **`coordinator.py`** — Added a full docstring to
  `CodexModelCoordinator.__init__` explaining the `hass`, `entry`, and
  `installation_id` parameters and the motivation for pre-building `_url`
  and `_headers` at init time.

### Added (tests)

- `test_coordinator_logging.py` — `test_debug_block_skipped_when_logging_disabled`:
  when `_LOGGER.isEnabledFor(DEBUG)` returns False the expensive `sum()` and
  `debug()` call must both be skipped, but the coordinator must still return
  the correct model list.

---

## [0.2.35] – 2026-05-19

### Fixed

- **`_pure_helpers.py`** — `parse_codex_toml` now strips leading/trailing
  whitespace from `base_url` values before removing trailing slashes
  (`str(provider["base_url"]).strip().rstrip("/")`).  Previously a TOML file
  with `base_url = " https://... "` would produce a URL starting with a space,
  which `validate_base_url` correctly rejected with `invalid_url_scheme`.  Now
  the value is cleaned up before validation, consistent with how `model` and
  `model_reasoning_effort` are already treated.

- **`tests/test_coordinator_retry.py`** — Fixed import order: `UpdateFailed`
  was imported from `homeassistant.helpers.update_coordinator` before
  `tests.ha_stubs` was bootstrapped, which caused `ModuleNotFoundError` when
  running the file in isolation.  Moved the import to after `ha_stubs`.
  Also moved `# isort: skip_file` to be immediately before
  `from __future__ import annotations` (no blank line) so ruff's isort
  recognises the directive correctly.

### Added (tests)

- `test_coordinator.py` — `test_empty_string_display_name_falls_back_to_id`:
  an explicit `display_name=""` must fall back to the model id (same as `None`).
- `test_pure_helpers.py` — `test_base_url_with_surrounding_whitespace_stripped`:
  verifies the new `.strip()` behaviour; `test_reasoning_effort_with_whitespace_stripped`:
  verifies `model_reasoning_effort` whitespace is already stripped (existing
  behaviour, newly documented in tests).
- `test_const.py` — `test_default_prompt_is_empty_string` guards against
  accidentally defaulting `DEFAULT_PROMPT` to a non-empty string.
- `test_manifest.py` — `test_quality_scale_is_silver` and
  `test_dependencies_is_empty_list`: guard accidental changes to
  `quality_scale` and `dependencies`.

---

## [0.2.34] – 2026-05-19

### Changed (tests)

- **`tests/ha_stubs.py`** — `SelectOptionDict` is now a real dict factory
  (`_SelectOptionDict(**kwargs) → dict`), so `option["value"]` and
  `option["label"]` return plain strings everywhere without any per-test
  patching.
- **`tests/test_model_select.py`** — Removed the now-redundant
  `_PATCH_SELECT_OPTION` context manager and the local `_SelectOptionDict`
  shim.  All ten tests call `_model_select_options` directly; ha_stubs
  provides the real dict-backed `SelectOptionDict`.

### Added (tests)

- **`tests/test_conversation_entity.py`** — `test_device_info_sw_version_present`
  added to both `TestCodexConversationEntity` and `TestCodexAITaskEntity`;
  verifies that `entity_utils.build_codex_device_info` now populates
  `sw_version` on subentry-level device info.

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
