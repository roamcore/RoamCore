"""Tests package marker for custom_components.roamcore.

This file does two things:
1. Acts as the package marker so `python -m unittest
   custom_components.roamcore.tests.test_automation_intents` can find the
   tests via the standard discovery rules.
2. Pre-installs lightweight stubs for the `homeassistant` core modules so
   the integration's `__init__.py` (which is loaded transitively when the
   tests are imported) can be parsed without a live HA install. We only
   stub the names the integration's top-level imports touch at module
   load time — no runtime HA calls happen here (the tests are pure-Python).
"""

from __future__ import annotations

import sys
import types


def _ensure_stub(name: str, attrs: dict[str, object] | None = None) -> None:
    """Create a stub module for `name` if one isn't already importable.

    Any attrs passed in are set on the stub so `from <name> import X`
    works for downstream imports.
    """
    if name in sys.modules:
        return
    mod = types.ModuleType(name)
    for k, v in (attrs or {}).items():
        setattr(mod, k, v)
    sys.modules[name] = mod


# We need *just enough* of `homeassistant` so `custom_components.roamcore`
# can be imported. The tests themselves never call HA; they exercise
# automation_intents (a pure-Python module) directly.
_ensure_stub("homeassistant")

_ensure_stub("homeassistant.config_entries", {"ConfigEntry": object})
_ensure_stub("homeassistant.const", {"Platform": types.SimpleNamespace(SENSOR="sensor")})
_ensure_stub("homeassistant.core", {"HomeAssistant": object})
_ensure_stub("homeassistant.components", {})
_ensure_stub("homeassistant.components.http", {"HomeAssistantView": object})
_ensure_stub("homeassistant.helpers", {})
_ensure_stub("homeassistant.helpers.entity_registry", {"async_get": lambda hass: None})
_ensure_stub("homeassistant.components.recorder", {})
_ensure_stub("homeassistant.components.recorder")
_recorder = sys.modules["homeassistant.components.recorder"]
_recorder.history = types.SimpleNamespace(
    get_significant_states=lambda *a, **kw: {}
)
_ensure_stub("homeassistant.util")
_dt_mod = sys.modules["homeassistant.util"]
_dt_mod.dt = types.SimpleNamespace(utcnow=lambda: None, as_utc=lambda x: x)
_ensure_stub("aiohttp")
_aiohttp = sys.modules["aiohttp"]
_aiohttp.web = types.SimpleNamespace(Response=object)