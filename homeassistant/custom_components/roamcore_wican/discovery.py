"""Auto-discovery for WiCAN Pro devices.

The WiCAN Pro (Custic SA) supports two auto-discovery paths from Home
Assistant's perspective:

  1. mDNS (`_wican._tcp.local`) — the device announces itself on the LAN
     via Avahi / Bonjour once it's joined the Wi-Fi network. We hook
     HA's existing zeroconf integration: the WiCAN Pro's mDNS TXT record
     includes the device name + firmware version + a `path=/api/diagnostics`
     hint pointing at the REST endpoint.
  2. MQTT — if the operator has already configured the WiCAN Pro to
     publish telemetry to an MQTT broker, HA's MQTT integration will
     pick up the discovery messages on `<prefix>/<device-id>/config`
     and surface them. We register an MQTT discovery topic template at
     `homeassistant/sensor/roamcore_wican/<device-id>/config`.

The third path (operator-supplied IP) is exposed via the config_flow as
a manual fallback.

We deliberately do NOT scan subnets or do raw TCP probing — that's
unreliable on busy Wi-Fi and generates noise. mDNS + MQTT are the
two supported discovery channels.

References:
  - Custic WiCAN Pro docs (manual section 4.3 — mDNS service name)
  - HA zeroconf integration: https://www.home-assistant.io/integrations/zeroconf/
  - HA MQTT discovery: https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

_LOGGER = logging.getLogger(__name__)

# Service type for mDNS — WiCAN Pro announces this on Avahi.
MDNS_SERVICE_TYPE = "_wican._tcp.local."

# MQTT discovery prefix — matches the RoamCore convention used by other
# integrations. The WiCAN's MQTT bridge (if configured) publishes to:
#   <prefix>/<device_id>/status  — online/offline (LWT)
#   <prefix>/<device_id>/telemetry/<pid>  — per-PID readings
MQTT_DISCOVERY_PREFIX = "homeassistant"
MQTT_DEVICE_TOPIC_PREFIX = "roamcore_wican"


@dataclass(frozen=True)
class DiscoveredWican:
    """A discovered WiCAN Pro device — the config_flow presents these."""

    name: str
    host: str
    port: int
    firmware_version: Optional[str] = None
    serial: Optional[str] = None
    discovery_source: str = "unknown"  # "mdns" | "mqtt" | "manual"


def parse_mdns_service_name(service_name: str) -> Optional[DiscoveredWican]:
    """Parse a WiCAN Pro mDNS service name into a DiscoveredWican.

    WiCAN Pro advertises its service name in the form:
      WiCAN-<last-6-of-mac>._wican._tcp.local.

    The TXT record contains: fw=<version>, path=/api/diagnostics, sn=<serial>.

    Returns None if the name doesn't match the WiCAN pattern.
    """
    m = re.match(r"^(WiCAN-[A-Fa-f0-9]{6,12})\._wican\._tcp\.local\.$", service_name)
    if not m:
        return None
    device_name = m.group(1)
    # WiCAN Pro defaults to port 80 (HTTP) unless the operator changed it.
    return DiscoveredWican(
        name=device_name,
        host=None,  # filled in by HA's zeroconf hook (we get the IP separately)
        port=80,
        firmware_version=None,  # filled in by HA from the TXT record
        serial=None,
        discovery_source="mdns",
    )


def mqtt_discovery_topic(device_id: str, component: str = "sensor") -> str:
    """Return the MQTT discovery topic we publish to (used by the broker side)."""
    return f"{MQTT_DISCOVERY_PREFIX}/{component}/{MQTT_DEVICE_TOPIC_PREFIX}/{device_id}/config"


def mqtt_telemetry_topic(device_id: str, pid_hex: str) -> str:
    """Return the MQTT telemetry topic for a specific PID (e.g. '0C')."""
    return f"{MQTT_DEVICE_TOPIC_PREFIX}/{device_id}/telemetry/{pid_hex.upper()}"


def mqtt_status_topic(device_id: str) -> str:
    """Return the MQTT Last-Will-and-Testament status topic."""
    return f"{MQTT_DEVICE_TOPIC_PREFIX}/{device_id}/status"


def is_valid_wican_host(host: str) -> bool:
    """Sanity-check a hostname or IP entered by the operator in the config_flow.

    Accepts:
      - IPv4 addresses (strictly 4 octets, each 0-255)
      - RFC 1123 hostnames (alphanumeric + hyphens, dot-separated labels)
    """
    if not host:
        return False
    # IPv4 (strictly 4 octets)
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host):
        parts = [int(p) for p in host.split(".")]
        return all(0 <= p <= 255 for p in parts)
    # Reject anything that looks like a partial IPv4 (numeric with dots but not 4 octets)
    if re.match(r"^\d+(\.\d+)+$", host):
        return False
    # Hostname (RFC 1123-ish — alphanumeric + hyphens, dot-separated)
    if re.match(r"^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$", host):
        return len(host) <= 253
    return False
