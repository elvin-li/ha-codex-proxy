"""Shared Home Assistant module stubs for the codex_proxy test suite.

Import this module at the TOP of any test file, BEFORE any codex_proxy import.
It injects the minimum set of HA module mocks into sys.modules so that
codex_proxy can be imported without a real HA installation.

Usage::

    import tests.ha_stubs  # noqa: F401  — must precede codex_proxy imports

Key design constraints
----------------------
* ``DataUpdateCoordinator`` must be a real Python class (not a MagicMock)
  that supports generic subscript syntax ``DataUpdateCoordinator[X]`` and has
  an ``__init__`` with the same positional signature as the real HA class.
  Otherwise ``CodexModelCoordinator(DataUpdateCoordinator[dict])`` fails at
  class-definition time.

* ``CoordinatorEntity`` and ``UpdateEntity`` similarly need subscript support.

* All other modules not explicitly configured here are stubbed as plain
  ``MagicMock()`` instances — attribute access returns further MagicMocks,
  which is fine for code that only imports names at module level.

* The ``if _mod not in sys.modules`` guards mean the first test file to import
  this module "wins" for each stub. Import order matters — run your most
  demanding test file first or rely on alphabetical pytest collection order.
"""
from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock


class _Subscriptable:
    """Base whose subclasses support ``Cls[X]`` generic syntax at class-def time."""

    def __class_getitem__(cls, item: Any) -> type:
        return cls


class _DataUpdateCoordinator(_Subscriptable):
    """Minimal stand-in with the same __init__ signature as the real class."""

    def __init__(
        self,
        hass: Any,
        logger: Any,
        name: str,
        update_interval: Any,
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data: dict[str, Any] | None = None
        self.last_update_success: bool = True
        self.last_update_success_time: Any = None

    def _handle_coordinator_update(self) -> None:
        """Stub — real implementation notifies the HA state machine."""


class _CoordinatorEntity(_Subscriptable):
    """Minimal CoordinatorEntity: stores the coordinator reference."""

    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator

    def _handle_coordinator_update(self) -> None:
        """Stub."""


class _UpdateEntity(_Subscriptable):
    pass


class _BinarySensorEntity:
    pass


class _ButtonEntity:
    pass


class _SelectEntity:
    pass


class _SensorEntity:
    pass


class _OpenAIConversationEntity:
    """Minimal stand-in for OpenAIConversationEntity.

    The real class requires a live HA setup.  For testing we only need it to
    be a proper Python class (so `class CodexConversationEntity(...)` works)
    and to store the constructor arguments.
    """

    def __init__(self, entry: Any, subentry: Any) -> None:
        self._entry = entry
        self._subentry = subentry


class _OpenAITaskEntity:
    """Minimal stand-in for OpenAITaskEntity."""

    def __init__(self, entry: Any, subentry: Any) -> None:
        self._entry = entry
        self._subentry = subentry


class _SensorEntityDescription:
    """Preserves all kwargs as attributes so entity.description.key works."""

    def __init__(self, key: str, **kwargs: Any) -> None:
        self.key = key
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# Modules to stub as plain MagicMock (no special configuration needed)
# ---------------------------------------------------------------------------

_PLAIN_MOCKS = [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.button",
    "homeassistant.components.diagnostics",
    "homeassistant.components.openai_conversation",
    "homeassistant.components.openai_conversation.const",
    "homeassistant.components.openai_conversation.conversation",
    "homeassistant.components.openai_conversation.ai_task",
    "homeassistant.components.select",
    "homeassistant.components.sensor",
    "homeassistant.components.update",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.httpx_client",
    "homeassistant.helpers.selector",
    "homeassistant.helpers.update_coordinator",
    "openai",
    "voluptuous",
]

for _mod in _PLAIN_MOCKS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# ---------------------------------------------------------------------------
# Configure specific attributes that codex_proxy accesses by name
# ---------------------------------------------------------------------------

# Upstream const keys used by config_flow / entity code
_OAI_CONST = sys.modules["homeassistant.components.openai_conversation.const"]
if not isinstance(_OAI_CONST.CONF_CHAT_MODEL, str):
    _OAI_CONST.CONF_CHAT_MODEL = "chat_model"
    _OAI_CONST.CONF_PROMPT = "prompt"
    _OAI_CONST.CONF_REASONING_EFFORT = "reasoning_effort"
    _OAI_CONST.CONF_STORE_RESPONSES = "store_responses"
    _OAI_CONST.CONF_SERVICE_TIER = "service_tier"

_CONST = sys.modules["homeassistant.const"]
if not isinstance(_CONST.CONF_LLM_HASS_API, str):
    _CONST.CONF_LLM_HASS_API = "llm_hass_api"

# DataUpdateCoordinator / CoordinatorEntity — real subscriptable classes
_UPD = sys.modules["homeassistant.helpers.update_coordinator"]
if not isinstance(getattr(_UPD, "DataUpdateCoordinator", None), type):
    _UPD.DataUpdateCoordinator = _DataUpdateCoordinator
if not isinstance(getattr(_UPD, "CoordinatorEntity", None), type):
    _UPD.CoordinatorEntity = _CoordinatorEntity
if not isinstance(getattr(_UPD, "UpdateFailed", None), type):
    _UPD.UpdateFailed = Exception

# UpdateEntity
_UPD_COMP = sys.modules["homeassistant.components.update"]
if not isinstance(getattr(_UPD_COMP, "UpdateEntity", None), type):
    _UPD_COMP.UpdateEntity = _UpdateEntity

# BinarySensorEntity / ButtonEntity / SelectEntity / SensorEntity
_BIN = sys.modules["homeassistant.components.binary_sensor"]
if not isinstance(getattr(_BIN, "BinarySensorEntity", None), type):
    _BIN.BinarySensorEntity = _BinarySensorEntity

_BTN = sys.modules["homeassistant.components.button"]
if not isinstance(getattr(_BTN, "ButtonEntity", None), type):
    _BTN.ButtonEntity = _ButtonEntity

_SEL = sys.modules["homeassistant.components.select"]
if not isinstance(getattr(_SEL, "SelectEntity", None), type):
    _SEL.SelectEntity = _SelectEntity

_SEN = sys.modules["homeassistant.components.sensor"]
if not isinstance(getattr(_SEN, "SensorEntity", None), type):
    _SEN.SensorEntity = _SensorEntity
if not isinstance(getattr(_SEN, "SensorEntityDescription", None), type):
    _SEN.SensorEntityDescription = _SensorEntityDescription

# OpenAIConversationEntity / OpenAITaskEntity — real classes so that
# `class CodexConversationEntity(OpenAIConversationEntity)` works at import time.
_OAI_CONV = sys.modules["homeassistant.components.openai_conversation.conversation"]
if not isinstance(getattr(_OAI_CONV, "OpenAIConversationEntity", None), type):
    _OAI_CONV.OpenAIConversationEntity = _OpenAIConversationEntity

_OAI_TASK = sys.modules["homeassistant.components.openai_conversation.ai_task"]
if not isinstance(getattr(_OAI_TASK, "OpenAITaskEntity", None), type):
    _OAI_TASK.OpenAITaskEntity = _OpenAITaskEntity

# DeviceInfo as dict (simplest stand-in that works with **kwargs and indexing)
_DR = sys.modules["homeassistant.helpers.device_registry"]
if not isinstance(getattr(_DR, "DeviceInfo", None), type):
    _DR.DeviceInfo = dict

# core.callback is just an identity decorator.
# NOTE: Do NOT guard this with `if not callable(...)` — MagicMock objects are
# always callable, so that guard would never fire and @callback would apply a
# MagicMock as a decorator, replacing decorated methods with MagicMock instances.
_CORE = sys.modules["homeassistant.core"]
_CORE.callback = lambda f: f

# ---------------------------------------------------------------------------
# Wire submodule attributes onto parent mocks.
#
# When code uses `from homeassistant.helpers import device_registry as dr`,
# Python resolves it by looking up the `device_registry` ATTRIBUTE on the
# `homeassistant.helpers` mock object — NOT via sys.modules.  Since
# MagicMock.__getattr__ returns a fresh child mock for every attribute, that
# child is a *different* object from sys.modules["homeassistant.helpers.device_registry"]
# where we configured DeviceInfo = dict above.
#
# The fix: explicitly set the attribute on the parent so that the attribute-
# lookup path and the sys.modules path both land on the same configured object.
# ---------------------------------------------------------------------------
_HELPERS = sys.modules["homeassistant.helpers"]
_HELPERS.device_registry = sys.modules["homeassistant.helpers.device_registry"]
_HELPERS.update_coordinator = sys.modules["homeassistant.helpers.update_coordinator"]
_HELPERS.httpx_client = sys.modules["homeassistant.helpers.httpx_client"]
_HELPERS.entity_platform = sys.modules["homeassistant.helpers.entity_platform"]
_HELPERS.selector = sys.modules["homeassistant.helpers.selector"]

_COMPONENTS = sys.modules["homeassistant.components"]
_COMPONENTS.binary_sensor = sys.modules["homeassistant.components.binary_sensor"]
_COMPONENTS.button = sys.modules["homeassistant.components.button"]
_COMPONENTS.diagnostics = sys.modules["homeassistant.components.diagnostics"]
_COMPONENTS.openai_conversation = sys.modules[
    "homeassistant.components.openai_conversation"
]
_COMPONENTS.openai_conversation.conversation = sys.modules[
    "homeassistant.components.openai_conversation.conversation"
]
_COMPONENTS.openai_conversation.ai_task = sys.modules[
    "homeassistant.components.openai_conversation.ai_task"
]
_COMPONENTS.openai_conversation.const = sys.modules[
    "homeassistant.components.openai_conversation.const"
]
_COMPONENTS.select = sys.modules["homeassistant.components.select"]
_COMPONENTS.sensor = sys.modules["homeassistant.components.sensor"]
_COMPONENTS.update = sys.modules["homeassistant.components.update"]
