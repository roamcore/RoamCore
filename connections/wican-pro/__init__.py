"""WiCAN Pro (OBD2 reader for van telemetry) — tier-a native connection.

This is a marker-only stub for the connection manifest. The actual
runtime code lives at:

    homeassistant/custom_components/roamcore_wican/

That custom component is a full Home Assistant integration (config_flow +
coordinator + sensor platforms + SQLite time-series store + HTTP
read-only views). This `__init__.py` exists only so the audit + boundary
CI can detect a `wican-pro/` folder that claims to be a connection via
the `DOMAIN` constant.

Tier-a is honest here: the custom component we ship is RoamCore-owned
(not a recipe wrapping an upstream integration), so this folder is the
right place for the slice + connection manifest, and the custom
component folder is the right place for the runtime code.
"""

DOMAIN = "roamcore_wican"
