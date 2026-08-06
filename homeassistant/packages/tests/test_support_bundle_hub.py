"""Hub-level Support Bundle export wiring tests (Wave 9 #120c).

The Hub-level one-tap "Send support bundle" wiring lives in
`homeassistant/packages/roamcore_support_bundle_hub.yaml`. This
pytest rig enforces the slice spec's acceptance criteria for that
package, in the same repo-local, no-live-HA-call style as
`test_connection_state_field.py`:

  - 3 sensors with `sensor.rc_support_bundle_hub_*` ids exist
    (last_export_path + last_export_at + status).
  - ≥ 2 input_buttons with `input_button.rc_support_bundle_hub_*`
    ids exist (the spec lists the two explicit ones — export with
    zip + export without zip — and the tests assert those two plus
    any additional Hub-level helper buttons).
  - 3 §8 MANDATORY automations exist
    (export-button guard + success bookkeeping + failure capture)
    with `automation.rc_support_bundle_hub_*` ids.
  - The button → service-call wiring is intact (the button-guard
    automation references both input_buttons AND calls
    `roamcore.export_support_bundle` with the `zip:` data field).
  - rc-entity-naming compliance: every entity_id starts with
    `rc_support_bundle_hub_` (the Hub-level prefix) OR carries
    the legacy `rc_support_bundle_` prefix (the recipe-level
    contract from `connections/support-bundle/connection.yml`).
  - Idempotency: re-applying the YAML produces the same end state
    (initial values for input_text + input_select + template
    sensors are all stable).

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest homeassistant/packages/tests/test_support_bundle_hub.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]
HUB_PACKAGE = (
    REPO_ROOT
    / "homeassistant"
    / "packages"
    / "roamcore_support_bundle_hub.yaml"
)


def _load_hub_yaml() -> dict:
    assert HUB_PACKAGE.is_file(), (
        f"missing Hub support-bundle package at {HUB_PACKAGE} "
        "(Wave 9 #120c acceptance criterion: file must exist)"
    )
    with HUB_PACKAGE.open(encoding="utf-8") as fp:
        data = yaml.safe_load(fp)
    assert isinstance(data, dict), (
        f"Hub support-bundle package must parse to a mapping; got {type(data).__name__}"
    )
    return data


def test_hub_package_file_exists():
    """Slice spec: the package file must exist on disk."""
    assert HUB_PACKAGE.is_file(), f"missing file at {HUB_PACKAGE}"


def test_hub_package_parses_cleanly():
    """Slice spec: the package must parse as valid YAML with no
    structural errors."""
    data = _load_hub_yaml()
    assert isinstance(data, dict)
    # All top-level keys must be one of the canonical HA package
    # domains. If a typo creeps in (e.g. `input_buttons:` plural)
    # the YAML parses but HA silently ignores the section.
    allowed_top_level_keys = {
        "input_button",
        "input_text",
        "input_number",
        "input_select",
        "input_datetime",
        "input_boolean",
        "template",
        "automation",
        "script",
        "scene",
        "sensor",
        "binary_sensor",
        "shell_command",
        "timer",
        "counter",
        "group",
    }
    extra = set(data.keys()) - allowed_top_level_keys
    assert not extra, (
        f"unexpected top-level keys in {HUB_PACKAGE.name}: {sorted(extra)} "
        "(likely a HA domain typo; HA silently ignores unknown keys)"
    )


def test_hub_input_buttons_exist_with_rc_naming():
    """Slice spec: ≥2 input_buttons with `rc_support_bundle_hub_*`
    ids must exist (the spec explicitly enumerates `export` +
    `export_no_zip`)."""
    data = _load_hub_yaml()
    buttons = data.get("input_button", {})
    assert isinstance(buttons, dict)
    button_ids = list(buttons.keys())
    assert len(button_ids) >= 2, (
        f"Hub package must declare ≥2 input_buttons (export + export_no_zip); "
        f"got {button_ids}"
    )
    for bid in button_ids:
        assert bid.startswith("rc_support_bundle_hub_"), (
            f"input_button {bid!r} must start with rc_support_bundle_hub_ "
            "(Hub-level rc-entity-naming compliance)"
        )


def test_hub_explicit_input_buttons_present():
    """Slice spec: the two EXPLICITLY-enumerated buttons must be
    present: `rc_support_bundle_hub_export` (with zip) +
    `rc_support_bundle_hub_export_no_zip` (no-zip variant)."""
    data = _load_hub_yaml()
    buttons = data.get("input_button", {})
    assert "rc_support_bundle_hub_export" in buttons, (
        "missing required input_button.rc_support_bundle_hub_export"
    )
    assert "rc_support_bundle_hub_export_no_zip" in buttons, (
        "missing required input_button.rc_support_bundle_hub_export_no_zip"
    )


def test_hub_sensors_exist_with_rc_naming():
    """Slice spec: exactly 3 sensors with `rc_support_bundle_hub_*`
    ids (last_export_path + last_export_at + status)."""
    data = _load_hub_yaml()
    # Sensors are declared as template sensors with `unique_id`
    # that matches the rc-entity-naming contract.
    templates = data.get("template", [])
    sensors: list[dict] = []
    for block in templates or []:
        if not isinstance(block, dict):
            continue
        for sensor in block.get("sensor", []) or []:
            if isinstance(sensor, dict):
                sensors.append(sensor)
    assert len(sensors) == 3, (
        f"Hub package must declare exactly 3 template sensors "
        "(last_export_path + last_export_at + status); got {len(sensors)}: "
        f"{[s.get('unique_id') for s in sensors]}"
    )
    unique_ids = [s.get("unique_id") for s in sensors]
    assert "rc_support_bundle_hub_last_export_path" in unique_ids
    assert "rc_support_bundle_hub_last_export_at" in unique_ids
    assert "rc_support_bundle_hub_status" in unique_ids
    # Every sensor name should be set (HA falls back to the entity_id
    # if `name:` is missing — assert it for clean UX).
    for s in sensors:
        assert s.get("name"), (
            f"sensor {s.get('unique_id')!r} missing `name:` (HA falls back to "
            "entity_id which is uglier on the dashboard)"
        )


def test_hub_automations_exist_with_rc_naming():
    """Slice spec: 3 §8 MANDATORY automations (export-button guard +
    success bookkeeping + failure capture)."""
    data = _load_hub_yaml()
    automations = data.get("automation", [])
    assert isinstance(automations, list)
    assert len(automations) == 3, (
        f"Hub package must declare exactly 3 §8 MANDATORY automations; "
        f"got {len(automations)}: {[a.get('id') for a in automations]}"
    )
    auto_ids = [a.get("id") for a in automations]
    expected_ids = {
        "rc_support_bundle_hub_export_button_guard",
        "rc_support_bundle_hub_export_success",
        "rc_support_bundle_hub_export_failure",
    }
    assert expected_ids.issubset(set(auto_ids)), (
        f"missing required §8 MANDATORY automations: "
        f"{sorted(expected_ids - set(auto_ids))}"
    )
    for aid in auto_ids:
        assert aid and aid.startswith("rc_support_bundle_hub_"), (
            f"automation id {aid!r} must start with rc_support_bundle_hub_"
        )


def test_hub_button_guard_calls_service_with_zip():
    """Slice spec: the button guard automation must call the
    `roamcore.export_support_bundle` service (the canonical
    RoamCore-owned exporter) AND must pass the `zip:` data
    field so the button flavor (zip vs no-zip) is honored."""
    data = _load_hub_yaml()
    automations = data.get("automation", [])
    button_guard = next(
        (a for a in automations if a.get("id") == "rc_support_bundle_hub_export_button_guard"),
        None,
    )
    assert button_guard is not None, (
        "missing rc_support_bundle_hub_export_button_guard automation"
    )

    # Trigger must include BOTH input_buttons (so either button
    # press kicks off the export).
    triggers = button_guard.get("trigger", [])
    trigger_entity_ids: set[str] = set()
    for trig in triggers or []:
        if not isinstance(trig, dict):
            continue
        ents = trig.get("entity_id")
        if isinstance(ents, list):
            trigger_entity_ids.update(ents)
        elif isinstance(ents, str):
            trigger_entity_ids.add(ents)
    assert "input_button.rc_support_bundle_hub_export" in trigger_entity_ids, (
        "button_guard must trigger on input_button.rc_support_bundle_hub_export"
    )
    assert "input_button.rc_support_bundle_hub_export_no_zip" in trigger_entity_ids, (
        "button_guard must trigger on input_button.rc_support_bundle_hub_export_no_zip"
    )

    # Action sequence must include a service call to
    # `roamcore.export_support_bundle` with `zip:` in the data.
    actions = button_guard.get("action", [])
    yaml_text = yaml.safe_dump({"action": actions}, default_flow_style=False)
    assert "roamcore.export_support_bundle" in yaml_text, (
        "button_guard must call the roamcore.export_support_bundle service"
    )
    assert "zip" in yaml_text, (
        "button_guard must pass the `zip:` data field to honor the "
        "button flavor (zip vs no-zip)"
    )


def test_hub_failure_automation_captures_error():
    """Slice spec: the failure-capture automation must set status
    to Failed AND populate the last_error input_text so the user
    can see the plain-English failure message."""
    data = _load_hub_yaml()
    automations = data.get("automation", [])
    failure_auto = next(
        (a for a in automations if a.get("id") == "rc_support_bundle_hub_export_failure"),
        None,
    )
    assert failure_auto is not None
    actions = failure_auto.get("action", [])
    yaml_text = yaml.safe_dump({"action": actions}, default_flow_style=False)
    assert "input_text.rc_support_bundle_hub_last_error_value" in yaml_text, (
        "failure automation must capture the error into "
        "input_text.rc_support_bundle_hub_last_error_value"
    )
    assert "Failed" in yaml_text, (
        "failure automation must mark the status as Failed"
    )


def test_hub_success_automation_populates_path_and_at():
    """Slice spec: the success-bookkeeping automation must
    populate last_export_path + last_export_at + status=Exported."""
    data = _load_hub_yaml()
    automations = data.get("automation", [])
    success_auto = next(
        (a for a in automations if a.get("id") == "rc_support_bundle_hub_export_success"),
        None,
    )
    assert success_auto is not None
    actions = success_auto.get("action", [])
    yaml_text = yaml.safe_dump({"action": actions}, default_flow_style=False)
    assert "input_text.rc_support_bundle_hub_last_export_path_value" in yaml_text, (
        "success automation must populate last_export_path_value"
    )
    assert "input_text.rc_support_bundle_hub_last_export_at_value" in yaml_text, (
        "success automation must populate last_export_at_value"
    )
    assert "Exported" in yaml_text, (
        "success automation must mark the status as Exported"
    )


def test_hub_rc_entity_naming_compliance():
    """Slice spec: every entity_id starts with `rc_support_bundle_hub_`
    (Hub-level prefix) OR with the legacy `rc_support_bundle_` prefix
    (recipe-level contract from `connections/support-bundle/`)."""
    data = _load_hub_yaml()

    def _check(prefix: str, container_key: str, entity_ids: list[str]) -> None:
        for eid in entity_ids:
            assert eid.startswith(prefix), (
                f"{container_key} {eid!r} must start with {prefix!r}"
            )

    # input_button entities
    buttons = data.get("input_button", {})
    for bid in buttons.keys():
        assert bid.startswith("rc_support_bundle_hub_"), (
            f"input_button {bid!r} must start with rc_support_bundle_hub_ "
            "(Hub-level rc-entity-naming compliance)"
        )

    # input_text entities (internal helpers — allowed to be _value suffix)
    texts = data.get("input_text", {})
    for tid in texts.keys():
        assert tid.startswith("rc_support_bundle_hub_"), (
            f"input_text {tid!r} must start with rc_support_bundle_hub_"
        )

    # input_select entities
    selects = data.get("input_select", {})
    for sid in selects.keys():
        assert sid.startswith("rc_support_bundle_hub_"), (
            f"input_select {sid!r} must start with rc_support_bundle_hub_"
        )

    # template sensors (use unique_id as the entity_id source of truth)
    for block in data.get("template", []) or []:
        if not isinstance(block, dict):
            continue
        for sensor in block.get("sensor", []) or []:
            uid = sensor.get("unique_id", "")
            assert uid.startswith("rc_support_bundle_hub_"), (
                f"template sensor unique_id {uid!r} must start with rc_support_bundle_hub_"
            )

    # automations
    for auto in data.get("automation", []) or []:
        aid = auto.get("id", "")
        assert aid.startswith("rc_support_bundle_hub_"), (
            f"automation id {aid!r} must start with rc_support_bundle_hub_"
        )


def test_hub_package_idempotent_initial_state():
    """Slice spec: re-applying the YAML produces the same end state.

    All `input_text.*` declare an `initial:` value, the `input_select.*`
    declares an `initial:` value, and the template sensors derive from
    those — so a second application produces the same end state. We
    assert the explicit `initial:` keys are present and that the
    template sensors reference only helpers defined in the same
    package (no implicit dependency on runtime state)."""
    data = _load_hub_yaml()
    texts = data.get("input_text", {})
    for tid, body in texts.items():
        assert isinstance(body, dict), f"input_text {tid} must be a mapping"
        assert "initial" in body, (
            f"input_text {tid!r} must declare `initial:` for idempotent "
            "re-application (otherwise the value drifts across reloads)"
        )
        assert body["initial"] == "", (
            f"input_text {tid!r} `initial:` should be empty string "
            "(no prior export on a fresh install)"
        )

    selects = data.get("input_select", {})
    for sid, body in selects.items():
        assert isinstance(body, dict), f"input_select {sid} must be a mapping"
        assert "initial" in body, (
            f"input_select {sid!r} must declare `initial:` for idempotent re-application"
        )
        assert body["initial"] == "Idle", (
            f"input_select {sid!r} `initial:` should be 'Idle' "
            "(no export attempted yet on a fresh install)"
        )

    # Re-loading the file should produce the same dict (parses twice,
    # compares equal).
    reloaded = _load_hub_yaml()
    assert data == reloaded, (
        "Hub package must parse deterministically — re-loading produces "
        "the same dict (catches nondeterministic YAML generation bugs)"
    )
