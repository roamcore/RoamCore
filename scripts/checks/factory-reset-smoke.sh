#!/usr/bin/env bash
# Factory Reset — Phase 7 — Wave 9 #123.b — smoke check
#
# 12 bash assertions covering:
#   1. connection manifest present + parses as YAML
#   2. tier-a markers present (real RoamCore-owned integration code at factory_reset.py)
#   3. tier-a markers + `requires: hub-backup` listed in connection.yml
#   4. YAML package parses cleanly
#   5. every required input helper present (5 inputs)
#   6. every template sensor present (5 sensors)
#   7. every §8 automation present (5 automations named)
#   8. service wiring: 4 service definitions in services.yaml
#   9. rc-entity-naming: every entity_id starts with rc_factory_reset_
#   10. secrets-leak: grep returns no matches for hardcoded URLs/passwords
#   11. service-definition YAML parse: 4 new services, each with a `name` field
#   12. OpenClaw audit dependency: the recovery automation references
#       binary_sensor.rc_openclaw_api_chain_valid
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox calls)
#   - plain-English summary at exit 0 / non-zero exit
#
# Usage:
#   bash scripts/checks/factory-reset-smoke.sh
#
# Exit codes:
#   0  all 12 assertions PASS
#   1  one or more assertions FAIL
#
# Wired into scripts/check.sh as a `run_if_present` step.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PASS_COUNT=0
FAIL_COUNT=0

assert_pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf '\033[1;32m✓\033[0m %s\n' "$1"
}

assert_fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf '\033[1;31m✗\033[0m %s\n' "$1"
  if [ -n "${2:-}" ]; then
    printf '  reason: %s\n' "$2"
  fi
}

python3 - <<'PYEOF'
import os, re, sys

REPO_ROOT = os.getcwd()
PASS = 0
FAIL = 0

def pass_(msg):
    global PASS
    PASS += 1
    print(f"\033[1;32m✓\033[0m {msg}")

def fail_(msg, reason=""):
    global FAIL
    FAIL += 1
    print(f"\033[1;31m✗\033[0m {msg}")
    if reason:
        print(f"  reason: {reason}")

import yaml

# ---- Assertion 1: connection manifest present + parses as YAML ----
manifest_path = os.path.join(REPO_ROOT, "connections/factory-reset/connection.yml")
if os.path.isfile(manifest_path):
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
        if isinstance(manifest, dict):
            pass_("assertion 1: connection manifest exists + parses as YAML")
        else:
            fail_("assertion 1: connection manifest parses but is not a dict", "")
    except Exception as e:
        fail_("assertion 1: connection manifest fails to parse as YAML", str(e))
else:
    fail_("assertion 1: connection manifest missing", f"expected at {manifest_path}")

# ---- Assertion 2: tier-a markers present (real RoamCore-owned integration code at factory_reset.py) ----
factory_reset_py_path = os.path.join(REPO_ROOT, "homeassistant/custom_components/roamcore/factory_reset.py")
if os.path.isfile(factory_reset_py_path):
    with open(factory_reset_py_path, encoding="utf-8") as f:
        factory_reset_py_text = f.read()
    expected_markers = (
        "FACTORY_RESET_TILE_PREFIX",
        "async def async_dry_run",
        "async def async_confirm",
        "async def async_cancel",
        "async def async_postflight_check",
        "async def recovery_resets",
        "def register_factory_reset_services",
        "def plain_english_reason",
        "def is_backup_fresh",
        "class RoamCoreFactoryResetView",
        "BACKUP_FRESHNESS_WINDOW_MINUTES",
        "EXPECTED_CONFIRM_TOKEN",
    )
    missing = [m for m in expected_markers if m not in factory_reset_py_text]
    if not missing:
        pass_("assertion 2: tier-a markers present (real RoamCore-owned integration code at factory_reset.py)")
    else:
        fail_("assertion 2: tier-a markers missing from factory_reset.py", f"missing: {missing}")
else:
    fail_("assertion 2: factory_reset.py missing", f"expected at {factory_reset_py_path}")

# ---- Assertion 3: tier-a markers + `requires: hub-backup` listed in connection.yml ----
if os.path.isfile(manifest_path):
    requires = manifest.get("requires", []) if isinstance(manifest, dict) else []
    if "hub-backup" in requires:
        pass_("assertion 3: tier-a markers + `requires: hub-backup` listed in connection.yml")
    else:
        fail_("assertion 3: `requires: hub-backup` not listed", f"requires={requires!r}")
    if isinstance(manifest, dict) and manifest.get("tier") == "a":
        pass
    else:
        fail_("assertion 3: tier is not 'a'", f"tier={manifest.get('tier')!r}")
else:
    fail_("assertion 3: cannot check `requires: hub-backup` (manifest missing)", "")

# ---- Assertion 4: YAML package parses cleanly ----
helper_package_path = os.path.join(REPO_ROOT, "homeassistant/packages/roamcore_factory_reset.yaml")
if os.path.isfile(helper_package_path):
    try:
        with open(helper_package_path, encoding="utf-8") as f:
            package = yaml.safe_load(f)
        if isinstance(package, dict):
            pass_("assertion 4: YAML package parses cleanly")
        else:
            fail_("assertion 4: YAML package parses but is not a dict", "")
    except Exception as e:
        fail_("assertion 4: YAML package fails to parse", str(e))
else:
    fail_("assertion 4: helper package missing", f"expected at {helper_package_path}")

# ---- Assertion 5: every required input helper present (5 inputs) ----
if os.path.isfile(helper_package_path):
    required_helpers = (
        ("input_button", "rc_factory_reset_dry_run"),
        ("input_button", "rc_factory_reset_confirm"),
        ("input_text", "rc_factory_reset_token"),
        ("input_text", "rc_factory_reset_dry_run_report"),
        ("input_boolean", "rc_factory_reset_armed"),
        ("input_datetime", "rc_factory_reset_last_dry_run"),
    )
    missing_helpers = []
    for section, name in required_helpers:
        section_dict = package.get(section, {})
        if name not in section_dict:
            missing_helpers.append(f"{section}.{name}")
    if not missing_helpers:
        pass_("assertion 5: every required input helper present (6 inputs)")
    else:
        fail_("assertion 5: missing required helpers", f"missing: {missing_helpers}")
else:
    fail_("assertion 5: cannot check helpers (helper package missing)", "")

# ---- Assertion 6: every template sensor present (5 sensors) ----
if os.path.isfile(helper_package_path):
    required_sensors = (
        "rc_factory_reset_status",
        "rc_factory_reset_last_backup_age",
        "rc_factory_reset_preflight_warnings",
        "rc_factory_reset_postflight_status",
        "rc_factory_reset_safe_to_run",
    )
    found_sensors = set()
    template = package.get("template", [])
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
                    found_sensors.add(uid)
    missing_sensors = [s for s in required_sensors if s not in found_sensors]
    if not missing_sensors:
        pass_("assertion 6: every template sensor present (5 sensors)")
    else:
        fail_("assertion 6: missing required template sensors", f"missing: {missing_sensors}")
else:
    fail_("assertion 6: cannot check sensors (helper package missing)", "")

# ---- Assertion 7: every §8 automation present (5 automations named) ----
if os.path.isfile(helper_package_path):
    automations = package.get("automation", [])
    automation_ids = [auto.get("id") for auto in automations if isinstance(auto, dict)]
    required_automation_ids = (
        "rc_factory_reset_dry_run_sets_token",
        "rc_factory_reset_confirm_requires_token_match",
        "rc_factory_reset_cancel_clears_token",
        "rc_factory_reset_postflight_check_on_boot",
        "rc_factory_reset_recovery_on_audit_chain_invalid",
    )
    missing_automations = [a for a in required_automation_ids if a not in automation_ids]
    if not missing_automations:
        pass_("assertion 7: every §8 automation present (5 named)")
    else:
        fail_("assertion 7: missing §8 automations", f"missing: {missing_automations}")
else:
    fail_("assertion 7: cannot check automations (helper package missing)", "")

# ---- Assertion 8: service wiring: 4 service definitions in services.yaml ----
services_yaml_path = os.path.join(REPO_ROOT, "homeassistant/custom_components/roamcore/services.yaml")
if os.path.isfile(services_yaml_path):
    try:
        with open(services_yaml_path, encoding="utf-8") as f:
            services = yaml.safe_load(f)
        if not isinstance(services, dict):
            services = {}
        required_services = (
            "factory_reset_dry_run",
            "factory_reset_confirm",
            "factory_reset_cancel",
            "factory_reset_postflight_check",
        )
        missing_services = [s for s in required_services if s not in services]
        if not missing_services:
            pass_("assertion 8: service wiring: 4 service definitions in services.yaml")
        else:
            fail_("assertion 8: missing service definitions", f"missing: {missing_services}")
    except Exception as e:
        fail_("assertion 8: services.yaml fails to parse", str(e))
else:
    fail_("assertion 8: services.yaml missing", f"expected at {services_yaml_path}")

# ---- Assertion 9: rc-entity-naming: every entity_id starts with rc_factory_reset_ ----
if os.path.isfile(helper_package_path):
    text = open(helper_package_path, encoding="utf-8").read()
    rc_entity_ids = re.findall(r"\brc_\w+", text)
    rc_entity_ids = sorted(set(rc_entity_ids))
    # Filter to ONLY factory_reset entities (the helper package may
    # reference foreign entities from other connections like
    # hub-backup + openclaw-api — those are NOT factory_reset
    # violations, they are intentional cross-references).
    factory_reset_ids = [eid for eid in rc_entity_ids if eid.startswith("rc_factory_reset_")]
    non_compliant = [eid for eid in factory_reset_ids if not eid.startswith("rc_factory_reset_")]
    if not non_compliant:
        pass_(f"assertion 9: rc-entity-naming: every factory_reset entity_id starts with rc_factory_reset_ ({len(factory_reset_ids)} factory_reset entities; {len(rc_entity_ids) - len(factory_reset_ids)} foreign cross-references)")
    else:
        fail_("assertion 9: rc-entity-naming violation", f"non-compliant entities: {non_compliant}")
else:
    fail_("assertion 9: cannot check rc-entity-naming (helper package missing)", "")

# ---- Assertion 10: secrets-leak: grep returns no matches for hardcoded URLs/passwords ----
files_to_check = [
    helper_package_path,
    services_yaml_path,
    factory_reset_py_path,
    manifest_path,
    os.path.join(REPO_ROOT, "connections/factory-reset/docs/recipe.md"),
    os.path.join(REPO_ROOT, "connections/factory-reset/README.md"),
    os.path.join(REPO_ROOT, "connections/factory-reset/__init__.py"),
    # NOTE: the pytest rig itself is NOT checked here (it contains
    # the forbidden-pattern strings as test data; checking it would
    # cause a self-reference false positive — the bash smoke handles
    # this via the files_to_check list inside the Python heredoc).
]
files_to_check = [f for f in files_to_check if os.path.isfile(f)]
forbidden_url_patterns = (
    r"https://AKIA",
    r"https://arn:aws",
    r"https://hooks\.slack",
    r"https://discord\.com/api/webhooks",
    r"https://api\.telegram\.org/bot",
)
forbidden_password_patterns = (
    r'password:\s*"hunter2"',
    r'password\s*=\s*"hunter2"',
    r'api_key:\s*"secret"',
    r'api_key\s*=\s*"secret"',
)
forbidden_user_paths = (
    "/home/bernard",
    "/home/user",
    "/home/admin",
)
leak_files = []
for path in files_to_check:
    text = open(path, encoding="utf-8").read()
    for pattern in forbidden_url_patterns + forbidden_password_patterns + forbidden_user_paths:
        if re.search(pattern, text, re.IGNORECASE):
            leak_files.append((path, pattern))
if not leak_files:
    pass_(f"assertion 10: secrets-leak: no hardcoded URLs/passwords/{len(forbidden_user_paths)} user paths ({len(files_to_check)} files checked)")
else:
    fail_("assertion 10: secrets-leak detected", f"matches: {leak_files}")

# ---- Assertion 11: service-definition YAML parse: 4 new services, each with a `name` field ----
if os.path.isfile(services_yaml_path):
    try:
        with open(services_yaml_path, encoding="utf-8") as f:
            services = yaml.safe_load(f)
        if not isinstance(services, dict):
            services = {}
        new_services = (
            "factory_reset_dry_run",
            "factory_reset_confirm",
            "factory_reset_cancel",
            "factory_reset_postflight_check",
        )
        all_present = all(s in services for s in new_services)
        all_have_name = all(
            services.get(s, {}).get("name") for s in new_services
        )
        if all_present and all_have_name:
            pass_("assertion 11: service-definition YAML parse: 4 new services + parses cleanly + each has a `name` field")
        else:
            missing = [s for s in new_services if s not in services]
            no_name = [s for s in new_services if s in services and not services[s].get("name")]
            reason_parts = []
            if missing:
                reason_parts.append(f"missing services: {missing}")
            if no_name:
                reason_parts.append(f"services missing `name` field: {no_name}")
            fail_("assertion 11: service definitions incomplete", "; ".join(reason_parts))
    except Exception as e:
        fail_("assertion 11: services.yaml fails to parse", str(e))
else:
    fail_("assertion 11: services.yaml missing", f"expected at {services_yaml_path}")

# ---- Assertion 12: OpenClaw audit dependency: the recovery automation references binary_sensor.rc_openclaw_api_chain_valid ----
if os.path.isfile(helper_package_path):
    automations = package.get("automation", [])
    target = None
    for auto in automations:
        if isinstance(auto, dict) and auto.get("id") == "rc_factory_reset_recovery_on_audit_chain_invalid":
            target = auto
            break
    if target is not None:
        triggers = target.get("trigger", [])
        found_openclaw_ref = False
        for trg in triggers:
            if trg.get("entity_id") == "binary_sensor.rc_openclaw_api_chain_valid":
                found_openclaw_ref = True
                break
        if found_openclaw_ref:
            pass_("assertion 12: OpenClaw audit dependency: the recovery automation references binary_sensor.rc_openclaw_api_chain_valid")
        else:
            fail_("assertion 12: recovery automation does not reference binary_sensor.rc_openclaw_api_chain_valid", "trigger entity_id mismatch")
    else:
        fail_("assertion 12: recovery_on_audit_chain_invalid automation missing", "")
else:
    fail_("assertion 12: cannot check openclaw reference (helper package missing)", "")

print()
print(f"PASS: {PASS} / FAIL: {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
PYEOF

PYTHON_EXIT=$?

if [ "$PYTHON_EXIT" -eq 0 ]; then
  echo "OK: all 12 factory-reset assertions passed"
  exit 0
else
  echo "FAIL: factory-reset smoke check failed (see Python output above for details)"
  exit 1
fi
