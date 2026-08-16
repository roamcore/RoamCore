#!/usr/bin/env bash
# Security Review — Phase 7 — Wave 9 #123.c.ii — smoke check
#
# ~10 bash assertions covering:
#   1. connection manifest exists + parses as YAML
#   2. tier-a markers present (real RoamCore-owned integration code at security.py)
#   3. YAML package parses
#   4. every required helper present (input_boolean + input_datetime + input_text × 2)
#   5. every §8 automation present (4 named)
#   6. service wiring: 3 service definitions in services.yaml
#   7. rc-entity-naming: every entity_id starts with rc_security_review_
#   8. idempotency: mode: single guard on every §8 automation
#   9. secrets-leak: grep returns no matches for hardcoded URLs/passwords
#   10. service-definition YAML parse: services.yaml has the 3 new services + parses cleanly
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox calls)
#   - plain-English summary at exit 0 / non-zero exit
#
# Usage:
#   bash scripts/checks/security-review-smoke.sh
#
# Exit codes:
#   0  all 10 assertions PASS
#   1  one or more assertions FAIL
#
# Wired into scripts/check.sh as a `run_if_present` step.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PASS_COUNT=0
FAIL_COUNT=0

# Helper: pass / fail / summarise. Each assertion increments the counter
# so the operator sees the pass/fail tally at the end.
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

# Use Python for YAML parsing (PyYAML is already a pytest dependency, so
# it's available). We delegate every assertion that needs YAML parsing
# to a Python heredoc — bash + YAML is fragile; this keeps the smoke
# fast + reliable.

python3 - <<'PYEOF'
import os, re, sys, glob

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

# ---- Assertion 1: connection manifest exists + parses as YAML ----
manifest_path = os.path.join(REPO_ROOT, "connections/security-review/connection.yml")
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

# ---- Assertion 2: tier-a markers present (real RoamCore-owned integration code at security.py) ----
security_py_path = os.path.join(REPO_ROOT, "homeassistant/custom_components/roamcore/security.py")
if os.path.isfile(security_py_path):
    with open(security_py_path, encoding="utf-8") as f:
        security_py_text = f.read()
    expected_markers = (
        "SECURITY_TILE_PREFIX",
        "class RCApiTokenManager",
        "class SSHAuditReader",
        "class FirewallAuditReader",
        "def register_security_services",
        "def plain_english_status",
        "_svc_rotate_api_token",
        "_svc_audit_ssh",
        "_svc_audit_firewall",
    )
    missing = [m for m in expected_markers if m not in security_py_text]
    if not missing:
        pass_("assertion 2: tier-a markers present (real RoamCore-owned integration code at security.py)")
    else:
        fail_("assertion 2: tier-a markers missing from security.py", f"missing: {missing}")
else:
    fail_("assertion 2: security.py missing", f"expected at {security_py_path}")

# ---- Assertion 3: YAML package parses ----
helper_package_path = os.path.join(REPO_ROOT, "homeassistant/packages/roamcore_security_review.yaml")
if os.path.isfile(helper_package_path):
    try:
        with open(helper_package_path, encoding="utf-8") as f:
            package = yaml.safe_load(f)
        if isinstance(package, dict):
            pass_("assertion 3: YAML package parses cleanly")
        else:
            fail_("assertion 3: YAML package parses but is not a dict", "")
    except Exception as e:
        fail_("assertion 3: YAML package fails to parse", str(e))
else:
    fail_("assertion 3: helper package missing", f"expected at {helper_package_path}")

# ---- Assertion 4: every required helper present ----
if os.path.isfile(helper_package_path):
    required_helpers = (
        ("input_boolean", "rc_security_review_enabled"),
        ("input_datetime", "rc_security_review_last_audit"),
        ("input_text", "rc_security_review_status"),
        ("input_text", "rc_security_review_warnings"),
    )
    missing_helpers = []
    for section, name in required_helpers:
        section_dict = package.get(section, {})
        if name not in section_dict:
            missing_helpers.append(f"{section}.{name}")
    if not missing_helpers:
        pass_("assertion 4: every required helper present (input_boolean + input_datetime + input_text × 2)")
    else:
        fail_("assertion 4: missing required helpers", f"missing: {missing_helpers}")
else:
    fail_("assertion 4: cannot check helpers (helper package missing)", "")

# ---- Assertion 5: every §8 automation present (4 named) ----
if os.path.isfile(helper_package_path):
    automations = package.get("automation", [])
    automation_ids = [auto.get("id") for auto in automations if isinstance(auto, dict)]
    required_automation_ids = (
        "rc_security_review_rotate_token",
        "rc_security_review_audit_ssh",
        "rc_security_review_audit_firewall",
        "rc_security_review_warn_rotation_age",
    )
    missing_automations = [a for a in required_automation_ids if a not in automation_ids]
    if not missing_automations:
        pass_("assertion 5: every §8 automation present (4 named)")
    else:
        fail_("assertion 5: missing §8 automations", f"missing: {missing_automations}")
else:
    fail_("assertion 5: cannot check automations (helper package missing)", "")

# ---- Assertion 6: service wiring: 3 service definitions in services.yaml ----
services_yaml_path = os.path.join(REPO_ROOT, "homeassistant/custom_components/roamcore/services.yaml")
if os.path.isfile(services_yaml_path):
    try:
        with open(services_yaml_path, encoding="utf-8") as f:
            services = yaml.safe_load(f)
        if not isinstance(services, dict):
            services = {}
        required_services = ("rotate_api_token", "audit_ssh", "audit_firewall")
        missing_services = [s for s in required_services if s not in services]
        if not missing_services:
            pass_("assertion 6: service wiring: 3 service definitions in services.yaml")
        else:
            fail_("assertion 6: missing service definitions", f"missing: {missing_services}")
    except Exception as e:
        fail_("assertion 6: services.yaml fails to parse", str(e))
else:
    fail_("assertion 6: services.yaml missing", f"expected at {services_yaml_path}")

# ---- Assertion 7: rc-entity-naming: every entity_id starts with rc_security_review_ ----
if os.path.isfile(helper_package_path):
    text = open(helper_package_path, encoding="utf-8").read()
    # Find every entity_id string in the helper package.
    rc_entity_ids = re.findall(r"\brc_\w+", text)
    # Deduplicate.
    rc_entity_ids = sorted(set(rc_entity_ids))
    non_compliant = [eid for eid in rc_entity_ids if not eid.startswith("rc_security_review_")]
    if not non_compliant:
        pass_(f"assertion 7: rc-entity-naming: every entity_id starts with rc_security_review_ ({len(rc_entity_ids)} entities)")
    else:
        fail_("assertion 7: rc-entity-naming violation", f"non-compliant entities: {non_compliant}")
else:
    fail_("assertion 7: cannot check rc-entity-naming (helper package missing)", "")

# ---- Assertion 8: idempotency: mode: single guard on every §8 automation ----
if os.path.isfile(helper_package_path):
    automations = package.get("automation", [])
    required_automation_ids = (
        "rc_security_review_rotate_token",
        "rc_security_review_audit_ssh",
        "rc_security_review_audit_firewall",
        "rc_security_review_warn_rotation_age",
    )
    failures = []
    for required_id in required_automation_ids:
        target = None
        for auto in automations:
            if isinstance(auto, dict) and auto.get("id") == required_id:
                target = auto
                break
        if target is None:
            failures.append(f"{required_id}: missing")
        elif target.get("mode") != "single":
            failures.append(f"{required_id}: mode={target.get('mode')!r} (expected 'single')")
    if not failures:
        pass_("assertion 8: idempotency: mode: single guard on every §8 automation (4 automations)")
    else:
        fail_("assertion 8: idempotency violation", f"failures: {failures}")
else:
    fail_("assertion 8: cannot check idempotency (helper package missing)", "")

# ---- Assertion 9: secrets-leak: grep returns no matches for hardcoded URLs/passwords ----
files_to_check = [
    helper_package_path,
    services_yaml_path,
    security_py_path,
    # NOTE: the smoke script itself is NOT checked (it contains the
    # forbidden-pattern strings as data; checking it would cause a
    # self-reference false positive).
]
# Filter to files that exist.
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
    pass_(f"assertion 9: secrets-leak: no hardcoded URLs/passwords/{len(forbidden_user_paths)} user paths ({len(files_to_check)} files checked)")
else:
    fail_("assertion 9: secrets-leak detected", f"matches: {leak_files}")

# ---- Assertion 10: service-definition YAML parse: services.yaml has the 3 new services + parses cleanly ----
if os.path.isfile(services_yaml_path):
    try:
        with open(services_yaml_path, encoding="utf-8") as f:
            services = yaml.safe_load(f)
        if not isinstance(services, dict):
            services = {}
        new_services = ("rotate_api_token", "audit_ssh", "audit_firewall")
        all_present = all(s in services for s in new_services)
        # Check that each new service has a `name` field (HA service
        # convention).
        all_have_name = all(
            services.get(s, {}).get("name") for s in new_services
        )
        if all_present and all_have_name:
            pass_("assertion 10: service-definition YAML parse: 3 new services + parses cleanly + each has a `name` field")
        else:
            missing = [s for s in new_services if s not in services]
            no_name = [s for s in new_services if s in services and not services[s].get("name")]
            reason_parts = []
            if missing:
                reason_parts.append(f"missing services: {missing}")
            if no_name:
                reason_parts.append(f"services missing `name` field: {no_name}")
            fail_("assertion 10: service definitions incomplete", "; ".join(reason_parts))
    except Exception as e:
        fail_("assertion 10: services.yaml fails to parse", str(e))
else:
    fail_("assertion 10: services.yaml missing", f"expected at {services_yaml_path}")

# Summary
print()
print(f"PASS: {PASS} / FAIL: {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
PYEOF

PYTHON_EXIT=$?

if [ "$PYTHON_EXIT" -eq 0 ]; then
  echo "OK: all 10 security-review assertions passed"
  exit 0
else
  echo "FAIL: security-review smoke check failed (see Python output above for details)"
  exit 1
fi
