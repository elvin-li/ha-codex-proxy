# Contributing to Codex Token Pool

Thanks for your interest! Here's how to get started.

## Development setup

```bash
git clone https://github.com/elvin-li/ha-codex-proxy
cd ha-codex-proxy

# Install test dependencies (no HA install needed)
pip install -r requirements_test.txt

# Optional: install pre-commit hooks for local quality gates
pip install pre-commit
pre-commit install
```

## Running tests

```bash
pytest tests/ -v
```

All 406+ tests run without a Home Assistant installation. They mock the
`homeassistant.*` namespace via `sys.modules` injection so you can develop
and test purely against the Python stdlib + real `httpx`.

To run with coverage reporting (requires `pytest-cov`, included in
`requirements_test.txt`):

```bash
pytest tests/ -v --cov=custom_components/codex_proxy --cov-report=term-missing
```

The integration maintains **100% source-line coverage** across all 14 source
files. Every new feature must come with tests that keep coverage at 100%.

## Project layout

```
custom_components/codex_proxy/
├── __init__.py          # Entry setup / teardown / migration
├── config_flow.py       # Config flow: setup, reconfigure, subentry flows
├── coordinator.py       # /v1/models polling with retry/back-off
├── conversation.py      # Conversation entity (thin subclass of upstream)
├── ai_task.py           # AI Task entity (thin subclass of upstream)
├── binary_sensor.py     # Proxy-reachable binary sensor
├── button.py            # Refresh-models button
├── select.py            # Active-model select entity
├── sensor.py            # Diagnostic sensors (model count, last refresh)
├── update.py            # Update entity: installed vs latest model
├── diagnostics.py       # Diagnostics download (API key redacted)
├── entity_utils.py      # Shared DeviceInfo builder (incl. sw_version)
├── _pure_helpers.py     # Pure-Python TOML parser + URL validator
├── const.py             # All constants
└── translations/        # zh-Hans.json, en.json
tests/
├── conftest.py                     # Shared fixtures
├── ha_stubs.py                     # HA module mock bootstrap (no HA install needed)
├── test_binary_sensor.py           # Proxy-reachable sensor logic
├── test_button.py                  # Refresh-models button
├── test_config_flow.py             # _pure_helpers TOML + URL validation
├── test_const.py                   # Constant value checks
├── test_conversation_entity.py     # Conversation entity device_info
├── test_coordinator.py             # Model processing / dedup / image filter
├── test_coordinator_init.py        # Coordinator construction
├── test_coordinator_logging.py     # Coordinator debug log
├── test_coordinator_properties.py  # chat_models + latest_chat_model_id
├── test_coordinator_request.py     # Request headers
├── test_coordinator_retry.py       # Retry/backoff with mocked httpx
├── test_diagnostics.py             # Redaction + data shape
├── test_enrich_subentry.py         # _enrich_subentry_data
├── test_entity_utils.py            # DeviceInfo builders (incl. sw_version)
├── test_init.py                    # _build_codex_headers
├── test_main_flow.py               # async_step_user full flow
├── test_manifest.py                # manifest.json structure
├── test_migrate_entry.py           # async_migrate_entry
├── test_model_select.py            # _model_select_options dropdown builder
├── test_parse_toml_validate.py     # _parse_toml_and_validate form helper
├── test_platform_setup.py          # async_setup_entry for each platform
├── test_probe_proxy.py             # _probe_proxy error mapping
├── test_pure_helpers.py            # parse_codex_toml + validate_base_url
├── test_reconfigure_flow.py        # async_step_reconfigure data preservation
├── test_select.py                  # CodexModelSelectEntity logic
├── test_sensor.py                  # Sensor entity native_value
├── test_setup_entry.py             # async_setup_entry (coordinator init)
├── test_setup_unload.py            # async_unload_entry
├── test_subentry_flow.py           # Subentry add/reconfigure flows
├── test_translations.py            # Translation file key consistency
└── test_update_entity.py           # Update entity logic + install + live refresh
```

## Adding a new feature

1. **Write a failing test first** — all new logic should be exercisable without HA.  
   If your code requires HA, extract the pure logic to `_pure_helpers.py` or a standalone function.

2. **Keep the thin-shim principle** — avoid duplicating logic that already lives in
   `homeassistant.components.openai_conversation`. Prefer subclassing + overriding
   the specific attribute that needs to change.

3. **Translations** — any new UI string needs to be added to all three files:
   - `custom_components/codex_proxy/strings.json` (source of truth)
   - `custom_components/codex_proxy/translations/en.json`
   - `custom_components/codex_proxy/translations/zh-Hans.json`

4. **Update CHANGELOG.md** — add a line to the `[Unreleased]` section.

5. **Open a PR** — use the template in `.github/pull_request_template.md`.

## Coding style

- Python 3.12+ type hints on all public functions.
- `from __future__ import annotations` at the top of every module.
- No bare `except Exception` — catch specific exception types.
- No `# noqa` suppressions without explanation.
- Ruff is configured in `pyproject.toml` — run `ruff check . && ruff format .` before committing
  (or install the pre-commit hooks which do this automatically).

## Architecture notes

### Why raw httpx in the coordinator?

The upstream `openai` SDK 2.x cursor-page parser fails on this proxy's `/v1/models`
response (`'str' object has no attribute '_set_private_attributes'`). We bypass the SDK
and call the endpoint directly with the HA shared httpx client.

### Why `after_dependencies` instead of `dependencies`?

`dependencies` would cause HA to load `openai_conversation` before this integration,
creating a hard dependency that would deadlock if `openai_conversation` itself tries to
load a dependency that loads `codex_proxy`. `after_dependencies` expresses ordering
without creating a hard dependency.

### Why `service_tier = None`?

Codex reverse-proxies return 502 for any non-null `service_tier` value
(`"auto"`, `"default"`, `"flex"`). Pinning it to `None` causes the SDK to omit the
field from the request payload entirely.

### Why never call `client.close()`?

The `AsyncOpenAI` client wraps HA's shared httpx client (`get_async_client(hass)`).
Calling `close()` would tear down HTTP I/O for every other integration in HA.
