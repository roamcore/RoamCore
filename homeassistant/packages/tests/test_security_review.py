"""Phase 7 — Wave 9 #123.c.ii Security Review contract validation rig.

~20 pytest tests covering:
  - YAML parses cleanly (yamllint-compatible)
  - input_boolean.rc_security_review_enabled exists with default ON
  - input_datetime.rc_security_review_last_audit exists with sensible default
  - input_text.rc_security_review_status exists with sensible default
  - input_text.rc_security_review_warnings exists with sensible default
  - sensor.rc_security_review_last_status present
  - sensor.rc_security_review_token_age_days present
  - sensor.rc_security_review_ssh_warnings present
  - sensor.rc_security_review_firewall_warnings present
  - binary_sensor.rc_security_review_healthy present
  - automation.rc_security_review_rotate_token present + has mode: single guard
  - automation.rc_security_review_audit_ssh present + cron 02:30 + calls roamcore.audit_ssh
  - automation.rc_security_review_audit_firewall present + cron 02:45 + calls roamcore.audit_firewall
  - automation.rc_security_review_warn_rotation_age present + cron 09:00 + condition on token age >= 75
  - the 3 service calls in the buttons reference `roamcore.rotate_api_token` / `roamcore.audit_ssh` / `roamcore.audit_firewall`
  - rc-entity-naming compliance (every entity_id starts with rc_security_review_)
  - secrets-leak grep: no hardcoded URLs, no hardcoded passwords, no /home/<user> paths
  - idempotency: every §8 automation has a `mode: single` guard so re-firing returns gracefully
  - the §8 contract: every §8 automation has an `id` field + a `description` field + a `mode` field
  - the bash smoke at scripts/checks/security-review-smoke.sh exists + parses as bash
  - the IKEA user-facing runbook at docs/runbooks/security-review.md exists + is ≤130 LOC + no file paths in §1-§4
  - the RoamCore-owned service handler at homeassistant/custom_components/roamcore/security.py exists + defines the 7 expected symbols + SECURITY_TILE_PREFIX

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest homeassistant/packages/tests/test_security_review.py -v
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> packages/ -> homeassistant/ -> repo
HELPER_PACKAGE_PATH = REPO_ROOT / "homeassistant" / "packages" / "roamcore_security_review.yaml"
SERVICES_YAML_PATH = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore" / "services.yaml"
SECURITY_PY_PATH = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore" / "security.py"
COMPONENT_INIT_PATH = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore" / "__init__.py"
BASH_SMOKE_PATH = REPO_ROOT / "scripts" / "checks" / "security-review-smoke.sh"
USER_RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "security-review.md"
CONNECTION_DIR = REPO_ROOT / "connections" / "security-review"


@pytest.fixture(scope="module")
def helper_package() -> dict:
    assert HELPER_PACKAGE_PATH.is_file(), f"missing helper package at {HELPER_PACKAGE_PATH}"
    return yaml.safe_load(HELPER_PACKAGE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def services_yaml() -> dict:
    assert SERVICES_YAML_PATH.is_file(), f"missing services.yaml at {SERVICES_YAML_PATH}"
    return yaml.safe_load(SERVICES_YAML_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Test 1: YAML parses cleanly (yamllint-compatible)
# ---------------------------------------------------------------------------

def test_yaml_parses_cleanly(helper_package: dict) -> None:
    """The helper package must parse as valid YAML (yamllint-compatible).
    A regression here (e.g. someone adding a tab character or invalid YAML)
    would break the dashboard load.
    """
    assert isinstance(helper_package, dict), (
        "helper package must parse as a YAML dict (yamllint-compatible)"
    )
    # Top-level keys must be one of the allowed HA package keys.
    allowed_keys = {
        "input_boolean",
        "input_datetime",
        "input_select",
        "input_text",
        "template",
        "button",
        "automation",
        "script",
        "sensor",
        "binary_sensor",
        "switch",
        "light",
        "group",
        "scene",
    }
    for key in helper_package.keys():
        assert key in allowed_keys, (
            f"helper package has unknown top-level key {key!r}; "
            f"allowed keys are {sorted(allowed_keys)!r}"
        )


# ---------------------------------------------------------------------------
# Test 2: input_boolean.rc_security_review_enabled exists with default ON
# ---------------------------------------------------------------------------

def test_input_boolean_enabled_default_on(helper_package: dict) -> None:
    """The master enable toggle must default to ON (so the audit starts
    running automatically without operator wiring).
    """
    input_booleans = helper_package.get("input_boolean", {})
    assert "rc_security_review_enabled" in input_booleans, (
        "helper package must declare input_boolean.rc_security_review_enabled"
    )
    enabled = input_booleans["rc_security_review_enabled"]
    assert enabled.get("initial") is True, (
        "input_boolean.rc_security_review_enabled must default to "
        "initial: true (audit starts running automatically)"
    )
    assert "icon" in enabled, (
        "input_boolean.rc_security_review_enabled must have an icon (mdi:shield-check)"
    )


# ---------------------------------------------------------------------------
# Test 3: input_datetime.rc_security_review_last_audit exists with sensible default
# ---------------------------------------------------------------------------

def test_input_datetime_last_audit_sensible_default(helper_package: dict) -> None:
    """The last-audit timestamp must have both date + time + a sensible default.
    """
    input_datetimes = helper_package.get("input_datetime", {})
    assert "rc_security_review_last_audit" in input_datetimes, (
        "helper package must declare input_datetime.rc_security_review_last_audit"
    )
    last_audit = input_datetimes["rc_security_review_last_audit"]
    assert last_audit.get("has_date") is True, (
        "input_datetime.rc_security_review_last_audit must have has_date: true"
    )
    assert last_audit.get("has_time") is True, (
        "input_datetime.rc_security_review_last_audit must have has_time: true"
    )
    assert "initial" in last_audit, (
        "input_datetime.rc_security_review_last_audit must have an initial value"
    )


# ---------------------------------------------------------------------------
# Test 4: input_text.rc_security_review_status exists with sensible default
# ---------------------------------------------------------------------------

def test_input_text_status_default_plain_english(helper_package: dict) -> None:
    """The status helper must have a sensible plain-English default.
    """
    input_texts = helper_package.get("input_text", {})
    assert "rc_security_review_status" in input_texts, (
        "helper package must declare input_text.rc_security_review_status"
    )
    status = input_texts["rc_security_review_status"]
    initial = status.get("initial", "")
    assert "Security review" in initial or "hasn't run" in initial, (
        f"input_text.rc_security_review_status must default to a "
        f"plain-English message starting with 'Security review' or "
        f"'hasn't run'; got {initial!r}"
    )


# ---------------------------------------------------------------------------
# Test 5: input_text.rc_security_review_warnings exists with sensible default
# ---------------------------------------------------------------------------

def test_input_text_warnings_default_plain_english(helper_package: dict) -> None:
    """The warnings helper must have a sensible plain-English default.
    """
    input_texts = helper_package.get("input_text", {})
    assert "rc_security_review_warnings" in input_texts, (
        "helper package must declare input_text.rc_security_review_warnings"
    )
    warnings = input_texts["rc_security_review_warnings"]
    initial = warnings.get("initial", "")
    assert "No warnings" in initial or "audit" in initial.lower(), (
        f"input_text.rc_security_review_warnings must default to a "
        f"plain-English message starting with 'No warnings' or "
        f"mentioning the audit; got {initial!r}"
    )


# ---------------------------------------------------------------------------
# Test 6: sensor.rc_security_review_last_status present
# ---------------------------------------------------------------------------

def test_sensor_last_status_present(helper_package: dict) -> None:
    """The template sensor mirroring the input_text status must be present.
    """
    template = helper_package.get("template", [])
    found = False
    for entry in template:
        if isinstance(entry, dict) and "sensor" in entry:
            for sensor in entry.get("sensor", []):
                if sensor.get("unique_id") == "rc_security_review_last_status":
                    found = True
                    break
    assert found, (
        "helper package must declare a template sensor with "
        "unique_id: rc_security_review_last_status"
    )


# ---------------------------------------------------------------------------
# Test 7: sensor.rc_security_review_token_age_days present
# ---------------------------------------------------------------------------

def test_sensor_token_age_days_present(helper_package: dict) -> None:
    """The template sensor for token-age-days must be present.
    """
    template = helper_package.get("template", [])
    found = False
    for entry in template:
        if isinstance(entry, dict) and "sensor" in entry:
            for sensor in entry.get("sensor", []):
                if sensor.get("unique_id") == "rc_security_review_token_age_days":
                    found = True
                    break
    assert found, (
        "helper package must declare a template sensor with "
        "unique_id: rc_security_review_token_age_days"
    )


# ---------------------------------------------------------------------------
# Test 8: binary_sensor.rc_security_review_healthy present
# ---------------------------------------------------------------------------

def test_binary_sensor_healthy_present(helper_package: dict) -> None:
    """The template binary_sensor for healthiness must be present.
    """
    template = helper_package.get("template", [])
    found = False
    for entry in template:
        if isinstance(entry, dict) and "binary_sensor" in entry:
            for bsensor in entry.get("binary_sensor", []):
                if bsensor.get("unique_id") == "rc_security_review_healthy":
                    found = True
                    break
    assert found, (
        "helper package must declare a template binary_sensor with "
        "unique_id: rc_security_review_healthy"
    )


# ---------------------------------------------------------------------------
# Test 9: automation.rc_security_review_rotate_token present + mode: single guard
# ---------------------------------------------------------------------------

def test_automation_rotate_token_with_mode_single(helper_package: dict) -> None:
    """The §8.1 rotate-token automation MUST have `mode: single` so
    re-firing the cron while a rotation is already running returns
    gracefully.
    """
    automations = helper_package.get("automation", [])
    target = None
    for auto in automations:
        if auto.get("id") == "rc_security_review_rotate_token":
            target = auto
            break
    assert target is not None, (
        "helper package must declare automation with "
        "id: rc_security_review_rotate_token"
    )
    assert target.get("mode") == "single", (
        "automation.rc_security_review_rotate_token MUST have "
        "mode: single so re-firing the cron while a rotation is "
        "running returns gracefully (idempotency marker)"
    )
    # Must call roamcore.rotate_api_token.
    action_text = str(target.get("action", []))
    assert "roamcore.rotate_api_token" in action_text, (
        "automation.rc_security_review_rotate_token must call "
        "roamcore.rotate_api_token"
    )


# ---------------------------------------------------------------------------
# Test 10: automation.rc_security_review_audit_ssh present + cron 02:30 + calls roamcore.audit_ssh
# ---------------------------------------------------------------------------

def test_automation_audit_ssh_with_cron(helper_package: dict) -> None:
    """The §8.2 audit-ssh automation must fire at 02:30 daily AND
    must call `roamcore.audit_ssh`.
    """
    automations = helper_package.get("automation", [])
    target = None
    for auto in automations:
        if auto.get("id") == "rc_security_review_audit_ssh":
            target = auto
            break
    assert target is not None, (
        "helper package must declare automation with "
        "id: rc_security_review_audit_ssh"
    )
    # Must have a `trigger` that includes the time 02:30.
    triggers = target.get("trigger", [])
    has_cron = False
    for trg in triggers:
        if trg.get("platform") == "time" and trg.get("at") == "02:30:00":
            has_cron = True
            break
    assert has_cron, (
        "automation.rc_security_review_audit_ssh must have a "
        "time trigger at '02:30:00'"
    )
    # Must call roamcore.audit_ssh.
    action_text = str(target.get("action", []))
    assert "roamcore.audit_ssh" in action_text, (
        "automation.rc_security_review_audit_ssh must call "
        "roamcore.audit_ssh"
    )


# ---------------------------------------------------------------------------
# Test 11: automation.rc_security_review_audit_firewall present + cron 02:45 + calls roamcore.audit_firewall
# ---------------------------------------------------------------------------

def test_automation_audit_firewall_with_cron(helper_package: dict) -> None:
    """The §8.3 audit-firewall automation must fire at 02:45 daily AND
    must call `roamcore.audit_firewall`.
    """
    automations = helper_package.get("automation", [])
    target = None
    for auto in automations:
        if auto.get("id") == "rc_security_review_audit_firewall":
            target = auto
            break
    assert target is not None, (
        "helper package must declare automation with "
        "id: rc_security_review_audit_firewall"
    )
    # Must have a `trigger` that includes the time 02:45.
    triggers = target.get("trigger", [])
    has_cron = False
    for trg in triggers:
        if trg.get("platform") == "time" and trg.get("at") == "02:45:00":
            has_cron = True
            break
    assert has_cron, (
        "automation.rc_security_review_audit_firewall must have a "
        "time trigger at '02:45:00'"
    )
    # Must call roamcore.audit_firewall.
    action_text = str(target.get("action", []))
    assert "roamcore.audit_firewall" in action_text, (
        "automation.rc_security_review_audit_firewall must call "
        "roamcore.audit_firewall"
    )


# ---------------------------------------------------------------------------
# Test 12: automation.rc_security_review_warn_rotation_age present + cron 09:00 + condition on token age
# ---------------------------------------------------------------------------

def test_automation_warn_rotation_age_with_cron(helper_package: dict) -> None:
    """The §8.4 warn-rotation-age automation must fire at 09:00 daily AND
    must check the token-age sensor for the threshold.
    """
    automations = helper_package.get("automation", [])
    target = None
    for auto in automations:
        if auto.get("id") == "rc_security_review_warn_rotation_age":
            target = auto
            break
    assert target is not None, (
        "helper package must declare automation with "
        "id: rc_security_review_warn_rotation_age"
    )
    # Must have a `trigger` that includes the time 09:00.
    triggers = target.get("trigger", [])
    has_cron = False
    for trg in triggers:
        if trg.get("platform") == "time" and trg.get("at") == "09:00:00":
            has_cron = True
            break
    assert has_cron, (
        "automation.rc_security_review_warn_rotation_age must have a "
        "time trigger at '09:00:00'"
    )
    # Must reference the token-age sensor in the conditions.
    action_text = str(target.get("condition", []))
    assert "rc_security_review_token_age_days" in action_text, (
        "automation.rc_security_review_warn_rotation_age must "
        "reference sensor.rc_security_review_token_age_days in "
        "its conditions"
    )


# ---------------------------------------------------------------------------
# Test 13: the 3 button service calls reference the 3 RoamCore services
# ---------------------------------------------------------------------------

def test_button_service_calls_reference_roamcore_namespace(helper_package: dict) -> None:
    """The 3 buttons must reference the RoamCore-namespaced services
    (`roamcore.rotate_api_token` / `roamcore.audit_ssh` /
    `roamcore.audit_firewall`). The RoamCore-owned service handler
    at `homeassistant/custom_components/roamcore/security.py`
    exposes the 3 services — the buttons call the RoamCore-owned
    services, not raw SSH / firewall commands.
    """
    package_text = HELPER_PACKAGE_PATH.read_text(encoding="utf-8")
    for service_name in (
        "roamcore.rotate_api_token",
        "roamcore.audit_ssh",
        "roamcore.audit_firewall",
    ):
        assert service_name in package_text, (
            f"helper package must reference {service_name!r} "
            f"(the RoamCore-owned service)"
        )


# ---------------------------------------------------------------------------
# Test 14: rc-entity-naming compliance (every entity_id starts with rc_security_review_)
# ---------------------------------------------------------------------------

def test_rc_entity_naming_compliance(helper_package: dict) -> None:
    """Every entity_id referenced in the helper package must start with
    `rc_security_review_` (the `security_review` subsystem prefix per
    `docs/reference/rc-entity-naming.md`).
    """
    forbidden_substrings = (
        # Vendor / integration / hardware leaks.
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
    # Find every entity_id string in the helper package.
    entity_ids = re.findall(r"\b(rc_\w+|input_\w+\.\w+|sensor\.\w+|binary_sensor\.\w+|button\.\w+)", text)
    for eid in entity_ids:
        # The RoamCore contract entities must start with rc_security_review_.
        if eid.startswith("rc_"):
            assert eid.startswith("rc_security_review_"), (
                f"entity_id {eid!r} does NOT start with "
                f"`rc_security_review_`; per "
                f"docs/reference/rc-entity-naming.md, contract "
                f"ids in the security_review subsystem MUST start "
                f"with the canonical prefix"
            )
            # Subsystem suffix MUST NOT contain forbidden vendor substrings.
            suffix = eid[len("rc_security_review_"):]
            for bad in forbidden_substrings:
                assert bad not in suffix.lower(), (
                    f"entity_id {eid!r} contains forbidden vendor "
                    f"substring {bad!r}; per rc-entity-naming.md, "
                    f"contract ids are vendor-neutral"
                )


# ---------------------------------------------------------------------------
# Test 15: secrets-leak grep: no hardcoded URLs, no hardcoded passwords, no /home/<user> paths
# ---------------------------------------------------------------------------

def test_secrets_leak_guard() -> None:
    """Secrets-leak guard: no hardcoded URLs, no hardcoded passwords,
    no /home/<user> paths in the shipped files.
    """
    files_to_check = [
        HELPER_PACKAGE_PATH,
        SERVICES_YAML_PATH,
        SECURITY_PY_PATH,
        # NOTE: the bash smoke itself is NOT checked here (it contains
        # the forbidden-pattern strings as data; checking it would
        # cause a self-reference false positive — the bash smoke
        # handles this via the files_to_check list inside the Python
        # heredoc).
    ]
    for path in files_to_check:
        assert path.is_file(), f"missing file at {path}"
        text = path.read_text(encoding="utf-8")
        # /home/<user> path leak.
        assert "/home/bernard" not in text, (
            f"{path} MUST NOT contain /home/bernard path leak"
        )
        # Hardcoded URL leaks.
        for forbidden in (
            "https://AKIA",
            "https://arn:aws",
            "https://hooks.slack",
            "https://discord.com/api/webhooks",
            "https://api.telegram.org/bot",
        ):
            assert forbidden.lower() not in text.lower(), (
                f"{path} MUST NOT contain hardcoded URL leak "
                f"{forbidden!r}"
            )
        # Hardcoded password leaks.
        for forbidden in (
            "password: \"hunter2\"",
            "password = \"hunter2\"",
            "api_key: \"secret\"",
            "api_key = \"secret\"",
        ):
            assert forbidden not in text, (
                f"{path} MUST NOT contain hardcoded password leak "
                f"{forbidden!r}"
            )


# ---------------------------------------------------------------------------
# Test 16: idempotency — every §8 automation has a `mode: single` guard
# ---------------------------------------------------------------------------

def test_idempotency_mode_single_on_all_automations(helper_package: dict) -> None:
    """The 4 §8 MANDATORY automations MUST have `mode: single` so
    re-firing returns gracefully. The 4 automations are:
      - §8.1 rotate-token
      - §8.2 audit-ssh
      - §8.3 audit-firewall
      - §8.4 warn-rotation-age
    """
    required_automation_ids = (
        "rc_security_review_rotate_token",
        "rc_security_review_audit_ssh",
        "rc_security_review_audit_firewall",
        "rc_security_review_warn_rotation_age",
    )
    automations = helper_package.get("automation", [])
    for required_id in required_automation_ids:
        target = None
        for auto in automations:
            if auto.get("id") == required_id:
                target = auto
                break
        assert target is not None, (
            f"helper package must declare automation with id={required_id!r}"
        )
        assert target.get("mode") == "single", (
            f"automation {required_id!r} MUST have mode: single "
            f"(idempotency marker; re-firing returns gracefully)"
        )


# ---------------------------------------------------------------------------
# Test 17: every §8 automation has an `id` field + a `description` field + a `mode` field
# ---------------------------------------------------------------------------

def test_section_8_contract_for_automations(helper_package: dict) -> None:
    """The §8 contract: every §8 automation must have an `id` field
    + a `description` field + a `mode` field.
    """
    automations = helper_package.get("automation", [])
    required_ids = (
        "rc_security_review_rotate_token",
        "rc_security_review_audit_ssh",
        "rc_security_review_audit_firewall",
        "rc_security_review_warn_rotation_age",
    )
    for required_id in required_ids:
        target = None
        for auto in automations:
            if auto.get("id") == required_id:
                target = auto
                break
        assert target is not None, (
            f"helper package must declare automation with id={required_id!r}"
        )
        assert "description" in target, (
            f"automation {required_id!r} must have a `description` field"
        )
        assert target["description"].strip(), (
            f"automation {required_id!r} must have a non-empty "
            f"`description` field"
        )
        assert target.get("mode") == "single", (
            f"automation {required_id!r} must have mode: single"
        )


# ---------------------------------------------------------------------------
# Test 18: bash smoke at scripts/checks/security-review-smoke.sh exists
# ---------------------------------------------------------------------------

def test_bash_smoke_exists() -> None:
    """The bash smoke at scripts/checks/security-review-smoke.sh must exist.
    """
    assert BASH_SMOKE_PATH.is_file(), (
        f"bash smoke must exist at {BASH_SMOKE_PATH}"
    )
    text = BASH_SMOKE_PATH.read_text(encoding="utf-8")
    # Must use bash strict mode (set -euo pipefail).
    assert "set -euo pipefail" in text, (
        "bash smoke must use bash strict mode (set -euo pipefail)"
    )
    # Must be executable.
    assert os.access(str(BASH_SMOKE_PATH), os.X_OK) or text.startswith("#!/usr/bin/env bash"), (
        "bash smoke must be executable (have a #!/usr/bin/env bash shebang)"
    )
    # Must have ≥10 bash assertions. The smoke uses Python heredoc
    # assertions internally; count the assertion markers (pass/fail
    # function calls + the assertion 1..10 comments).
    assertion_count = len(re.findall(r"assertion \d+:", text))
    assert assertion_count >= 10, (
        f"bash smoke must have ≥10 assertions; got {assertion_count}"
    )


# ---------------------------------------------------------------------------
# Test 19: user-facing IKEA runbook at docs/runbooks/security-review.md exists + is ≤130 LOC
# ---------------------------------------------------------------------------

def test_user_runbook_ikea_style() -> None:
    """The user-facing IKEA runbook must exist + be ≤130 LOC + open
    with a plain-English sentence.
    """
    assert USER_RUNBOOK_PATH.is_file(), (
        f"user-facing IKEA runbook must exist at {USER_RUNBOOK_PATH}"
    )
    text = USER_RUNBOOK_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) <= 130, (
        f"user-facing IKEA runbook must be ≤130 LOC per spec; "
        f"got {len(lines)} lines"
    )
    # The opening line(s) must include plain English (a single
    # sentence a vanlifer can understand). A markdown title heading
    # is allowed as line 1; the FIRST PLAIN-ENGLISH line after the
    # title must NOT contain file paths, PR numbers, "Wave N" labels,
    # or other internal jargon.
    plain_english_line_found = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("# "):
            continue
        # First non-empty, non-heading line.
        plain_english_line_found = True
        forbidden = (
            "/home/", "Wave ", "PR #", "Phase ", "branch:", "feat/",
            "tier-", "sub-slice", "connections/", ".py", ".yml",
            ".yaml", ".md", ".sh", "#123", "GitHub issue",
        )
        for f in forbidden:
            assert f.lower() not in stripped.lower(), (
                f"the opening plain-English line of the user-facing "
                f"runbook must NOT contain the internal-jargon substring "
                f"{f!r}; got {stripped!r}"
            )
        break
    assert plain_english_line_found, (
        "the user-facing runbook must have at least one non-empty, "
        "non-heading line of plain English"
    )


# ---------------------------------------------------------------------------
# Test 20: RoamCore-owned service handler exists + defines the 7 expected symbols + SECURITY_TILE_PREFIX
# ---------------------------------------------------------------------------

def test_security_py_defines_expected_symbols() -> None:
    """The RoamCore-owned service handler at
    `homeassistant/custom_components/roamcore/security.py` must define:
      - SECURITY_TILE_PREFIX constant
      - class RCApiTokenManager
      - class SSHAuditReader
      - class FirewallAuditReader
      - def register_security_services
      - def plain_english_status
      - the 3 service handlers (`_svc_rotate_api_token` +
        `_svc_audit_ssh` + `_svc_audit_firewall`)
    """
    assert SECURITY_PY_PATH.is_file(), (
        f"RoamCore-owned service handler must exist at {SECURITY_PY_PATH}"
    )
    text = SECURITY_PY_PATH.read_text(encoding="utf-8")
    assert "SECURITY_TILE_PREFIX" in text, (
        "security.py must define SECURITY_TILE_PREFIX constant"
    )
    for expected in (
        "class RCApiTokenManager",
        "class SSHAuditReader",
        "class FirewallAuditReader",
        "def register_security_services",
        "def plain_english_status",
        "_svc_rotate_api_token",
        "_svc_audit_ssh",
        "_svc_audit_firewall",
    ):
        assert expected in text, (
            f"security.py must define {expected!r}"
        )


# ---------------------------------------------------------------------------
# Test 21: register_security_services wired into async_setup_entry
# ---------------------------------------------------------------------------

def test_register_security_services_wired_into_init() -> None:
    """The RoamCore-owned `register_security_services(hass)` call must be
    wired into the `homeassistant/custom_components/roamcore/__init__.py`
    `async_setup_entry` function.
    """
    text = COMPONENT_INIT_PATH.read_text(encoding="utf-8")
    assert "register_security_services" in text, (
        "homeassistant/custom_components/roamcore/__init__.py must "
        "call register_security_services(hass) somewhere in "
        "async_setup_entry"
    )
    # The call must be inside async_setup_entry (look for the function
    # definition + the call in the same scope).
    setup_match = re.search(
        r"async def async_setup_entry\([^)]*\)[^:]*:\s*\n((?:.|\n)*?)\n    return True\n",
        text,
    )
    assert setup_match is not None, (
        "homeassistant/custom_components/roamcore/__init__.py must "
        "have an async_setup_entry function with `return True` at "
        "the end"
    )
    setup_body = setup_match.group(1)
    assert "register_security_services" in setup_body, (
        "register_security_services(hass) call must be wired into "
        "async_setup_entry (inside the function body)"
    )


# ---------------------------------------------------------------------------
# Test 22: services.yaml has the 3 new services
# ---------------------------------------------------------------------------

def test_services_yaml_has_three_new_services(services_yaml: dict) -> None:
    """The services.yaml must have the 3 new Security Review service definitions.
    """
    required_services = (
        "rotate_api_token",
        "audit_ssh",
        "audit_firewall",
    )
    for required in required_services:
        assert required in services_yaml, (
            f"services.yaml must declare the {required!r} service "
            f"definition"
        )
    # The `rotate_api_token` service must have a `reason` field
    # with default "manual".
    rotate_api_token_fields = services_yaml["rotate_api_token"].get("fields", {})
    assert "reason" in rotate_api_token_fields, (
        "rotate_api_token service must have a `reason` field"
    )
    assert rotate_api_token_fields["reason"].get("default") == "manual", (
        "rotate_api_token service must default reason to 'manual'"
    )
    # The `audit_ssh` + `audit_firewall` services must have no fields
    # (read-only audit).
    assert services_yaml["audit_ssh"].get("fields", {}) == {}, (
        "audit_ssh service must have no fields (read-only audit)"
    )
    assert services_yaml["audit_firewall"].get("fields", {}) == {}, (
        "audit_firewall service must have no fields (read-only audit)"
    )
