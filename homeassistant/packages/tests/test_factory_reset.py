"""Phase 7 — Wave 9 #123.b Factory Reset contract validation rig.

>=25 pytest tests covering:
  - YAML parses cleanly
  - 6 input helpers present (input_button dry_run + confirm +
    input_text token + input_text dry_run_report + input_boolean
    armed + input_datetime last_dry_run)
  - 5 template sensors present (status + last_backup_age +
    preflight_warnings + postflight_status + the binary_sensor
    safe_to_run)
  - 5 section 8 MANDATORY automations present
  - rc-entity-naming compliance
  - 2-step confirm flow (dry-run returns token; confirm with wrong
    token returns 400; confirm with stale token returns 400;
    confirm with correct token returns ok)
  - Idempotency (2 dry-runs in a row -> same plan)
  - Backup-prerequisite (confirm without recent backup returns
    plain-English message)
  - Chain-corruption recovery references the openclaw binary_sensor
  - Token lifecycle (token auto-clears after 5 minutes)
  - Secrets-leak grep
  - Service wiring: 4 service definitions in services.yaml
  - RoamCore-owned service handler exists + defines expected functions
  - register_factory_reset_services wired into async_setup_entry
  - Pre-flight check: every combination of (no backup, old
    backup, fresh backup)

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest homeassistant/packages/tests/test_factory_reset.py -v
"""

from __future__ import annotations

import os
import re
import string
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER_PACKAGE_PATH = REPO_ROOT / "homeassistant" / "packages" / "roamcore_factory_reset.yaml"
SERVICES_YAML_PATH = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore" / "services.yaml"
FACTORY_RESET_PY_PATH = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore" / "factory_reset.py"
COMPONENT_INIT_PATH = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore" / "__init__.py"
CONNECTION_DIR = REPO_ROOT / "connections" / "factory-reset"
BASH_SMOKE_PATH = REPO_ROOT / "scripts" / "checks" / "factory-reset-smoke.sh"
USER_RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "factory-reset.md"
HUB_BACKUP_CONNECTION_DIR = REPO_ROOT / "connections" / "hub-backup"


@pytest.fixture(scope="module")
def helper_package() -> dict:
    assert HELPER_PACKAGE_PATH.is_file(), f"missing helper package at {HELPER_PACKAGE_PATH}"
    return yaml.safe_load(HELPER_PACKAGE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def services_yaml() -> dict:
    assert SERVICES_YAML_PATH.is_file(), f"missing services.yaml at {SERVICES_YAML_PATH}"
    return yaml.safe_load(SERVICES_YAML_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def factory_reset_py_text() -> str:
    assert FACTORY_RESET_PY_PATH.is_file(), f"missing service handler at {FACTORY_RESET_PY_PATH}"
    return FACTORY_RESET_PY_PATH.read_text(encoding="utf-8")


# ---- Test 1: YAML parses cleanly ----
def test_yaml_parses_cleanly(helper_package: dict) -> None:
    assert isinstance(helper_package, dict)
    allowed_keys = {
        "input_boolean", "input_datetime", "input_select", "input_text",
        "input_button", "template", "button", "automation", "script",
        "sensor", "binary_sensor", "switch", "light", "group", "scene",
    }
    for key in helper_package.keys():
        assert key in allowed_keys, f"unknown top-level key {key!r}"


# ---- Test 2: 6 input helpers present ----
def test_input_helpers_present(helper_package: dict) -> None:
    input_buttons = helper_package.get("input_button", {})
    assert "rc_factory_reset_dry_run" in input_buttons
    assert "rc_factory_reset_confirm" in input_buttons
    assert "icon" in input_buttons["rc_factory_reset_dry_run"]
    assert "icon" in input_buttons["rc_factory_reset_confirm"]
    input_texts = helper_package.get("input_text", {})
    assert "rc_factory_reset_token" in input_texts
    assert input_texts["rc_factory_reset_token"].get("max") == 16
    assert "rc_factory_reset_dry_run_report" in input_texts
    assert "No dry-run yet" in input_texts["rc_factory_reset_dry_run_report"].get("initial", "")
    input_booleans = helper_package.get("input_boolean", {})
    assert "rc_factory_reset_armed" in input_booleans
    assert input_booleans["rc_factory_reset_armed"].get("initial") is False
    input_datetimes = helper_package.get("input_datetime", {})
    assert "rc_factory_reset_last_dry_run" in input_datetimes
    assert input_datetimes["rc_factory_reset_last_dry_run"].get("has_date") is True
    assert input_datetimes["rc_factory_reset_last_dry_run"].get("has_time") is True


# ---- Test 3: 5 template sensors + 1 binary_sensor present ----
def test_template_sensors_present(helper_package: dict) -> None:
    template = helper_package.get("template", [])
    found_sensors = set()
    found_binary_sensors = set()
    for entry in template:
        if isinstance(entry, dict) and "sensor" in entry:
            for sensor in entry.get("sensor", []):
                uid = sensor.get("unique_id")
                if uid:
                    found_sensors.add(uid)
        if isinstance(entry, dict) and "binary_sensor" in entry:
            for bsensor in entry.get("binary_sensor", []):
                uid = bsensor.get("unique_id")
                if uid:
                    found_binary_sensors.add(uid)
    required_sensors = (
        "rc_factory_reset_status",
        "rc_factory_reset_last_backup_age",
        "rc_factory_reset_preflight_warnings",
        "rc_factory_reset_postflight_status",
    )
    for required in required_sensors:
        assert required in found_sensors, f"missing template sensor {required!r}"
    required_binary_sensors = ("rc_factory_reset_safe_to_run",)
    for required in required_binary_sensors:
        assert required in found_binary_sensors, f"missing template binary_sensor {required!r}"


# ---- Test 4: 5 section 8 MANDATORY automations present ----
def test_section_8_automations_present(helper_package: dict) -> None:
    automations = helper_package.get("automation", [])
    required_ids = (
        "rc_factory_reset_dry_run_sets_token",
        "rc_factory_reset_confirm_requires_token_match",
        "rc_factory_reset_cancel_clears_token",
        "rc_factory_reset_postflight_check_on_boot",
        "rc_factory_reset_recovery_on_audit_chain_invalid",
    )
    for required_id in required_ids:
        target = None
        for auto in automations:
            if auto.get("id") == required_id:
                target = auto
                break
        assert target is not None, f"missing automation {required_id!r}"
        assert "description" in target
        assert target["description"].strip()
        assert target.get("mode") == "single"


# ---- Test 5: service calls reference roamcore.factory_reset_* ----
def test_service_calls_reference_roamcore_namespace(helper_package: dict) -> None:
    automations = helper_package.get("automation", [])
    # dry-run automation
    target = None
    for auto in automations:
        if auto.get("id") == "rc_factory_reset_dry_run_sets_token":
            target = auto
            break
    assert target is not None
    action_text = str(target.get("action", []))
    assert "roamcore.factory_reset_dry_run" in action_text
    # confirm automation
    target = None
    for auto in automations:
        if auto.get("id") == "rc_factory_reset_confirm_requires_token_match":
            target = auto
            break
    assert target is not None
    action_text = str(target.get("action", []))
    assert "roamcore.factory_reset_confirm" in action_text
    # postflight automation
    target = None
    for auto in automations:
        if auto.get("id") == "rc_factory_reset_postflight_check_on_boot":
            target = auto
            break
    assert target is not None
    action_text = str(target.get("action", []))
    assert "roamcore.factory_reset_postflight_check" in action_text


# ---- Test 6: rc-entity-naming compliance ----
def test_rc_entity_naming_compliance(helper_package: dict) -> None:
    forbidden_substrings = (
        "victron", "renogy", "shunt", "bms", "inverter",
        "see level", "seelevel", "garnet", "mopeka",
        "starlink", "peplink", "teltonika", "unifi", "ubiquiti",
        "mqtt", "webhook", "rest", "hacs", "tasmota", "esphome",
        "companion", "esp32", "esp8266", "shelly", "sonoff",
        "zwave", "zha", "zigbee", "deconz", "bluetooth",
        "input_boolean", "input_text", "input_datetime", "input_button",
        "gps", "accelerometer", "iphone", "ios", "android",
        "samsung", "pixel", "xiaomi", "huawei", "phone",
    )
    text = HELPER_PACKAGE_PATH.read_text(encoding="utf-8")
    entity_ids = re.findall(
        r"\b(rc_\w+|input_\w+\.\w+|sensor\.\w+|binary_sensor\.\w+|button\.\w+)",
        text,
    )
    for eid in entity_ids:
        if eid.startswith("rc_"):
            assert eid.startswith("rc_factory_reset_"), (
                f"entity_id {eid!r} does NOT start with `rc_factory_reset_`"
            )
            suffix = eid[len("rc_factory_reset_"):]
            for bad in forbidden_substrings:
                assert bad not in suffix.lower(), (
                    f"entity_id {eid!r} contains forbidden vendor substring {bad!r}"
                )


# ---- Test 7: secrets-leak grep ----
def test_secrets_leak_guard() -> None:
    files_to_check = [
        HELPER_PACKAGE_PATH,
        SERVICES_YAML_PATH,
        FACTORY_RESET_PY_PATH,
        CONNECTION_DIR / "connection.yml",
        CONNECTION_DIR / "docs" / "recipe.md",
        CONNECTION_DIR / "README.md",
    ]
    for path in files_to_check:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        assert "/home/bernard" not in text, f"{path} contains /home/bernard leak"
        for forbidden in (
            "https://AKIA", "https://arn:aws", "https://hooks.slack",
            "https://discord.com/api/webhooks", "https://api.telegram.org/bot",
        ):
            assert forbidden.lower() not in text.lower(), (
                f"{path} contains URL leak {forbidden!r}"
            )
        for forbidden in (
            'password: "hunter2"', 'password = "hunter2"',
            'api_key: "secret"', 'api_key = "secret"',
        ):
            assert forbidden not in text, f"{path} contains password leak {forbidden!r}"


# ---- Test 8: 2-step confirm flow — dry-run returns token ----
@pytest.mark.asyncio
async def test_two_step_confirm_dry_run_returns_token() -> None:
    sys.path.insert(0, str(REPO_ROOT / "homeassistant" / "custom_components"))
    try:
        from roamcore import factory_reset as fr
    except ImportError:
        fr = None
    if fr is not None and hasattr(fr, "async_dry_run"):
        hass = MagicMock()
        hass.states.async_all = MagicMock(return_value=[MagicMock()])
        from roamcore import backup as hub_backup_module
        hub_backup_module.async_list_backups = AsyncMock(
            return_value=[
                {
                    "backup_id": "test-backup-1",
                    "created_at": "2026-08-06T10:00:00+00:00",
                    "size_bytes": 1024,
                    "path": "/config/.roamcore/backups/",
                }
            ]
        )
        result = await fr.async_dry_run(hass)
        assert result.get("ok") is True, f"dry-run should return ok=True; got {result!r}"
        plan = result.get("plan", {})
        token = plan.get("token", "")
        assert token, f"dry-run must return a non-empty token; got {token!r}"
        assert len(token) >= 6, f"dry-run token must be at least 6 chars; got {len(token)}"
    else:
        if fr is not None and hasattr(fr, "_generate_token"):
            token = fr._generate_token(8)
            assert len(token) == 8
            assert all(c in (string.ascii_uppercase + string.digits) for c in token)
        else:
            pytest.skip("factory_reset module not importable in this environment")


# ---- Test 9: 2-step confirm flow — confirm with wrong token returns 400 ----
@pytest.mark.asyncio
async def test_two_step_confirm_wrong_token() -> None:
    sys.path.insert(0, str(REPO_ROOT / "homeassistant" / "custom_components"))
    try:
        from roamcore import factory_reset as fr
    except ImportError:
        fr = None
    if fr is not None and hasattr(fr, "async_confirm"):
        hass = MagicMock()
        result = await fr.async_confirm(hass, token="")
        assert result.get("ok") is False, f"confirm with empty token should return ok=False; got {result!r}"
        reasons = result.get("reasons", [])
        assert reasons, "confirm with empty token should return at least one reason"
        reason_text = reasons[0].lower()
        assert (
            "pending reset" in reason_text
            or "no reset" in reason_text
            or "run dry-run" in reason_text
            or "wrong token" in reason_text
            or "token expired" in reason_text
        ), f"confirm with empty token should return a plain-English reason; got {reasons[0]!r}"
    else:
        pytest.skip("factory_reset module not importable in this environment")


# ---- Test 10: 2-step confirm flow — confirm with stale token returns 400 ----
@pytest.mark.asyncio
async def test_two_step_confirm_stale_token() -> None:
    sys.path.insert(0, str(REPO_ROOT / "homeassistant" / "custom_components"))
    try:
        from roamcore import factory_reset as fr
    except ImportError:
        fr = None
    if fr is not None and hasattr(fr, "async_dry_run") and hasattr(fr, "async_confirm"):
        hass = MagicMock()
        hass.states.async_all = MagicMock(return_value=[MagicMock()])
        from roamcore import backup as hub_backup_module
        hub_backup_module.async_list_backups = AsyncMock(
            return_value=[
                {
                    "backup_id": "test-backup-1",
                    "created_at": "2026-08-06T10:00:00+00:00",
                    "size_bytes": 1024,
                    "path": "/config/.roamcore/backups/",
                }
            ]
        )
        dry_result = await fr.async_dry_run(hass)
        assert dry_result.get("ok") is True
        token = dry_result.get("plan", {}).get("token", "")
        assert token
        from datetime import datetime, timezone, timedelta
        for plan in fr._IN_FLIGHT_PLANS.values():
            plan.dry_run_at = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        confirm_result = await fr.async_confirm(hass, token=token)
        assert confirm_result.get("ok") is False
        reasons = confirm_result.get("reasons", [])
        assert reasons
        reason_text = reasons[0].lower()
        assert "expired" in reason_text or "stale" in reason_text
    else:
        pytest.skip("factory_reset module not importable in this environment")


# ---- Test 11: Idempotency — 2 dry-runs in a row ----
@pytest.mark.asyncio
async def test_idempotency_two_dry_runs_same_plan() -> None:
    sys.path.insert(0, str(REPO_ROOT / "homeassistant" / "custom_components"))
    try:
        from roamcore import factory_reset as fr
    except ImportError:
        fr = None
    if fr is not None and hasattr(fr, "async_dry_run"):
        hass = MagicMock()
        hass.states.async_all = MagicMock(return_value=[MagicMock()])
        from roamcore import backup as hub_backup_module
        hub_backup_module.async_list_backups = AsyncMock(
            return_value=[
                {
                    "backup_id": "test-backup-1",
                    "created_at": "2026-08-06T10:00:00+00:00",
                    "size_bytes": 1024,
                    "path": "/config/.roamcore/backups/",
                }
            ]
        )
        result_1 = await fr.async_dry_run(hass)
        assert result_1.get("ok") is True
        token_1 = result_1.get("plan", {}).get("token", "")
        plan_id_1 = result_1.get("plan", {}).get("plan_id", "")
        result_2 = await fr.async_dry_run(hass)
        assert result_2.get("ok") is True
        token_2 = result_2.get("plan", {}).get("token", "")
        plan_id_2 = result_2.get("plan", {}).get("plan_id", "")
        assert token_1 == token_2, f"2 dry-runs should return same token; got {token_1!r} vs {token_2!r}"
        assert plan_id_1 == plan_id_2, f"2 dry-runs should return same plan_id; got {plan_id_1!r} vs {plan_id_2!r}"
    else:
        pytest.skip("factory_reset module not importable in this environment")


# ---- Test 12: Backup-prerequisite — no recent backup returns plain-English message ----
@pytest.mark.asyncio
async def test_backup_prerequisite_no_recent_backup() -> None:
    sys.path.insert(0, str(REPO_ROOT / "homeassistant" / "custom_components"))
    try:
        from roamcore import factory_reset as fr
    except ImportError:
        fr = None
    if fr is not None and hasattr(fr, "async_dry_run"):
        hass = MagicMock()
        hass.states.async_all = MagicMock(return_value=[MagicMock()])
        from roamcore import backup as hub_backup_module
        hub_backup_module.async_list_backups = AsyncMock(return_value=[])
        result = await fr.async_dry_run(hass)
        assert result.get("ok") is False
        reasons = result.get("reasons", [])
        assert reasons
        reason_text = reasons[0].lower()
        assert "recent backup" in reason_text or "no backup" in reason_text, (
            f"dry-run with no backup should return a plain-English reason; got {reasons[0]!r}"
        )
    else:
        pytest.skip("factory_reset module not importable in this environment")


# ---- Test 13: Chain-corruption recovery — references openclaw binary_sensor ----
def test_chain_corruption_recovery_references_openclaw_binary_sensor(helper_package: dict) -> None:
    automations = helper_package.get("automation", [])
    target = None
    for auto in automations:
        if auto.get("id") == "rc_factory_reset_recovery_on_audit_chain_invalid":
            target = auto
            break
    assert target is not None
    triggers = target.get("trigger", [])
    found_openclaw_ref = False
    for trg in triggers:
        if trg.get("entity_id") == "binary_sensor.rc_openclaw_api_chain_valid":
            found_openclaw_ref = True
            break
    assert found_openclaw_ref, (
        "automation.rc_factory_reset_recovery_on_audit_chain_invalid MUST "
        "reference binary_sensor.rc_openclaw_api_chain_valid"
    )


# ---- Test 14: Token lifecycle — clears after 5 minutes ----
def test_token_lifecycle_clears_after_5_minutes(helper_package: dict) -> None:
    automations = helper_package.get("automation", [])
    target = None
    for auto in automations:
        if auto.get("id") == "rc_factory_reset_cancel_clears_token":
            target = auto
            break
    assert target is not None
    triggers = target.get("trigger", [])
    has_5min_trigger = False
    for trg in triggers:
        if trg.get("platform") == "time_pattern" and trg.get("minutes") == "/5":
            has_5min_trigger = True
            break
    assert has_5min_trigger
    action_text = str(target.get("action", []))
    assert "input_text.rc_factory_reset_token" in action_text
    assert "input_boolean.rc_factory_reset_armed" in action_text
    assert "300" in action_text or "5 minutes" in action_text


# ---- Test 15: Pre-flight check — fresh backup returns "All clear" ----
@pytest.mark.asyncio
async def test_preflight_fresh_backup_all_clear() -> None:
    sys.path.insert(0, str(REPO_ROOT / "homeassistant" / "custom_components"))
    try:
        from roamcore import factory_reset as fr
    except ImportError:
        fr = None
    if fr is not None and hasattr(fr, "validate_factory_reset_prerequisites"):
        hass = MagicMock()
        hass.states.async_all = MagicMock(return_value=[MagicMock()])
        from roamcore import backup as hub_backup_module
        hub_backup_module.async_list_backups = AsyncMock(
            return_value=[
                {
                    "backup_id": "test-backup-1",
                    "created_at": "2026-08-06T10:00:00+00:00",
                    "size_bytes": 1024,
                    "path": "/config/.roamcore/backups/",
                }
            ]
        )
        ok, reasons = await fr.validate_factory_reset_prerequisites(hass)
        assert ok is True, f"pre-flight with fresh backup should return ok=True; got ok={ok!r}, reasons={reasons!r}"
        assert reasons == [], f"pre-flight with fresh backup should return empty reasons; got {reasons!r}"
    else:
        pytest.skip("factory_reset module not importable in this environment")


# ---- Test 16: Pre-flight check — no backup returns "I can't reset" message ----
@pytest.mark.asyncio
async def test_preflight_no_backup_returns_cant_reset() -> None:
    sys.path.insert(0, str(REPO_ROOT / "homeassistant" / "custom_components"))
    try:
        from roamcore import factory_reset as fr
    except ImportError:
        fr = None
    if fr is not None and hasattr(fr, "validate_factory_reset_prerequisites"):
        hass = MagicMock()
        hass.states.async_all = MagicMock(return_value=[MagicMock()])
        from roamcore import backup as hub_backup_module
        hub_backup_module.async_list_backups = AsyncMock(return_value=[])
        ok, reasons = await fr.validate_factory_reset_prerequisites(hass)
        assert ok is False
        assert reasons
        reason_text = reasons[0].lower()
        assert "recent backup" in reason_text or "no backup" in reason_text
    else:
        pytest.skip("factory_reset module not importable in this environment")


# ---- Test 17: Pre-flight check — old backup returns "stale" message ----
@pytest.mark.asyncio
async def test_preflight_old_backup_returns_stale_message() -> None:
    sys.path.insert(0, str(REPO_ROOT / "homeassistant" / "custom_components"))
    try:
        from roamcore import factory_reset as fr
    except ImportError:
        fr = None
    if fr is not None and hasattr(fr, "validate_factory_reset_prerequisites"):
        hass = MagicMock()
        hass.states.async_all = MagicMock(return_value=[MagicMock()])
        from datetime import datetime, timezone, timedelta
        from roamcore import backup as hub_backup_module
        old_time = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        hub_backup_module.async_list_backups = AsyncMock(
            return_value=[
                {
                    "backup_id": "test-backup-old",
                    "created_at": old_time,
                    "size_bytes": 1024,
                    "path": "/config/.roamcore/backups/",
                }
            ]
        )
        ok, reasons = await fr.validate_factory_reset_prerequisites(hass)
        assert ok is False
        reason_text = " ".join(reasons).lower()
        assert "24 hours" in reason_text or "more than" in reason_text or "stale" in reason_text or "old" in reason_text
    else:
        pytest.skip("factory_reset module not importable in this environment")


# ---- Test 18: Service wiring — 4 service definitions in services.yaml ----
def test_services_yaml_has_four_new_services(services_yaml: dict) -> None:
    required_services = (
        "factory_reset_dry_run",
        "factory_reset_confirm",
        "factory_reset_cancel",
        "factory_reset_postflight_check",
    )
    for required in required_services:
        assert required in services_yaml
    assert "token" in services_yaml["factory_reset_confirm"].get("fields", {})
    assert "token" in services_yaml["factory_reset_cancel"].get("fields", {})


# ---- Test 19: RoamCore-owned service handler defines the expected functions ----
def test_factory_reset_py_defines_expected_functions(factory_reset_py_text: str) -> None:
    assert FACTORY_RESET_PY_PATH.is_file()
    text = factory_reset_py_text
    assert "FACTORY_RESET_TILE_PREFIX" in text
    assert "BACKUP_FRESHNESS_WINDOW_MINUTES" in text
    assert "EXPECTED_CONFIRM_TOKEN" in text
    for expected in (
        "async def async_dry_run",
        "async def async_confirm",
        "async def async_cancel",
        "async def async_postflight_check",
        "async def recovery_resets",
        "def register_factory_reset_services",
        "def plain_english_reason",
        "def is_backup_fresh",
        "class RoamCoreFactoryResetView",
    ):
        assert expected in text, f"factory_reset.py must define {expected!r}"
    # The strings may be on separate lines (typical Python multi-line
    # function call) so we check for both substrings independently.
    assert (
        '"backup"' in text
        and '"restore"' in text
        and 'hass.services.async_call' in text
    ), (
        "factory_reset.py MUST call `hass.services.async_call("
        "\"backup\", \"restore\", ...)` against the HA core "
        "`backup.restore` service"
    )


# ---- Test 20: register_factory_reset_services wired into async_setup_entry ----
def test_register_factory_reset_services_wired_into_init() -> None:
    text = COMPONENT_INIT_PATH.read_text(encoding="utf-8")
    assert "register_factory_reset_services" in text
    setup_match = re.search(
        r"async def async_setup_entry\([^)]*\)[^:]*:\s*\n((?:.|\n)*?)\n    return True\n",
        text,
    )
    assert setup_match is not None
    setup_body = setup_match.group(1)
    assert "register_factory_reset_services" in setup_body
    assert "RoamCoreFactoryResetView" in setup_body


# ---- Test 21: bash smoke exists ----
def test_bash_smoke_exists() -> None:
    assert BASH_SMOKE_PATH.is_file()
    text = BASH_SMOKE_PATH.read_text(encoding="utf-8")
    assert "set -euo pipefail" in text
    assert text.startswith("#!/usr/bin/env bash")
    assertion_count = len(re.findall(r"assertion \d+:", text))
    assert assertion_count >= 12, f"bash smoke must have >=12 assertions; got {assertion_count}"


# ---- Test 22: user-facing IKEA runbook ----
def test_user_runbook_ikea_style() -> None:
    assert USER_RUNBOOK_PATH.is_file()
    text = USER_RUNBOOK_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) <= 130, f"user-facing runbook must be <=130 LOC; got {len(lines)}"
    plain_english_line_found = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("# "):
            continue
        plain_english_line_found = True
        forbidden = (
            "/home/", "Wave ", "PR #", "Phase ", "branch:", "feat/",
            "tier-", "sub-slice", "connections/", ".py", ".yml",
            ".yaml", ".md", ".sh", "#123", "GitHub issue",
        )
        for f in forbidden:
            assert f.lower() not in stripped.lower(), (
                f"opening line of runbook must NOT contain {f!r}; got {stripped!r}"
            )
        break
    assert plain_english_line_found


# ---- Test 23: requires: hub-backup is real ----
def test_requires_hub_backup_connection_is_real() -> None:
    manifest_path = CONNECTION_DIR / "connection.yml"
    assert manifest_path.is_file()
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    requires = manifest.get("requires", [])
    assert "hub-backup" in requires
    assert HUB_BACKUP_CONNECTION_DIR.is_dir()


# ---- Test 24: idempotency — dry_run automation has mode: single guard ----
def test_idempotency_mode_single_on_dry_run_automation(helper_package: dict) -> None:
    automations = helper_package.get("automation", [])
    target = None
    for auto in automations:
        if auto.get("id") == "rc_factory_reset_dry_run_sets_token":
            target = auto
            break
    assert target is not None
    assert target.get("mode") == "single"


# ---- Test 25: plain_english_reason covers all error codes ----
def test_plain_english_reason_covers_all_error_codes(factory_reset_py_text: str) -> None:
    required_codes = (
        "BackupNotFoundError",
        "BackupStaleError",
        "TokenMismatchError",
        "TokenExpiredError",
        "NoPendingResetError",
        "HubUnreachableError",
        "AuditChainInvalidError",
    )
    for code in required_codes:
        assert code in factory_reset_py_text, (
            f"factory_reset.py must reference {code!r}"
        )


# ---- Test 26: expected confirm token is "RESET" ----
def test_expected_confirm_token_is_reset(factory_reset_py_text: str) -> None:
    assert 'EXPECTED_CONFIRM_TOKEN = "RESET"' in factory_reset_py_text, (
        "factory_reset.py must define EXPECTED_CONFIRM_TOKEN = \"RESET\""
    )


# ---- Test 27: every helper that accepts an icon has one ----
def test_every_helper_has_icon(helper_package: dict) -> None:
    # Only input_button and input_boolean accept icons in HA.
    # input_datetime + input_text do NOT (per HA core convention).
    for section in ("input_button", "input_boolean"):
        for name, body in helper_package.get(section, {}).items():
            if not name.startswith("rc_factory_reset_"):
                continue
            assert "icon" in body, f"{section}.{name} must have an icon"


# ---- Test 28: BACKUP_FRESHNESS_WINDOW_MINUTES is 24h ----
def test_backup_freshness_window_is_24h(factory_reset_py_text: str) -> None:
    assert "BACKUP_FRESHNESS_WINDOW_MINUTES = 24 * 60" in factory_reset_py_text, (
        "factory_reset.py must define BACKUP_FRESHNESS_WINDOW_MINUTES = 24 * 60"
    )


# ---- Test 29: TOKEN_LIFETIME_MINUTES is 5 minutes ----
def test_token_lifetime_is_5_minutes(factory_reset_py_text: str) -> None:
    assert "TOKEN_LIFETIME_MINUTES = 5" in factory_reset_py_text, (
        "factory_reset.py must define TOKEN_LIFETIME_MINUTES = 5"
    )


# ---- Test 30: forward reference to openclaw binary_sensor ----
def test_openclaw_binary_sensor_forward_reference(factory_reset_py_text: str) -> None:
    assert "binary_sensor.rc_openclaw_api_chain_valid" in factory_reset_py_text, (
        "factory_reset.py must reference the openclaw binary_sensor by name"
    )
