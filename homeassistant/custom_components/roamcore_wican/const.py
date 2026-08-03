"""Constants for the RoamCore WiCAN Pro integration."""

from __future__ import annotations

DOMAIN = "roamcore_wican"

# --- Config-flow keys ---

CONF_HOST = "host"
CONF_PORT = "port"
CONF_POLL_INTERVAL = "poll_interval"
CONF_RETENTION_DAYS = "retention_days"
CONF_DISCOVERY_SOURCE = "discovery_source"  # "mdns" | "mqtt" | "manual"
CONF_DEVICE_NAME = "device_name"
CONF_DEVICE_SERIAL = "device_serial"

DEFAULT_PORT = 80
DEFAULT_POLL_INTERVAL = 5  # seconds; WiCAN Pro's default diag interval is 1s, but we
                            # default to 5s to keep SD-card writes sane on the HA host
MIN_POLL_INTERVAL = 1
MAX_POLL_INTERVAL = 60

DEFAULT_RETENTION_DAYS = 90
MIN_RETENTION_DAYS = 1
MAX_RETENTION_DAYS = 365

# --- WiCAN Pro REST endpoints (Custic firmware >= v2.x) ---
REST_DIAGNOSTICS = "/api/diagnostics"
REST_PIDS = "/api/pids"
REST_DTC = "/api/dtc"
REST_INFO = "/api/info"
REST_NETWORK = "/api/network"

# --- HTTP timeouts ---

HTTP_TIMEOUT = 10  # seconds; WiCAN can be slow on first POST when it wakes from CAN-bus idle
