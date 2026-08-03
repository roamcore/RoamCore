"""Unit tests for the WiCAN Pro discovery layer."""

from __future__ import annotations

import sys
import pathlib

# Make the custom_components dir importable
_COMP = pathlib.Path(__file__).resolve().parents[3] / "homeassistant" / "custom_components" / "roamcore_wican"
sys.path.insert(0, str(_COMP))

from discovery import (  # noqa: E402
    DiscoveredWican,
    MDNS_SERVICE_TYPE,
    MQTT_DISCOVERY_PREFIX,
    MQTT_DEVICE_TOPIC_PREFIX,
    is_valid_wican_host,
    mqtt_discovery_topic,
    mqtt_status_topic,
    mqtt_telemetry_topic,
    parse_mdns_service_name,
)


# --- mDNS service name parsing ---

def test_parse_wican_pro_mdns_name():
    """WiCAN Pro advertises as 'WiCAN-A1B2C3._wican._tcp.local.'"""
    result = parse_mdns_service_name("WiCAN-A1B2C3._wican._tcp.local.")
    assert result is not None
    assert result.name == "WiCAN-A1B2C3"
    assert result.port == 80
    assert result.discovery_source == "mdns"


def test_parse_wican_pro_mdns_name_long_serial():
    """Some firmware versions use the full MAC (12 hex chars)."""
    result = parse_mdns_service_name("WiCAN-123456ABCDEF._wican._tcp.local.")
    assert result is not None
    assert result.name == "WiCAN-123456ABCDEF"


def test_parse_non_wican_mdns_name():
    """Other mDNS services (e.g. _http._tcp) should return None."""
    assert parse_mdns_service_name("myserver._http._tcp.local.") is None


def test_parse_malformed_mdns_name():
    assert parse_mdns_service_name("") is None
    assert parse_mdns_service_name("garbage") is None
    assert parse_mdns_service_name("WiCAN-zz._wican._tcp.local.") is None  # non-hex
    assert parse_mdns_service_name("WiCAN-A1._wican._tcp.local") is None  # missing trailing dot


# --- MQTT topic helpers ---

def test_mqtt_discovery_topic():
    topic = mqtt_discovery_topic("WiCAN-A1B2C3")
    assert topic == "homeassistant/sensor/roamcore_wican/WiCAN-A1B2C3/config"


def test_mqtt_telemetry_topic_uppercase_pid():
    topic = mqtt_telemetry_topic("WiCAN-A1B2C3", "0C")
    assert topic == "roamcore_wican/WiCAN-A1B2C3/telemetry/0C"


def test_mqtt_status_topic():
    topic = mqtt_status_topic("WiCAN-A1B2C3")
    assert topic == "roamcore_wican/WiCAN-A1B2C3/status"


def test_mqtt_prefix_constants():
    assert MQTT_DISCOVERY_PREFIX == "homeassistant"
    assert MQTT_DEVICE_TOPIC_PREFIX == "roamcore_wican"
    assert MDNS_SERVICE_TYPE == "_wican._tcp.local."


# --- Host validation (config_flow fallback) ---

def test_is_valid_wican_host_ipv4():
    assert is_valid_wican_host("192.168.1.10")
    assert is_valid_wican_host("10.0.0.1")
    assert is_valid_wican_host("127.0.0.1")


def test_is_valid_wican_host_ipv4_edge_cases():
    assert is_valid_wican_host("0.0.0.0")  # technically valid (zero host)
    assert is_valid_wican_host("255.255.255.255")
    assert not is_valid_wican_host("256.0.0.0")  # octet > 255
    assert not is_valid_wican_host("192.168.1")  # too few octets
    assert not is_valid_wican_host("192.168.1.300")  # octet > 255


def test_is_valid_wican_host_hostname():
    assert is_valid_wican_host("wican-pro")
    assert is_valid_wican_host("wican.local")
    assert is_valid_wican_host("my-van-wifi-router.lan")


def test_is_valid_wican_host_invalid():
    assert not is_valid_wican_host("")
    assert not is_valid_wican_host(" ")
    assert not is_valid_wican_host("host with spaces")
    assert not is_valid_wican_host("../etc/passwd")
    assert not is_valid_wican_host("a" * 300)  # too long


def test_is_valid_wican_host_localhost_variants():
    assert is_valid_wican_host("localhost")
    assert is_valid_wican_host("localhost.localdomain")


# --- DiscoveredWican dataclass ---

def test_discovered_wican_defaults():
    d = DiscoveredWican(name="WiCAN-A1B2C3", host="192.168.1.10", port=80)
    assert d.discovery_source == "unknown"
    assert d.firmware_version is None
    assert d.serial is None


def test_discovered_wican_with_all_fields():
    d = DiscoveredWican(
        name="WiCAN-A1B2C3",
        host="192.168.1.10",
        port=80,
        firmware_version="2.1.4",
        serial="WCP-A1B2C3-1234",
        discovery_source="mdns",
    )
    assert d.firmware_version == "2.1.4"
    assert d.serial == "WCP-A1B2C3-1234"


def test_discovered_wican_is_immutable():
    d = DiscoveredWican(name="x", host="y", port=80)
    try:
        d.name = "z"  # type: ignore[misc]
        assert False, "should have raised FrozenInstanceError"
    except Exception:
        pass
