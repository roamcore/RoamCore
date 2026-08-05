"""Mock-kill tests for homeassistant/packages/roamcore_power.yaml.

Wave 9 #114 — power mock-kill.

What we assert:
1. The old `input_number.rc_mock_power_*` fallback chain is gone from the
   power package. Power tile sensors MUST go `unavailable` instead of reading
   from dev-mock input_numbers.
2. The new banner entity `binary_sensor.rc_power_no_real_source` exists, is
   named canonically per `docs/reference/rc-entity-naming.md`
   (binary_sensor.<scope>_<noun>_<state>), and reacts to Victron source
   availability — NOT to dev mocks.
3. The auto-recover entity `binary_sensor.rc_power_offline_checking` exists
   for the "Victron went offline >5min" case (no crash-to-mock).
4. The plain-English status sensor `sensor.rc_power_source_status` exists and
   carries both banner strings.
5. The native dashboard YAML wires `binary_sensor.rc_power_no_real_source`
   into a conditional banner card so the UI shows the truth.

This is a real check (loads the actual YAML on disk), not a stub.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> packages/ -> homeassistant/ -> repo
POWER_YAML = REPO_ROOT / "homeassistant" / "packages" / "roamcore_power.yaml"
DASHBOARD_YAML = REPO_ROOT / "homeassistant" / "lovelace" / "roamcore-dashboard-native.yaml"

RC_BANNER_ID = "binary_sensor.rc_power_no_real_source"
RC_OFFLINE_CHECKING_ID = "binary_sensor.rc_power_offline_checking"
RC_STATUS_ID = "sensor.rc_power_source_status"

BANNER_NO_SOURCE = "Power not connected — go to Setup."
BANNER_OFFLINE_CHECKING = "Power source went offline — checking..."


def _find_binary_sensor_state(power_doc: dict, unique_id: str):
    template = (power_doc.get("template") or [])
    for block in template:
        for entry in (block.get("binary_sensor") or []):
            if entry.get("unique_id") == unique_id:
                return entry.get("state")
    return None


def _find_sensor_state(power_doc: dict, unique_id: str):
    template = (power_doc.get("template") or [])
    for block in template:
        for entry in (block.get("sensor") or []):
            if entry.get("unique_id") == unique_id:
                return entry.get("state")
    return None


def _unique_ids(power_doc: dict) -> set:
    ids: set = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "unique_id" and isinstance(v, str):
                    ids.add(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(power_doc)
    return ids


@pytest.fixture(scope="module")
def power_doc():
    assert POWER_YAML.is_file(), f"missing package at {POWER_YAML}"
    return yaml.safe_load(POWER_YAML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def power_text():
    return POWER_YAML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dashboard_text():
    assert DASHBOARD_YAML.is_file(), f"missing dashboard at {DASHBOARD_YAML}"
    return DASHBOARD_YAML.read_text(encoding="utf-8")


# 1. Mock fallback chain is GONE.
def test_no_input_number_rc_mock_power_references(power_text):
    offenders = re.findall(r"input_number\.rc_mock_power_[a-zA-Z0-9_]+", power_text)
    assert offenders == [], (
        "roamcore_power.yaml still references the dev-mock fallback chain: "
        f"{offenders}. Wave 9 #114: strip the fallback chain so sensors go "
        "`unavailable` when no real source is present."
    )


def test_no_input_boolean_rc_mock_power_references(power_text):
    offenders = re.findall(r"input_boolean\.rc_mock_power_[a-zA-Z0-9_]+", power_text)
    assert offenders == [], (
        "roamcore_power.yaml still references the mock inverter/shore booleans: "
        f"{offenders}."
    )


def test_no_input_select_rc_mock_power_references(power_text):
    offenders = re.findall(r"input_select\.rc_mock_power_[a-zA-Z0-9_]+", power_text)
    assert offenders == [], (
        "roamcore_power.yaml still references the mock inverter status select: "
        f"{offenders}."
    )


def test_required_rc_unique_ids_present(power_text):
    required = [
        "rc_power_battery_soc",
        "rc_power_solar_power",
        "rc_power_load_power",
        "rc_power_battery_voltage",
        "rc_power_battery_current",
        "rc_power_battery_power",
        "rc_power_ac_in_power",
        "rc_power_ac_out_power",
        "rc_power_inverter_status",
        "rc_power_shore_power_w",
        "rc_power_shore_connected",
    ]
    missing = [r for r in required if f"unique_id: {r}" not in power_text]
    assert not missing, f"missing required rc_* entity unique_ids: {missing}"


# 2. Banner entity exists, with canonical naming.
def test_banner_binary_sensor_unique_id(power_doc):
    ids = _unique_ids(power_doc)
    assert "rc_power_no_real_source" in ids, (
        f"expected unique_id `rc_power_no_real_source` in {POWER_YAML}, "
        f"found unique_ids: {sorted(ids)}"
    )


def test_banner_binary_sensor_name(power_doc):
    template = (power_doc.get("template") or [])
    names = []
    for block in template:
        for entry in (block.get("binary_sensor") or []):
            if entry.get("unique_id") == "rc_power_no_real_source":
                names.append(entry.get("name"))
    assert "RC Power No Real Source" in names, (
        f"expected binary_sensor named 'RC Power No Real Source', got {names}"
    )


def test_banner_binary_sensor_naming_pattern(power_text):
    assert RC_BANNER_ID in power_text, (
        f"expected canonical entity_id `{RC_BANNER_ID}` declared in package"
    )


def test_banner_binary_sensor_reacts_to_victron_not_mocks(power_doc):
    state_expr = _find_binary_sensor_state(power_doc, "rc_power_no_real_source")
    assert state_expr is not None, "rc_power_no_real_source binary_sensor missing"
    assert "input_number.rc_mock_power" not in state_expr, (
        "rc_power_no_real_source must not depend on dev mocks"
    )
    assert (
        "vt_battery_soc_percent" in state_expr
        or "vt_battery_voltage_v" in state_expr
        or "victron_battery_soc" in state_expr
    ), "rc_power_no_real_source must watch the canonical Victron sources"


# 3. Auto-recover state for "offline >5min".
def test_offline_checking_entity_exists(power_text):
    assert RC_OFFLINE_CHECKING_ID in power_text, (
        f"expected `{RC_OFFLINE_CHECKING_ID}` for the offline-checking auto-recover state"
    )


def test_offline_checking_uses_5min_threshold(power_doc):
    state_expr = _find_binary_sensor_state(power_doc, "rc_power_offline_checking")
    assert state_expr is not None, "rc_power_offline_checking binary_sensor missing"
    assert "300" in state_expr, (
        "rc_power_offline_checking must use the 5-minute (300s) threshold"
    )


def test_offline_checking_gates_on_no_real_source(power_doc):
    state_expr = _find_binary_sensor_state(power_doc, "rc_power_offline_checking")
    assert state_expr is not None, "rc_power_offline_checking binary_sensor missing"
    assert "rc_power_no_real_source" in state_expr, (
        "rc_power_offline_checking must gate on rc_power_no_real_source"
    )
    assert "rc_system_power_backend_connected" in state_expr, (
        "rc_power_offline_checking must depend on the backend-connected last_changed"
    )


# 4. Plain-English status sensor with both banner strings.
def test_status_sensor_exists(power_text):
    assert RC_STATUS_ID in power_text, (
        f"expected `{RC_STATUS_ID}` to render the plain-English status string"
    )


def test_status_sensor_contains_banner_strings(power_doc):
    state_expr = _find_sensor_state(power_doc, "rc_power_source_status")
    assert state_expr is not None, "rc_power_source_status sensor missing"
    assert BANNER_NO_SOURCE in state_expr, (
        f"rc_power_source_status must surface `{BANNER_NO_SOURCE}`"
    )
    assert BANNER_OFFLINE_CHECKING in state_expr, (
        f"rc_power_source_status must surface `{BANNER_OFFLINE_CHECKING}`"
    )


def test_status_sensor_does_not_depend_on_dev_mocks(power_doc):
    state_expr = _find_sensor_state(power_doc, "rc_power_source_status")
    assert state_expr is not None, "rc_power_source_status sensor missing"
    assert "rc_mock_power" not in state_expr, (
        "rc_power_source_status must not depend on dev mocks"
    )


# 5. Dashboard wires the banner into a conditional card.
def test_dashboard_has_banner_card(dashboard_text):
    assert RC_BANNER_ID in dashboard_text, (
        f"native dashboard must reference `{RC_BANNER_ID}` in a conditional card"
    )
    assert BANNER_NO_SOURCE in dashboard_text, (
        f"native dashboard must show the plain-English string `{BANNER_NO_SOURCE}`"
    )


def test_dashboard_has_offline_checking_card(dashboard_text):
    assert RC_OFFLINE_CHECKING_ID in dashboard_text, (
        f"native dashboard must reference `{RC_OFFLINE_CHECKING_ID}`"
    )
    assert BANNER_OFFLINE_CHECKING in dashboard_text, (
        f"native dashboard must show the plain-English string `{BANNER_OFFLINE_CHECKING}`"
    )


def test_dashboard_banner_uses_conditional_card(dashboard_text):
    pattern = re.compile(
        r"type:\s*conditional[\s\S]*?rc_power_no_real_source",
    )
    assert pattern.search(dashboard_text), (
        "native dashboard must wrap the no-real-source banner in a `type: conditional` "
        "card keyed on `binary_sensor.rc_power_no_real_source`"
    )
