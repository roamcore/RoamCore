"""RoamCore Traccar connection — thin shim.

The actual integration code lives in
``homeassistant/custom_components/roamcore_traccar_proxy/__init__.py``
(it's an `async_setup`-only integration that registers HTTP views for
the same-origin proxy). This module is the connections-pipeline entry
point used by the wizard + audit + registry.

Why a shim and not a copy?
  - The integration predates the connections pipeline.
  - Copies would drift. The shim re-exports the live constants so the
    pipeline sees the integration's actual identity, not a snapshot.
  - When the integration moves into this folder (Day N of the migration),
    the shim becomes a passthrough and the migration is a one-commit
    rename.

Promoting to tier-a:
  To upgrade this connection to ``tier: a`` the integration must land
  a real ``config_flow`` and ``config_entry`` setup, plus the
  ``tests/test_config_flow.py`` must exercise the flow. Until then,
  ``status: shipped`` + ``tier: b`` is the honest answer.
"""

from __future__ import annotations

# Re-export the integration's identity so the pipeline (registry, audit,
# wizard) sees the same domain + prefix as the live integration code.
try:
    from homeassistant.custom_components.roamcore_traccar_proxy import (
        DOMAIN,                  # "roamcore_traccar_proxy"
        DEFAULT_UPSTREAM,        # "http://127.0.0.1:8082"
        PROXY_PREFIX,            # "/api/roamcore/traccar"
        PUBLIC_WEB_PREFIX,       # "/traccar"
        API_PREFIX,              # "/api/roamcore/traccar_api"
    )
except ImportError:  # pragma: no cover — HA not on the test PYTHONPATH
    # Fallback constants when the integration is not importable (e.g. when
    # audit_connections.py is run from CI without the homeassistant package).
    DOMAIN = "roamcore_traccar_proxy"
    DEFAULT_UPSTREAM = "http://127.0.0.1:8082"
    PROXY_PREFIX = "/api/roamcore/traccar"
    PUBLIC_WEB_PREFIX = "/traccar"
    API_PREFIX = "/api/roamcore/traccar_api"


__all__ = [
    "DOMAIN",
    "DEFAULT_UPSTREAM",
    "PROXY_PREFIX",
    "PUBLIC_WEB_PREFIX",
    "API_PREFIX",
]


def ha_integration_domain() -> str:
    """Return the HA integration domain. The wizard uses this to look up
    the integration's config_flow status, icon, etc."""
    return DOMAIN


def proxy_route() -> str:
    """Return the public iframe route embedded on the RoamCore map page."""
    return PUBLIC_WEB_PREFIX


def api_route() -> str:
    """Return the API route used by the dashboard map to fetch positions."""
    return API_PREFIX
