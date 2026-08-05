"""Manifest-honesty tests for connections/openwrt/connection.yml.

The openwrt/ connection (auto-pair layer) is a NEW
sibling slice that complements the existing tier-a
openwrt-controls/ connection (which wraps the two
RoamCore-owned packages at
`homeassistant/packages/roamcore_openwrt_api.yaml` +
`homeassistant/packages/roamcore_net.yaml`).

The new slice adds a LAN discovery module at
`homeassistant/custom_components/roamcore/discovery/`
(real asyncio stdlib-first probe + token push + token
verify) and a connection-side `apply_pair()` helper at
`connections/openwrt/__init__.py`.

Tests:
  - id matches folder name
  - tier-a with real discovery code
  - docs recipe published
  - user-facing IKEA-style doc
  - dashboard tiles follow rc_naming
  - status reflects real probe + pytest
  - automations are documented

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/openwrt/tests/test_connection_yml.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]
CONNECTION_DIR = REPO_ROOT / "connections" / "openwrt"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
INIT_PATH = CONNECTION_DIR / "__init__.py"
DOCS_DIR = CONNECTION_DIR / "docs"
RECIPE_PATH = DOCS_DIR / "recipe.md"
RUNBOOK_PATH = DOCS_DIR / "runbook-devbox.md"

DISCOVERY_DIR = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore" / "discovery"
DISCOVERY_INIT = DISCOVERY_DIR / "__init__.py"
DISCOVERY_PROBE = DISCOVERY_DIR / "probe.py"
DISCOVERY_PAIR = DISCOVERY_DIR / "pair.py"

USER_FACING_DOC = REPO_ROOT / "docs" / "catalog" / "networking" / "openwrt-controls.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name."""
    assert CONNECTION_DIR.name == "openwrt"
    assert manifest["id"] in ("openwrt", "openwrt_discovery"), (
        f"manifest id={manifest['id']!r} must be "
        f"'openwrt' or 'openwrt_discovery'"
    )


def test_tier_a_with_real_discovery_code(manifest: dict) -> None:
    """Tier-a must advertise tier-a-only RoamCore-
    owned fields AND must back them with real on-disk
    code.
    """
    assert manifest["tier"] == "a"
    assert manifest["install"]["config_flow"] is True
    assert manifest["wizard"]["one_tap"] is True
    assert manifest["wizard"]["auto_discover"] is True

    # The discovery module MUST exist on disk.
    assert DISCOVERY_DIR.is_dir(), f"missing {DISCOVERY_DIR}"
    assert DISCOVERY_INIT.is_file(), f"missing {DISCOVERY_INIT}"
    assert DISCOVERY_PROBE.is_file(), f"missing {DISCOVERY_PROBE}"
    assert DISCOVERY_PAIR.is_file(), f"missing {DISCOVERY_PAIR}"

    probe_text = DISCOVERY_PROBE.read_text(encoding="utf-8")
    assert "BANNER_HEADER" in probe_text
    assert "BANNER_VALUE" in probe_text
    assert "DEFAULT_PORTS" in probe_text
    assert "async def probe_ip" in probe_text
    assert "async def scan_subnet" in probe_text

    pair_text = DISCOVERY_PAIR.read_text(encoding="utf-8")
    assert "def generate_token" in pair_text
    assert "async def push_token" in pair_text
    assert "async def verify_token" in pair_text
    assert "TOKEN_HEX_LENGTH" in pair_text
    assert "TOKEN_HEX_LENGTH = 32" in pair_text

    init_text = INIT_PATH.read_text(encoding="utf-8")
    assert "DOMAIN" in init_text
    assert 'DOMAIN = "openwrt_discovery"' in init_text
    # Substring guard: no literal config_flow.py.
    assert "config_flow.py" not in init_text
    assert "operator-wired" in init_text
    assert "apply_pair" in init_text
    assert "discover_candidates" in init_text
    assert "plain_english_error" in init_text


def test_requires_docs_recipe_published(manifest: dict) -> None:
    """docs_recipe_published must be in tier_requirements."""
    assert "docs_recipe_published" in manifest["tier_requirements"]
    assert RECIPE_PATH.is_file(), f"missing {RECIPE_PATH}"
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert "homeassistant/custom_components/roamcore/discovery/" in text, (
        "recipe.md must reference the discovery module"
    )
    assert RUNBOOK_PATH.is_file(), f"missing {RUNBOOK_PATH}"
    runbook_text = RUNBOOK_PATH.read_text(encoding="utf-8")
    assert "192.168.1.250" in runbook_text, (
        "runbook-devbox.md must reference the OpenWrt VM dev IP"
    )


def test_user_facing_doc_is_ikea_style(manifest: dict) -> None:
    """The user-facing IKEA 5-step doc must live at
    docs/catalog/networking/openwrt-controls.md.
    """
    assert USER_FACING_DOC.is_file()
    text = USER_FACING_DOC.read_text(encoding="utf-8")
    expected_step_headings = ("step 1", "step 2", "step 3", "step 4", "step 5")
    text_lower = text.lower()
    for step in expected_step_headings:
        assert step in text_lower, (
            f"user-facing IKEA doc is missing '{step}' heading"
        )
    expected_errors = ("couldn't find", "plugged in", "network cable")
    for phrase in expected_errors:
        assert phrase in text_lower, (
            f"user-facing IKEA doc must contain the plain-English error phrase '{phrase}'"
        )
    assert "SUPERSEDED" not in text, (
        "user-facing IKEA doc must NOT carry the SUPERSEDED banner"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names."""
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles

    pattern = re.compile(r"^[a-z_]+\.rc_openwrt_discovery_[a-z0-9_]+$")

    forbidden_substrings = (
        "luci", "ubus", "rpcd", "uci", "uhttpd",
        "netifd", "wpad", "hostapd", "wpa_supplicant",
        "dnsmasq", "odhcpd", "qmi", "mbim",
        "modemmanager", "sstp", "wireguard", "pptpd",
        "victron", "renogy", "shunt", "bms",
        "inverter", "mppt", "see level", "seelevel",
        "garnet", "mopeka", "icon", "resistive",
        "tank", "peplink", "teltonika", "unifi",
        "ubiquiti", "mqtt", "webhook", "rest",
        "http", "https", "ha core", "hacs",
        "tasmota", "esphome", "companion", "esp32",
        "esp8266", "nodemcu", "wemos", "shelly",
        "sonoff", "zwave", "zha", "zigbee", "deconz",
        "conbee", "raspbee", "nous", "aqara",
        "bluetooth", "input_boolean", "input_text",
        "input_datetime", "input_button", "gps",
        "accelerometer", "gyroscope", "magnetometer",
        "compass", "heading", "iphone", "ios",
        "android", "samsung", "pixel", "oneplus",
        "xiaomi", "huawei", "phone",
    )

    for tile in tiles:
        assert isinstance(tile, str)
        assert pattern.match(tile), (
            f"tile id {tile!r} must match "
            f"^[a-z_]+\\.rc_openwrt_discovery_[a-z0-9_]+$"
        )
        suffix = tile.split(".rc_openwrt_discovery_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor substring {bad!r}"
            )


def test_status_reflects_real_probe_and_pytest(manifest: dict) -> None:
    """Status must be 'beta' (tier-a-but-flagged)."""
    assert manifest["status"] == "beta"
    tier_warnings = manifest.get("tier_warnings", [])
    assert "real_discovery_code_real_pytest_http_probe" in tier_warnings
    assert "no_full_bench_fixture_for_multi_subnet" in tier_warnings

    integration_tests = (
        manifest.get("tier_requirements", {})
        .get("integration_tests", {})
    )
    assert integration_tests.get("present") is False
    assert integration_tests.get("reason")
    bench_artifacts_needed = integration_tests.get(
        "bench_artifacts_needed", []
    )
    assert len(bench_artifacts_needed) >= 3
    required_bench_artifacts = (
        "canned OpenWrt banner response (X-RoamCore-Api: ok) on 127.0.0.1:18080",
        "canned OpenWrt banner response (no banner - empty list returned)",
        "canned OpenWrt /api/roamcore/token endpoint (accepts 32-hex-char tokens)",
    )
    for required_artifact in required_bench_artifacts:
        assert required_artifact in bench_artifacts_needed


def test_automations_are_documented(manifest: dict) -> None:
    """The FIVE mandatory section-8 automations are documented."""
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert "## section 8 mandatory" in text.lower() or "## section-8 mandatory" in text.lower() or "section 8" in text.lower(), (
        "recipe.md must have a section for the FIVE MANDATORY automations"
    )
    automation_coverage = (
        "lan-probe failure tile-unavailable guard",
        "router-found-but-not-paired guard",
        "pair-failed guard",
        "token-push-confirmation guard",
        "ha-boot-discovery-doesn't-block guard",
    )
    for phrase in automation_coverage:
        assert phrase in text.lower(), (
            f"recipe.md must cover {phrase!r}"
        )

if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
