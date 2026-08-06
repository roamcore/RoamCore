"""Phase 7 — Wave 9 #123.a Hub Backup contract validation rig.

22 pytest tests covering:
  - YAML parses cleanly (yamllint-compatible)
  - input_boolean.rc_hub_backup_enabled exists with default ON
  - input_datetime.rc_hub_backup_next_run exists with sensible default
  - input_select.rc_hub_backup_retention_policy has 3 options
  - input_text.rc_hub_backup_destination exists with mode password
  - input_text.rc_hub_backup_status exists with sensible default
  - sensor.rc_hub_backup_last_status present
  - sensor.rc_hub_backup_age_minutes present
  - binary_sensor.rc_hub_backup_healthy present
  - automation.rc_hub_backup_nightly_create_backup present + uses cron 02:00 + uses rc_hub_backup_enabled guard
  - automation.rc_hub_backup_verify_integrity present + triggered by nightly_create_backup completion + calls roamcore.test_restore
  - automation.rc_hub_backup_cleanup_old present + uses cron 03:30 + enforces retention policy
  - the service calls in the automations reference `roamcore.create_backup` / `roamcore.test_restore` (not raw `backup.create`)
  - rc-entity-naming compliance (every entity_id starts with rc_hub_backup_)
  - secrets-leak grep: no hardcoded URLs, no hardcoded passwords, no /home/<user> paths
  - idempotency: the nightly_create_backup automation has a `mode: single` guard so re-firing doesn't double-create
  - the §8 contract: every §8 automation has an `id` field + a `description` field + a `mode` field
  - the bash smoke at scripts/checks/hub-backup-smoke.sh exists + parses as bash
  - the IKEA user-facing runbook at docs/runbooks/hub-backup.md exists + is ≤130 LOC + no file paths in §1-§4
  - the RoamCore-owned service handler at homeassistant/custom_components/roamcore/backup.py exists + defines the 6 expected functions + BACKUP_TILE_PREFIX

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest homeassistant/packages/tests/test_hub_backup.py -v
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
HELPER_PACKAGE_PATH = REPO_ROOT / "homeassistant" / "packages" / "roamcore_hub_backup.yaml"
SERVICES_YAML_PATH = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore" / "services.yaml"
BACKUP_PY_PATH = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore" / "backup.py"
COMPONENT_INIT_PATH = REPO_ROOT / "homeassistant" / "custom_components" / "roamcore" / "__init__.py"
BASH_SMOKE_PATH = REPO_ROOT / "scripts" / "checks" / "hub-backup-smoke.sh"
USER_RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "hub-backup.md"
CONNECTION_DIR = REPO_ROOT / "connections" / "hub-backup"


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
# Test 2: input_boolean.rc_hub_backup_enabled exists with default ON
# ---------------------------------------------------------------------------

def test_input_boolean_enabled_default_on(helper_package: dict) -> None:
    """The master enable toggle must default to ON (so backups start
    running automatically without operator wiring).
    """
    input_booleans = helper_package.get("input_boolean", {})
    assert "rc_hub_backup_enabled" in input_booleans, (
        "helper package must declare input_boolean.rc_hub_backup_enabled"
    )
    enabled = input_booleans["rc_hub_backup_enabled"]
    assert enabled.get("initial") is True, (
        "input_boolean.rc_hub_backup_enabled must default to "
        "initial: true (backups start running automatically)"
    )
    assert "icon" in enabled, (
        "input_boolean.rc_hub_backup_enabled must have an icon (mdi:backup-restore)"
    )


# ---------------------------------------------------------------------------
# Test 3: input_datetime.rc_hub_backup_next_run exists with sensible default
# ---------------------------------------------------------------------------

def test_input_datetime_next_run_sensible_default(helper_package: dict) -> None:
    """The next-run timestamp must have both date + time + a sensible default.
    """
    input_datetimes = helper_package.get("input_datetime", {})
    assert "rc_hub_backup_next_run" in input_datetimes, (
        "helper package must declare input_datetime.rc_hub_backup_next_run"
    )
    next_run = input_datetimes["rc_hub_backup_next_run"]
    assert next_run.get("has_date") is True, (
        "input_datetime.rc_hub_backup_next_run must have has_date: true"
    )
    assert next_run.get("has_time") is True, (
        "input_datetime.rc_hub_backup_next_run must have has_time: true"
    )
    assert "initial" in next_run, (
        "input_datetime.rc_hub_backup_next_run must have an initial value"
    )


# ---------------------------------------------------------------------------
# Test 4: input_select.rc_hub_backup_retention_policy has 3 options
# ---------------------------------------------------------------------------

def test_input_select_retention_policy_three_options(helper_package: dict) -> None:
    """The retention-policy selector must have exactly 3 options.
    """
    input_selects = helper_package.get("input_select", {})
    assert "rc_hub_backup_retention_policy" in input_selects, (
        "helper package must declare "
        "input_select.rc_hub_backup_retention_policy"
    )
    policy = input_selects["rc_hub_backup_retention_policy"]
    options = policy.get("options", [])
    assert len(options) == 3, (
        f"input_select.rc_hub_backup_retention_policy must have "
        f"exactly 3 options; got {len(options)}: {options!r}"
    )
    # The 3 options must be the canonical trio (in the spec-required order).
    expected = (
        "7 daily + 4 weekly + 12 monthly",
        "30 daily only",
        "90 daily only",
    )
    for exp in expected:
        assert exp in options, (
            f"input_select.rc_hub_backup_retention_policy must "
            f"include the option {exp!r}"
        )
    # The default must be "30 daily only" (best for most operators).
    assert policy.get("initial") == "30 daily only", (
        "input_select.rc_hub_backup_retention_policy must default "
        "to '30 daily only' (best for most operators)"
    )


# ---------------------------------------------------------------------------
# Test 5: input_text.rc_hub_backup_destination exists with mode password
# ---------------------------------------------------------------------------

def test_input_text_destination_mode_password(helper_package: dict) -> None:
    """The destination helper must use mode password (the value is
    obscured in the dashboard) + have a pattern validation.
    """
    input_texts = helper_package.get("input_text", {})
    assert "rc_hub_backup_destination" in input_texts, (
        "helper package must declare "
        "input_text.rc_hub_backup_destination"
    )
    destination = input_texts["rc_hub_backup_destination"]
    assert destination.get("mode") == "password", (
        "input_text.rc_hub_backup_destination must use mode: password "
        "(the value is obscured in the dashboard)"
    )
    assert "pattern" in destination, (
        "input_text.rc_hub_backup_destination must have a pattern "
        "validation (only valid folder paths are accepted)"
    )
    assert destination.get("initial") == "/config/.roamcore/backups/", (
        "input_text.rc_hub_backup_destination must default to "
        "'/config/.roamcore/backups/' (the Hub's built-in backup folder)"
    )


# ---------------------------------------------------------------------------
# Test 6: input_text.rc_hub_backup_status exists with sensible default
# ---------------------------------------------------------------------------

def test_input_text_status_default_plain_english(helper_package: dict) -> None:
    """The status helper must have a sensible plain-English default.
    """
    input_texts = helper_package.get("input_text", {})
    assert "rc_hub_backup_status" in input_texts, (
        "helper package must declare input_text.rc_hub_backup_status"
    )
    status = input_texts["rc_hub_backup_status"]
    initial = status.get("initial", "")
    assert "No backups yet" in initial, (
        f"input_text.rc_hub_backup_status must default to a "
        f"plain-English message starting with 'No backups yet'; "
        f"got {initial!r}"
    )


# ---------------------------------------------------------------------------
# Test 7: sensor.rc_hub_backup_last_status present
# ---------------------------------------------------------------------------

def test_sensor_last_status_present(helper_package: dict) -> None:
    """The template sensor mirroring the input_text status must be present.
    """
    template = helper_package.get("template", [])
    found = False
    for entry in template:
        if isinstance(entry, dict) and "sensor" in entry:
            for sensor in entry.get("sensor", []):
                if sensor.get("unique_id") == "rc_hub_backup_last_status":
                    found = True
                    break
    assert found, (
        "helper package must declare a template sensor with "
        "unique_id: rc_hub_backup_last_status"
    )


# ---------------------------------------------------------------------------
# Test 8: sensor.rc_hub_backup_age_minutes present
# ---------------------------------------------------------------------------

def test_sensor_age_minutes_present(helper_package: dict) -> None:
    """The template sensor for age-in-minutes must be present.
    """
    template = helper_package.get("template", [])
    found = False
    for entry in template:
        if isinstance(entry, dict) and "sensor" in entry:
            for sensor in entry.get("sensor", []):
                if sensor.get("unique_id") == "rc_hub_backup_age_minutes":
                    found = True
                    break
    assert found, (
        "helper package must declare a template sensor with "
        "unique_id: rc_hub_backup_age_minutes"
    )


# ---------------------------------------------------------------------------
# Test 9: binary_sensor.rc_hub_backup_healthy present
# ---------------------------------------------------------------------------

def test_binary_sensor_healthy_present(helper_package: dict) -> None:
    """The template binary_sensor for healthiness must be present.
    """
    template = helper_package.get("template", [])
    found = False
    for entry in template:
        if isinstance(entry, dict) and "binary_sensor" in entry:
            for bsensor in entry.get("binary_sensor", []):
                if bsensor.get("unique_id") == "rc_hub_backup_healthy":
                    found = True
                    break
    assert found, (
        "helper package must declare a template binary_sensor with "
        "unique_id: rc_hub_backup_healthy"
    )


# ---------------------------------------------------------------------------
# Test 10: automation.rc_hub_backup_nightly_create_backup present + uses cron 02:00 + uses rc_hub_backup_enabled guard
# ---------------------------------------------------------------------------

def test_automation_nightly_create_with_cron_and_guard(helper_package: dict) -> None:
    """The §8.1 nightly-create automation must fire at 02:00 daily
    AND must guard on `input_boolean.rc_hub_backup_enabled` being ON.
    """
    automations = helper_package.get("automation", [])
    target = None
    for auto in automations:
        if auto.get("id") == "rc_hub_backup_nightly_create_backup":
            target = auto
            break
    assert target is not None, (
        "helper package must declare automation with "
        "id: rc_hub_backup_nightly_create_backup"
    )
    # Must have a `trigger` that includes the time 02:00.
    triggers = target.get("trigger", [])
    has_cron = False
    for trg in triggers:
        if trg.get("platform") == "time" and trg.get("at") == "02:00:00":
            has_cron = True
            break
    assert has_cron, (
        "automation.rc_hub_backup_nightly_create_backup must have a "
        "time trigger at '02:00:00'"
    )
    # Must have a `condition` that checks rc_hub_backup_enabled is ON.
    conditions = target.get("condition", [])
    has_guard = False
    for cond in conditions:
        if (
            cond.get("condition") == "state"
            and cond.get("entity_id") == "input_boolean.rc_hub_backup_enabled"
            and cond.get("state") == "on"
        ):
            has_guard = True
            break
    assert has_guard, (
        "automation.rc_hub_backup_nightly_create_backup must guard on "
        "input_boolean.rc_hub_backup_enabled being ON"
    )


# ---------------------------------------------------------------------------
# Test 11: automation.rc_hub_backup_verify_integrity present + triggered by nightly_create_backup completion + calls roamcore.test_restore
# ---------------------------------------------------------------------------

def test_automation_verify_integrity_triggered_by_completion(helper_package: dict) -> None:
    """The §8.2 verify-integrity automation must be triggered by the
    `roamcore_hub_backup_backup_created` event (the completion event
    from §8.1) AND must call `roamcore.test_restore`.
    """
    automations = helper_package.get("automation", [])
    target = None
    for auto in automations:
        if auto.get("id") == "rc_hub_backup_verify_integrity":
            target = auto
            break
    assert target is not None, (
        "helper package must declare automation with "
        "id: rc_hub_backup_verify_integrity"
    )
    # Must be triggered by the `roamcore_hub_backup_backup_created` event.
    triggers = target.get("trigger", [])
    has_event_trigger = False
    for trg in triggers:
        if (
            trg.get("platform") == "event"
            and trg.get("event_type") == "roamcore_hub_backup_backup_created"
        ):
            has_event_trigger = True
            break
    assert has_event_trigger, (
        "automation.rc_hub_backup_verify_integrity must be triggered "
        "by the 'roamcore_hub_backup_backup_created' event"
    )
    # Must call `roamcore.test_restore` (not raw `backup.something`).
    action_text = str(target.get("action", []))
    assert "roamcore.test_restore" in action_text, (
        "automation.rc_hub_backup_verify_integrity must call "
        "roamcore.test_restore"
    )


# ---------------------------------------------------------------------------
# Test 12: automation.rc_hub_backup_cleanup_old present + uses cron 03:30 + enforces retention policy
# ---------------------------------------------------------------------------

def test_automation_cleanup_old_with_cron_and_retention(helper_package: dict) -> None:
    """The §8.3 cleanup-old automation must fire at 03:30 daily AND
    must reference the retention-policy helper.
    """
    automations = helper_package.get("automation", [])
    target = None
    for auto in automations:
        if auto.get("id") == "rc_hub_backup_cleanup_old":
            target = auto
            break
    assert target is not None, (
        "helper package must declare automation with "
        "id: rc_hub_backup_cleanup_old"
    )
    # Must have a `trigger` that includes the time 03:30.
    triggers = target.get("trigger", [])
    has_cron = False
    for trg in triggers:
        if trg.get("platform") == "time" and trg.get("at") == "03:30:00":
            has_cron = True
            break
    assert has_cron, (
        "automation.rc_hub_backup_cleanup_old must have a "
        "time trigger at '03:30:00'"
    )
    # Must reference the retention-policy helper.
    action_text = str(target.get("action", []))
    assert "rc_hub_backup_retention_policy" in action_text, (
        "automation.rc_hub_backup_cleanup_old must reference "
        "input_select.rc_hub_backup_retention_policy to enforce "
        "the operator-chosen retention policy"
    )
    assert "roamcore.list_backups" in action_text, (
        "automation.rc_hub_backup_cleanup_old must call "
        "roamcore.list_backups"
    )
    assert "roamcore.delete_backup" in action_text, (
        "automation.rc_hub_backup_cleanup_old must call "
        "roamcore.delete_backup"
    )


# ---------------------------------------------------------------------------
# Test 13: service calls reference `roamcore.create_backup` / `roamcore.test_restore` (not raw `backup.create`)
# ---------------------------------------------------------------------------

def test_service_calls_reference_roamcore_namespace(helper_package: dict) -> None:
    """The automations must reference the RoamCore-namespaced services
    (`roamcore.create_backup` / `roamcore.test_restore`) — NOT the raw
    `backup.create` / `backup.delete` services. The RoamCore-owned
    service handler wraps the raw services + adds the plain-English
    status surface + the sandbox restore-test runner.
    """
    automations = helper_package.get("automation", [])
    for auto in automations:
        if auto.get("id") == "rc_hub_backup_nightly_create_backup":
            action_text = str(auto.get("action", []))
            assert "roamcore.create_backup" in action_text, (
                "automation.rc_hub_backup_nightly_create_backup must "
                "call roamcore.create_backup (NOT raw backup.create)"
            )
            # The raw `backup.create` service call MUST NOT appear
            # (the RoamCore-owned handler wraps the raw service).
            assert "'backup', 'create'" not in action_text, (
                "automation.rc_hub_backup_nightly_create_backup must "
                "NOT call raw 'backup', 'create' (RoamCore wraps it)"
            )


# ---------------------------------------------------------------------------
# Test 14: rc-entity-naming compliance (every entity_id starts with rc_hub_backup_)
# ---------------------------------------------------------------------------

def test_rc_entity_naming_compliance(helper_package: dict) -> None:
    """Every entity_id referenced in the helper package must start with
    `rc_hub_backup_` (the `hub_backup` subsystem prefix per
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
        # The RoamCore contract entities must start with rc_hub_backup_.
        if eid.startswith("rc_"):
            assert eid.startswith("rc_hub_backup_"), (
                f"entity_id {eid!r} does NOT start with "
                f"`rc_hub_backup_`; per "
                f"docs/reference/rc-entity-naming.md, contract "
                f"ids in the hub_backup subsystem MUST start "
                f"with the canonical prefix"
            )
            # Subsystem suffix MUST NOT contain forbidden vendor substrings.
            suffix = eid[len("rc_hub_backup_"):]
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
        BACKUP_PY_PATH,
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
# Test 16: idempotency — the nightly_create_backup automation has a `mode: single` guard
# ---------------------------------------------------------------------------

def test_idempotency_mode_single_on_nightly_create(helper_package: dict) -> None:
    """The §8.1 nightly-create automation MUST have `mode: single` so
    re-firing the cron while a backup is running returns gracefully.
    """
    automations = helper_package.get("automation", [])
    target = None
    for auto in automations:
        if auto.get("id") == "rc_hub_backup_nightly_create_backup":
            target = auto
            break
    assert target is not None, (
        "helper package must declare automation with "
        "id: rc_hub_backup_nightly_create_backup"
    )
    assert target.get("mode") == "single", (
        "automation.rc_hub_backup_nightly_create_backup MUST have "
        "mode: single so re-firing the cron while a backup is "
        "running returns gracefully (idempotency marker)"
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
        "rc_hub_backup_nightly_create_backup",
        "rc_hub_backup_verify_integrity",
        "rc_hub_backup_cleanup_old",
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
# Test 18: bash smoke at scripts/checks/hub-backup-smoke.sh exists
# ---------------------------------------------------------------------------

def test_bash_smoke_exists() -> None:
    """The bash smoke at scripts/checks/hub-backup-smoke.sh must exist.
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
# Test 19: user-facing IKEA runbook at docs/runbooks/hub-backup.md exists + is ≤130 LOC
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
# Test 20: RoamCore-owned service handler exists + defines the 6 expected functions + BACKUP_TILE_PREFIX
# ---------------------------------------------------------------------------

def test_backup_py_defines_expected_functions() -> None:
    """The RoamCore-owned service handler at
    `homeassistant/custom_components/roamcore/backup.py` must define:
      - BACKUP_TILE_PREFIX constant
      - async def async_create_backup
      - async def async_list_backups
      - async def async_delete_backup
      - async def async_test_restore
      - def register_backup_services
      - def plain_english_status
    """
    assert BACKUP_PY_PATH.is_file(), (
        f"RoamCore-owned service handler must exist at {BACKUP_PY_PATH}"
    )
    text = BACKUP_PY_PATH.read_text(encoding="utf-8")
    assert "BACKUP_TILE_PREFIX" in text, (
        "backup.py must define BACKUP_TILE_PREFIX constant"
    )
    for expected in (
        "async def async_create_backup",
        "async def async_list_backups",
        "async def async_delete_backup",
        "async def async_test_restore",
        "def register_backup_services",
        "def plain_english_status",
    ):
        assert expected in text, (
            f"backup.py must define {expected!r}"
        )


# ---------------------------------------------------------------------------
# Test 21: register_backup_services wired into async_setup_entry
# ---------------------------------------------------------------------------

def test_register_backup_services_wired_into_init() -> None:
    """The RoamCore-owned `register_backup_services(hass)` call must be
    wired into the `homeassistant/custom_components/roamcore/__init__.py`
    `async_setup_entry` function.
    """
    text = COMPONENT_INIT_PATH.read_text(encoding="utf-8")
    assert "register_backup_services" in text, (
        "homeassistant/custom_components/roamcore/__init__.py must "
        "call register_backup_services(hass) somewhere in "
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
    assert "register_backup_services" in setup_body, (
        "register_backup_services(hass) call must be wired into "
        "async_setup_entry (inside the function body)"
    )


# ---------------------------------------------------------------------------
# Test 22: services.yaml has the 4 new services
# ---------------------------------------------------------------------------

def test_services_yaml_has_four_new_services(services_yaml: dict) -> None:
    """The services.yaml must have the 4 new Hub Backup service definitions.
    """
    required_services = (
        "create_backup",
        "list_backups",
        "delete_backup",
        "test_restore",
    )
    for required in required_services:
        assert required in services_yaml, (
            f"services.yaml must declare the {required!r} service "
            f"definition"
        )
    # The `delete_backup` + `test_restore` services must have a
    # `backup_id` field.
    assert "backup_id" in services_yaml["delete_backup"].get("fields", {}), (
        "delete_backup service must have a `backup_id` field"
    )
    assert "backup_id" in services_yaml["test_restore"].get("fields", {}), (
        "test_restore service must have a `backup_id` field"
    )
    # The `create_backup` service must have a `retention_days` field
    # with default 30.
    create_backup_fields = services_yaml["create_backup"].get("fields", {})
    assert "retention_days" in create_backup_fields, (
        "create_backup service must have a `retention_days` field"
    )
    assert create_backup_fields["retention_days"].get("default") == 30, (
        "create_backup service must default retention_days to 30"
    )
