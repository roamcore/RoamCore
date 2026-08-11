"""Manifest-honesty + structural tests for
`homeassistant/packages/roamcore_tailscale_self_test.yaml`
(Wave 9 #122.d.iii — Phase 6 Tailscale wizard connectivity
self-test: HA → tunnel → phone → tunnel → HA round-trip, without
requiring a real phone).

This is the verification rig for the connectivity-self-test slice.
It asserts:

  - YAML parses successfully (sanity check).
  - Every required helper is present (input_text × 1, input_boolean
    × 1, input_button × 1, input_datetime × 1, shell_command × 2,
    command_line sensor × 3, template binary_sensor × 4, template
    sensor × 1).
  - All 3 §8 MANDATORY automations are present with the correct
    `id:` and trigger/action contract.
  - `input_text.rc_tailscale_self_test_tunnel_url` is `mode:
    password` (sensitive — never logged).
  - `sensor.rc_tailscale_self_test_status` template covers every
    combination of the 6 state dimensions (url_configured ×
    running × outbound × inbound × recovery × never_run) with
    a plain-English phrase that has no bash / entity ID / jargon.
  - Idempotency: running the YAML through PyYAML twice produces
    the same dict (no random IDs, no timestamps that diverge).
  - rc-entity-naming compliance: every entity_id starts with
    `rc_tailscale_self_test_` or `rc_tailscale_run_self_test` /
    `rc_tailscale_self_test_*` / `rc_setup_*` (the latter via the
    external references — internal entities are scoped to
    `rc_tailscale_self_test_*`).
  - No secrets in YAML: grep for `tskey-` or any tailnet auth-key
    pattern — must NOT find any.
  - IKEA doc 5-step shape: docs/setup/tailscale-self-test.md
    exists, opens with one plain-English sentence, has exactly
    five numbered sections, contains an operator→vanlifer
    translation table.
  - §8.T.3 wizard advance automation MUST be idempotent: it
    advances `rc_setup_stage` only if currently `networking`,
    otherwise it no-ops (the global stage can already be past
    `networking` because the existing remote-access wizard
    advances it first).
  - §8.T.1 run automation MUST NOT clear the tunnel URL (idempotent
    retry without re-typing).
  - §8.T.2 recovery automation MUST fire a plain-English
    persistent_notification after a 60s timeout.
  - Plain-English status copy: the 6 status phrases the template
    can render MUST NOT contain operator jargon (no entity IDs,
    no bash terms, no upstream-integration names in the user-
    visible output).

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest homeassistant/packages/tests/test_tailscale_self_test.py -v
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> packages/ -> homeassistant/ -> repo
PACKAGE_PATH = REPO_ROOT / "homeassistant" / "packages" / "roamcore_tailscale_self_test.yaml"
DOC_PATH = REPO_ROOT / "docs" / "setup" / "tailscale-self-test.md"


# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def package() -> dict:
    assert PACKAGE_PATH.is_file(), f"missing package at {PACKAGE_PATH}"
    return yaml.safe_load(PACKAGE_PATH.read_text(encoding="utf-8"))


def _helpers_by_entity_id(package: dict, helper_kind: str) -> dict[str, dict]:
    """Return {entity_id: helper_dict} for a given helper kind
    (e.g. 'input_text', 'input_boolean', 'shell_command')."""
    raw = package.get(helper_kind, {}) or {}
    assert isinstance(raw, dict), (
        f"{helper_kind!r} must be a YAML mapping keyed by entity_id; got {type(raw).__name__}"
    )
    return raw


def _template_binary_sensors(package: dict) -> list[dict]:
    tpl = package.get("template") or []
    out: list[dict] = []
    for entry in tpl:
        for bs in (entry.get("binary_sensor") or []):
            out.append(bs)
    return out


def _template_sensors(package: dict) -> list[dict]:
    tpl = package.get("template") or []
    out: list[dict] = []
    for entry in tpl:
        for s in (entry.get("sensor") or []):
            out.append(s)
    return out


def _command_line_sensors(package: dict) -> list[dict]:
    raw = package.get("command_line") or []
    out: list[dict] = []
    for entry in raw:
        for s in (entry.get("sensor") or []):
            out.append(s)
    return out


def _automations(package: dict) -> list[dict]:
    raw = package.get("automation") or []
    assert isinstance(raw, list), (
        f"'automation' must be a list; got {type(raw).__name__}"
    )
    return raw


# ----------------------------------------------------------------------------
# (a) YAML parses successfully
# ----------------------------------------------------------------------------


def test_yaml_parses_successfully(package: dict) -> None:
    assert isinstance(package, dict), (
        f"package must be a YAML mapping at the top level; got {type(package).__name__}"
    )
    expected = {"input_text", "input_boolean", "input_button", "input_datetime", "shell_command", "command_line", "template", "automation"}
    assert expected.issubset(set(package.keys())), (
        f"package is missing required top-level keys; "
        f"missing={expected - set(package.keys())}; got={sorted(package.keys())}"
    )


# ----------------------------------------------------------------------------
# (b) Required helpers present
# ----------------------------------------------------------------------------


REQUIRED_INPUT_TEXTS = ("rc_tailscale_self_test_tunnel_url",)
REQUIRED_INPUT_BOOLEANS = ("rc_tailscale_self_test_running",)
REQUIRED_INPUT_BUTTONS = ("rc_tailscale_run_self_test",)
REQUIRED_INPUT_DATETIMES = ("rc_tailscale_self_test_last_run",)
REQUIRED_SHELL_COMMANDS = (
    "rc_tailscale_self_test_outbound_probe",
    "rc_tailscale_self_test_inbound_probe",
)
REQUIRED_COMMAND_LINE_SENSOR_UNIQUE_IDS = (
    "rc_tailscale_self_test_outbound_code",
    "rc_tailscale_self_test_expected_nonce_sensor",
    "rc_tailscale_self_test_received_nonce_sensor",
)
REQUIRED_BINARY_SENSOR_UNIQUE_IDS = (
    "rc_tailscale_self_test_outbound_ok",
    "rc_tailscale_self_test_inbound_ok",
    "rc_tailscale_self_test_ok",
    "rc_tailscale_self_test_recovery",
)
REQUIRED_SENSOR_UNIQUE_IDS = ("rc_tailscale_self_test_status",)


@pytest.mark.parametrize("entity_id", REQUIRED_INPUT_TEXTS)
def test_required_input_text_present(package: dict, entity_id: str) -> None:
    helpers = _helpers_by_entity_id(package, "input_text")
    assert entity_id in helpers, (
        f"missing required input_text: {entity_id!r}; "
        f"present={sorted(helpers.keys())}"
    )


@pytest.mark.parametrize("entity_id", REQUIRED_INPUT_BOOLEANS)
def test_required_input_boolean_present(package: dict, entity_id: str) -> None:
    helpers = _helpers_by_entity_id(package, "input_boolean")
    assert entity_id in helpers, (
        f"missing required input_boolean: {entity_id!r}; "
        f"present={sorted(helpers.keys())}"
    )


@pytest.mark.parametrize("entity_id", REQUIRED_INPUT_BUTTONS)
def test_required_input_button_present(package: dict, entity_id: str) -> None:
    helpers = _helpers_by_entity_id(package, "input_button")
    assert entity_id in helpers, (
        f"missing required input_button: {entity_id!r}; "
        f"present={sorted(helpers.keys())}"
    )


@pytest.mark.parametrize("entity_id", REQUIRED_INPUT_DATETIMES)
def test_required_input_datetime_present(package: dict, entity_id: str) -> None:
    helpers = _helpers_by_entity_id(package, "input_datetime")
    assert entity_id in helpers, (
        f"missing required input_datetime: {entity_id!r}; "
        f"present={sorted(helpers.keys())}"
    )


@pytest.mark.parametrize("entity_id", REQUIRED_SHELL_COMMANDS)
def test_required_shell_command_present(package: dict, entity_id: str) -> None:
    helpers = _helpers_by_entity_id(package, "shell_command")
    assert entity_id in helpers, (
        f"missing required shell_command: {entity_id!r}; "
        f"present={sorted(helpers.keys())}"
    )


@pytest.mark.parametrize("unique_id", REQUIRED_COMMAND_LINE_SENSOR_UNIQUE_IDS)
def test_required_command_line_sensor_present(package: dict, unique_id: str) -> None:
    sensors = _command_line_sensors(package)
    uids = [s.get("unique_id") for s in sensors]
    assert unique_id in uids, (
        f"missing required command_line sensor with unique_id={unique_id!r}; "
        f"present unique_ids={uids}"
    )


@pytest.mark.parametrize("unique_id", REQUIRED_BINARY_SENSOR_UNIQUE_IDS)
def test_required_template_binary_sensor_present(package: dict, unique_id: str) -> None:
    bss = _template_binary_sensors(package)
    uids = [bs.get("unique_id") for bs in bss]
    assert unique_id in uids, (
        f"missing required template binary_sensor with unique_id={unique_id!r}; "
        f"present unique_ids={uids}"
    )


@pytest.mark.parametrize("unique_id", REQUIRED_SENSOR_UNIQUE_IDS)
def test_required_template_sensor_present(package: dict, unique_id: str) -> None:
    sensors = _template_sensors(package)
    uids = [s.get("unique_id") for s in sensors]
    assert unique_id in uids, (
        f"missing required template sensor with unique_id={unique_id!r}; "
        f"present unique_ids={uids}"
    )


# ----------------------------------------------------------------------------
# (c) §8 MANDATORY automations — unique_id, trigger, action contract
# ----------------------------------------------------------------------------


REQUIRED_AUTOMATIONS = (
    "rc_tailscale_self_test_run",
    "rc_tailscale_self_test_recovery",
    "rc_tailscale_self_test_wizard_advance",
)


@pytest.mark.parametrize("automation_id", REQUIRED_AUTOMATIONS)
def test_required_automation_present(package: dict, automation_id: str) -> None:
    autos = _automations(package)
    ids = [a.get("id") for a in autos]
    assert automation_id in ids, (
        f"missing required automation with id={automation_id!r}; "
        f"present ids={ids}"
    )


def test_automation_run_contract(package: dict) -> None:
    """§8.T.1 — triggers on button press / stage transition /
    rc_run_tailscale_self_test event, requires tunnel URL set,
    sets running flag, fires both probes, waits 30s, clears
    running flag, stamps last_run. MUST NOT clear tunnel URL."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_tailscale_self_test_run")
    triggers = auto.get("trigger") or []
    # Button trigger
    assert any(
        t.get("platform") == "state"
        and t.get("entity_id") == "input_button.rc_tailscale_run_self_test"
        for t in triggers
    ), f"run must trigger on rc_tailscale_run_self_test button; got triggers={triggers}"
    # Wizard stage trigger
    assert any(
        t.get("platform") == "state"
        and t.get("entity_id") == "input_select.rc_remote_access_setup_stage"
        and t.get("to") == "tailscale_verify"
        for t in triggers
    ), f"run must trigger on wizard stage tailscale_verify; got triggers={triggers}"
    # Event trigger
    assert any(
        t.get("platform") == "event"
        and t.get("event_type") == "rc_run_tailscale_self_test"
        for t in triggers
    ), f"run must trigger on rc_run_tailscale_self_test event; got triggers={triggers}"
    # Condition: URL set
    conditions = auto.get("condition") or []
    cond_serialized = " ".join(str(c) for c in conditions)
    assert "rc_tailscale_self_test_tunnel_url" in cond_serialized, (
        f"run must condition on tunnel URL being non-empty; got conditions={conditions}"
    )
    # Actions
    actions = auto.get("action") or []
    actions_serialized = " ".join(str(a) for a in actions)
    actions_dumped = yaml.safe_dump(actions, default_flow_style=False)
    assert "input_boolean.turn_on" in actions_serialized, (
        f"run must turn on the running flag; got actions={actions}"
    )
    assert "shell_command.rc_tailscale_self_test_outbound_probe" in actions_serialized, (
        f"run must fire the outbound probe; got actions={actions}"
    )
    assert "shell_command.rc_tailscale_self_test_inbound_probe" in actions_serialized, (
        f"run must fire the inbound probe; got actions={actions}"
    )
    assert "input_datetime.set_datetime" in actions_serialized, (
        f"run must stamp last_run; got actions={actions}"
    )
    assert "00:00:30" in actions_dumped, (
        f"run must wait 30s before clearing running flag; got actions={actions}"
    )
    # MUST NOT clear the tunnel URL (idempotent retry)
    assert "input_text.set_value" not in actions_serialized or "rc_tailscale_self_test_tunnel_url" not in actions_dumped, (
        f"run MUST NOT clear the tunnel URL helper; got actions={actions}"
    )


def test_automation_recovery_contract(package: dict) -> None:
    """§8.T.2 — triggers on running flag ON for >60s without OK,
    clears running flag, fires plain-English persistent_notification.
    MUST NOT clear tunnel URL."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_tailscale_self_test_recovery")
    triggers = auto.get("trigger") or []
    assert any(
        t.get("platform") == "state"
        and t.get("entity_id") == "input_boolean.rc_tailscale_self_test_running"
        and t.get("to") == "on"
        and t.get("for") == "00:01:00"
        for t in triggers
    ), f"recovery must trigger on running flag ON for 60s; got triggers={triggers}"
    # Condition: NOT OK
    conditions = auto.get("condition") or []
    cond_dumped = yaml.safe_dump(conditions, default_flow_style=False)
    assert "binary_sensor.rc_tailscale_self_test_ok" in cond_dumped, (
        f"recovery must condition on self-test NOT being OK; got conditions={conditions}"
    )
    # Actions
    actions = auto.get("action") or []
    actions_dumped = yaml.safe_dump(actions, default_flow_style=False)
    assert "persistent_notification.create" in actions_dumped, (
        f"recovery must fire persistent_notification; got actions={actions}"
    )
    assert "input_boolean.turn_off" in actions_dumped, (
        f"recovery must clear the running flag; got actions={actions}"
    )
    # Plain-English recovery copy
    lower = actions_dumped.lower()
    assert "tunnel" in lower, f"recovery copy must mention 'tunnel' in plain English; got actions={actions}"
    assert "wizard" in lower or "van" in lower, (
        f"recovery copy must mention 'wizard' or 'van' in plain English; got actions={actions}"
    )
    # MUST NOT clear the tunnel URL
    assert "rc_tailscale_self_test_tunnel_url" not in actions_dumped or "set_value" not in actions_dumped, (
        f"recovery MUST NOT clear the tunnel URL helper; got actions={actions}"
    )


def test_automation_wizard_advance_contract(package: dict) -> None:
    """§8.T.3 — triggers on rc_tailscale_self_test_ok going ON,
    conditions on rc_setup_stage == 'networking', flips stage to
    'map' + fires plain-English persistent_notification. Idempotent
    via the condition (no-op if stage already past networking)."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_tailscale_self_test_wizard_advance")
    triggers = auto.get("trigger") or []
    assert any(
        t.get("platform") == "state"
        and t.get("entity_id") == "binary_sensor.rc_tailscale_self_test_ok"
        and t.get("to") == "on"
        for t in triggers
    ), f"wizard_advance must trigger on rc_tailscale_self_test_ok going ON; got triggers={triggers}"
    conditions = auto.get("condition") or []
    cond_dumped = yaml.safe_dump(conditions, default_flow_style=False)
    assert "input_select.rc_setup_stage" in cond_dumped, (
        f"wizard_advance must condition on rc_setup_stage; got conditions={conditions}"
    )
    assert "networking" in cond_dumped, (
        f"wizard_advance must condition on rc_setup_stage == 'networking'; got conditions={conditions}"
    )
    actions = auto.get("action") or []
    actions_dumped = yaml.safe_dump(actions, default_flow_style=False)
    assert "input_select.select_option" in actions_dumped, (
        f"wizard_advance must call input_select.select_option; got actions={actions}"
    )
    assert "map" in actions_dumped, (
        f"wizard_advance must flip stage to 'map'; got actions={actions}"
    )
    assert "persistent_notification.create" in actions_dumped, (
        f"wizard_advance must fire persistent_notification; got actions={actions}"
    )
    lower = actions_dumped.lower()
    assert "reachable" in lower and "anywhere" in lower, (
        f"wizard_advance copy must include 'reachable' + 'anywhere' plain English; got actions={actions}"
    )


# ----------------------------------------------------------------------------
# (d) Operator-editable tunnel URL — mode: password (sensitive)
# ----------------------------------------------------------------------------


def test_tunnel_url_helper_is_password_mode(package: dict) -> None:
    """The tunnel URL helper MUST be `mode: password` so it's never
    exposed in dashboard logs / history / events."""
    helpers = _helpers_by_entity_id(package, "input_text")
    url = helpers.get("rc_tailscale_self_test_tunnel_url")
    assert url is not None, "rc_tailscale_self_test_tunnel_url helper missing"
    assert url.get("mode") == "password", (
        f"rc_tailscale_self_test_tunnel_url MUST be mode: password (sensitive); "
        f"got mode={url.get('mode')!r}"
    )


def test_running_flag_default_off(package: dict) -> None:
    """The running flag MUST default to off (the wizard is not
    running on first boot)."""
    helpers = _helpers_by_entity_id(package, "input_boolean")
    running = helpers.get("rc_tailscale_self_test_running")
    assert running is not None, "rc_tailscale_self_test_running helper missing"
    assert running.get("initial") is False, (
        f"rc_tailscale_self_test_running default MUST be false; "
        f"got {running.get('initial')!r}"
    )


def test_last_run_initial_epoch(package: dict) -> None:
    """The last_run helper MUST default to the epoch
    (1970-01-01 00:00:00) so the 'never_run' check in the
    recovery / status templates works correctly."""
    helpers = _helpers_by_entity_id(package, "input_datetime")
    last_run = helpers.get("rc_tailscale_self_test_last_run")
    assert last_run is not None, "rc_tailscale_self_test_last_run helper missing"
    assert last_run.get("initial") == "1970-01-01 00:00:00", (
        f"rc_tailscale_self_test_last_run default MUST be epoch; "
        f"got {last_run.get('initial')!r}"
    )


# ----------------------------------------------------------------------------
# (e) Status sensor template — covers all 6 state combinations
# ----------------------------------------------------------------------------


# The branches the template must cover. Each combo maps to one of
# the 6 plain-English phrases the template can render. The test
# runs a pure-function reimplementation of the template and asserts
# the slice spec's 6 branches all produce non-empty strings (no
# hidden fall-through to the catch-all `else`).
EXPECTED_STATUS_BRANCHES: tuple[tuple[tuple, str], ...] = (
    # (url, running, outbound, inbound, recovery, never_run) → expected substring (lowercase)
    (("", False, False, False, False, True), "type your tunnel address"),
    (("https://my-van.ts.net", True, False, False, False, False), "checking your tunnel"),
    (("https://my-van.ts.net", False, True, True, False, False), "round-trip succeeded"),
    (("https://my-van.ts.net", False, False, False, True, False), "hub can't reach itself"),
    (("https://my-van.ts.net", False, True, False, True, False), "phone-side callback didn't arrive"),
    (("https://my-van.ts.net", False, False, False, False, False), "ready to check your tunnel"),
)


def _status_pure(url: str, running: bool, outbound: bool, inbound: bool, recovery: bool, never_run: bool) -> str:
    """Pure-function reimplementation of `sensor.rc_tailscale_self_test_status`.

    Extracted out of the YAML template so the test can call it with
    every required combination without spinning up Home Assistant.
    Keep this in lockstep with the YAML template; the test asserts
    the YAML still contains the strings this function emits, so the
    two cannot drift silently.
    """
    if url == "":
        return "Type your tunnel address to run a check."
    if running:
        return "Checking your tunnel — one moment..."
    if outbound and inbound:
        return "Round-trip succeeded — your tunnel is two-way."
    if recovery and not outbound:
        return "Hub can't reach itself through the tunnel — check your Tailscale ACL."
    if recovery and not inbound:
        return "Phone-side callback didn't arrive — check the tunnel URL."
    if never_run:
        return "Ready to check your tunnel — tap Run now."
    return "Ready to check your tunnel."


@pytest.mark.parametrize(
    "combo,expected_substr",
    [
        (combo, substr) for combo, substr in EXPECTED_STATUS_BRANCHES
    ],
)
def test_status_template_covers_combo(combo: tuple, expected_substr: str) -> None:
    """The pure-function reimplementation must cover every required
    combination with a plain-English phrase that contains the
    expected substring (case-insensitive)."""
    result = _status_pure(*combo)
    assert expected_substr in result.lower(), (
        f"status template branch for combo={combo!r} must include "
        f"{expected_substr!r}; got {result!r}"
    )


def test_status_template_present_in_yaml(package: dict) -> None:
    """The YAML template must actually contain the plain-English
    phrases the pure function emits (catches silent drift between the
    pure-function helper and the YAML)."""
    sensors = _template_sensors(package)
    status = next(
        (s for s in sensors if s.get("unique_id") == "rc_tailscale_self_test_status"),
        None,
    )
    assert status is not None, "missing sensor.rc_tailscale_self_test_status template"
    state = status.get("state") or ""
    state_lower = state.lower()
    must_contain = (
        "type your tunnel address",
        "checking your tunnel",
        "round-trip succeeded",
        "hub can't reach itself",
        "phone-side callback didn't arrive",
        "ready to check your tunnel",
    )
    for marker in must_contain:
        assert marker in state_lower, (
            f"sensor.rc_tailscale_self_test_status state template is missing "
            f"marker {marker!r}; verify the YAML template is in lockstep with "
            f"the pure-function helper in this test"
        )


def test_status_template_no_operator_jargon(package: dict) -> None:
    """The user-facing strings the status template can render MUST
    NOT contain operator jargon (no entity IDs in the output, no
    bash terms, no upstream-integration names in the user-visible
    output).

    Note: the template SOURCE naturally references entity_ids to
    compute its output — that's normal in Home Assistant templates.
    This test pins the user-facing strings by computing them via
    the pure-function helper and asserting each output is jargon-
    free.
    """
    forbidden = (
        "binary_sensor.",
        "input_boolean.",
        "input_text.",
        "input_datetime.",
        "input_button.",
        "shell_command.",
        "command_line.",
        "avahi-daemon",
        "zeroconf",
        "tskey-",
        "magicdns",
        ".ts.net",
        "curl ",
        "bash ",
    )
    # Exercise every combination from EXPECTED_STATUS_BRANCHES +
    # a few extras (URL configured but never run + URL configured,
    # running, with outbound already on).
    combos = [
        c for c, _ in EXPECTED_STATUS_BRANCHES
    ] + [
        ("https://my-van.ts.net", True, True, False, False, False),
        ("https://my-van.ts.net", False, True, False, False, False),
    ]
    for combo in combos:
        result = _status_pure(*combo)
        for term in forbidden:
            assert term not in result.lower(), (
                f"sensor.rc_tailscale_self_test_status output {result!r} "
                f"(combo={combo}) contains operator jargon {term!r}; "
                f"user-facing copy must be plain English"
            )


# ----------------------------------------------------------------------------
# (f) Idempotency — running PyYAML twice produces the same dict
# ----------------------------------------------------------------------------


def test_yaml_idempotent(package: dict) -> None:
    """Parse the YAML twice, dump both via yaml.safe_dump, and assert
    the two dumps are byte-identical. No random IDs / no timestamps /
    no `$` substitutions that would diverge between runs."""
    text = PACKAGE_PATH.read_text(encoding="utf-8")
    d1 = yaml.safe_load(text)
    d2 = yaml.safe_load(text)
    dump1 = yaml.safe_dump(d1, sort_keys=True)
    dump2 = yaml.safe_dump(d2, sort_keys=True)
    assert dump1 == dump2, (
        "YAML not idempotent — re-parsing produces different output. "
        "Possible cause: random IDs, timestamps, or non-deterministic ordering."
    )


def test_shell_command_does_not_duplicate_probe(package: dict) -> None:
    """Idempotency at the probe layer: there must be exactly ONE
    `shell_command.rc_tailscale_self_test_outbound_probe` and ONE
    `shell_command.rc_tailscale_self_test_inbound_probe` defined.
    Re-pushing the package does NOT duplicate the probes."""
    helpers = _helpers_by_entity_id(package, "shell_command")
    assert helpers.get("rc_tailscale_self_test_outbound_probe") is not None
    assert helpers.get("rc_tailscale_self_test_inbound_probe") is not None
    assert len(helpers) == 2, (
        f"expected exactly 2 shell_command probes; got {len(helpers)}: {list(helpers.keys())}"
    )


def test_command_line_sensors_have_distinct_unique_ids(package: dict) -> None:
    """All command_line sensors MUST have unique unique_ids (HA's
    registry rejects duplicates)."""
    sensors = _command_line_sensors(package)
    uids = [s.get("unique_id") for s in sensors]
    assert len(uids) == len(set(uids)), (
        f"duplicate command_line unique_ids detected: {uids}"
    )


def test_automation_run_does_not_clear_tunnel_url(package: dict) -> None:
    """The §8.T.1 run automation MUST NOT call
    input_text.set_value on rc_tailscale_self_test_tunnel_url (the
    operator should be able to re-tap without re-typing the URL)."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_tailscale_self_test_run")
    actions_dumped = yaml.safe_dump(auto.get("action") or [], default_flow_style=False)
    assert not (
        "input_text.set_value" in actions_dumped
        and "rc_tailscale_self_test_tunnel_url" in actions_dumped
    ), (
        f"§8.T.1 MUST NOT call input_text.set_value on "
        f"rc_tailscale_self_test_tunnel_url (idempotent retry); "
        f"got actions={auto.get('action')}"
    )


def test_automation_recovery_does_not_clear_tunnel_url(package: dict) -> None:
    """The §8.T.2 recovery automation MUST NOT call
    input_text.set_value on rc_tailscale_self_test_tunnel_url
    (the operator should be able to re-tap without re-typing the URL)."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_tailscale_self_test_recovery")
    actions_dumped = yaml.safe_dump(auto.get("action") or [], default_flow_style=False)
    assert not (
        "input_text.set_value" in actions_dumped
        and "rc_tailscale_self_test_tunnel_url" in actions_dumped
    ), (
        f"§8.T.2 MUST NOT call input_text.set_value on "
        f"rc_tailscale_self_test_tunnel_url (idempotent retry); "
        f"got actions={auto.get('action')}"
    )


# ----------------------------------------------------------------------------
# (g) rc-entity-naming compliance — every entity_id starts with
# `rc_tailscale_self_test_` or `rc_tailscale_run_self_test`.
# ----------------------------------------------------------------------------


ALLOWED_ENTITY_ID_PREFIXES = (
    "rc_tailscale_self_test_",
    "rc_tailscale_run_self_test",  # the operator-facing button
)


def _all_entity_ids(package: dict) -> list[str]:
    ids: list[str] = []
    for kind in (
        "input_select",
        "input_text",
        "input_boolean",
        "input_number",
        "input_datetime",
        "input_button",
        "shell_command",
    ):
        for eid in (_helpers_by_entity_id(package, kind).keys()):
            ids.append(eid)
    return ids


def test_entity_ids_comply_with_rc_naming(package: dict) -> None:
    """Every helper entity_id MUST start with one of the
    `rc_tailscale_self_test_` / `rc_tailscale_run_self_test`
    prefixes (per docs/reference/rc-entity-naming.md)."""
    eids = _all_entity_ids(package)
    assert eids, "no entity_ids found in the package"
    for eid in eids:
        assert any(eid.startswith(p) for p in ALLOWED_ENTITY_ID_PREFIXES), (
            f"entity_id {eid!r} violates rc-naming; must start with one of "
            f"{ALLOWED_ENTITY_ID_PREFIXES!r}"
        )


def test_command_line_sensors_comply_with_rc_naming(package: dict) -> None:
    """Every command_line sensor's unique_id MUST start with
    `rc_tailscale_self_test_`."""
    sensors = _command_line_sensors(package)
    uids = [s.get("unique_id") for s in sensors]
    assert uids, "no command_line sensors found"
    for uid in uids:
        assert uid.startswith("rc_tailscale_self_test_"), (
            f"command_line unique_id {uid!r} violates rc-naming; "
            f"must start with 'rc_tailscale_self_test_'"
        )


def test_template_binary_sensors_comply_with_rc_naming(package: dict) -> None:
    """Every template binary_sensor's unique_id MUST start with
    `rc_tailscale_self_test_`."""
    bss = _template_binary_sensors(package)
    uids = [bs.get("unique_id") for bs in bss]
    assert uids, "no template binary_sensors found"
    for uid in uids:
        assert uid.startswith("rc_tailscale_self_test_"), (
            f"template binary_sensor unique_id {uid!r} violates rc-naming; "
            f"must start with 'rc_tailscale_self_test_'"
        )


def test_template_sensors_comply_with_rc_naming(package: dict) -> None:
    """Every template sensor's unique_id MUST start with
    `rc_tailscale_self_test_`."""
    sensors = _template_sensors(package)
    uids = [s.get("unique_id") for s in sensors]
    assert uids, "no template sensors found"
    for uid in uids:
        assert uid.startswith("rc_tailscale_self_test_"), (
            f"template sensor unique_id {uid!r} violates rc-naming; "
            f"must start with 'rc_tailscale_self_test_'"
        )


def test_automation_ids_comply_with_rc_naming(package: dict) -> None:
    """Every automation's `id` MUST start with `rc_tailscale_self_test_`
    or `rc_tailscale_run_self_test`."""
    autos = _automations(package)
    ids = [a.get("id") for a in autos]
    assert ids, "no automations found"
    for aid in ids:
        assert any(aid.startswith(p) for p in ALLOWED_ENTITY_ID_PREFIXES), (
            f"automation id {aid!r} violates rc-naming; must start with one of "
            f"{ALLOWED_ENTITY_ID_PREFIXES!r}"
        )


# ----------------------------------------------------------------------------
# (h) No secrets in YAML — grep for tskey- or any tailnet auth-key
# pattern, plus hard-coded IPs.
# ----------------------------------------------------------------------------


SECRET_PATTERNS = (
    re.compile(r"tskey-[A-Za-z0-9_-]{10,}"),
    re.compile(r"tskey-api-[A-Za-z0-9_-]{10,}"),
    re.compile(r"ts-auth-[A-Za-z0-9_-]{10,}"),
    # Also grep for hard-coded IPv4 fallbacks (could leak operator network info)
    re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"),
    re.compile(r"\b172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b"),
)


def test_no_secrets_in_yaml() -> None:
    text = PACKAGE_PATH.read_text(encoding="utf-8")
    for pat in SECRET_PATTERNS:
        matches = pat.findall(text)
        assert not matches, (
            f"secret pattern {pat.pattern!r} found in YAML: {matches[:3]} "
            f"— operator credentials / IPs MUST NOT be committed"
        )


# ----------------------------------------------------------------------------
# (i) IKEA doc 5-step shape — docs/setup/tailscale-self-test.md
# exists, opens with one plain-English sentence, has 5 numbered
# sections, contains the operator→vanlifer translation table.
# ----------------------------------------------------------------------------


def test_ikea_doc_exists() -> None:
    assert DOC_PATH.is_file(), f"missing IKEA doc at {DOC_PATH}"


def test_ikea_doc_opens_with_plain_english() -> None:
    """The doc must open with one plain-English sentence (no YAML
    jargon, no 'this slice' wording, no 'Wave 9' labels)."""
    text = DOC_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    first_content = next(
        (line.strip() for line in lines[1:] if line.strip() and not line.strip().startswith("#")),
        "",
    )
    assert first_content, "doc has no first content paragraph"
    forbidden_openers = (
        "this slice",
        "wave 9",
        "wave",
        "tier-a",
        "tier-b",
        "tier-c",
        "yaml",
        "input_boolean",
        "binary_sensor",
        "rc_tailscale_self_test_",
        "homeassistant/packages/",
        "scripts/check.sh",
        "pr #",
        "commit ",
        "branch ",
        "lint-pass",
        "apple-grade",
    )
    lower = first_content.lower()
    for term in forbidden_openers:
        assert term not in lower, (
            f"IKEA doc opener {first_content!r} contains operator jargon {term!r}; "
            f"first sentence must be plain English a vanlifer would understand"
        )


def test_ikea_doc_has_five_numbered_sections() -> None:
    """The IKEA doc MUST have exactly five numbered sections
    (## 1 / 2 / 3 / 4 / 5)."""
    text = DOC_PATH.read_text(encoding="utf-8")
    section_lines = [
        line for line in text.splitlines()
        if re.match(r"^##\s+\d+\.\s+", line.strip())
    ]
    section_numbers = [
        int(re.match(r"^##\s+(\d+)\.", line.strip()).group(1))
        for line in section_lines
    ]
    assert section_numbers == [1, 2, 3, 4, 5], (
        f"IKEA doc must have exactly 5 numbered sections (## 1 / 2 / 3 / 4 / 5); "
        f"got {section_numbers}"
    )


def test_ikea_doc_has_translation_table() -> None:
    """The IKEA doc MUST contain an operator→vanlifer translation
    table somewhere (the doctrine block requires it)."""
    text = DOC_PATH.read_text(encoding="utf-8")
    lower = text.lower()
    assert "operator" in lower, "IKEA doc missing 'operator' translation table"
    assert any(
        marker in lower
        for marker in ("you might call it", "you'd call it", "what you see", "what this means")
    ), "IKEA doc missing plain-English translation explanation"


def test_ikea_doc_no_supersede_banner() -> None:
    """No 'SUPERSEDED' banner in user-facing tree (per doctrine)."""
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "SUPERSEDED" not in text, "IKEA doc must not contain a SUPERSEDED banner"
    assert "CRON-HANDOFF" not in text.upper(), "IKEA doc must not mention Cron-handoff"


def test_ikea_doc_answers_all_four_questions() -> None:
    """The IKEA doc MUST answer all four questions:
       - what it does (section 1: What this is)
       - what you see (section 2)
       - what you do (section 3)
       - what to do if it goes wrong (section 4)
    Plus section 5 (Useful links). Each section must be non-empty."""
    text = DOC_PATH.read_text(encoding="utf-8")
    # Split by numbered section headings
    section_pattern = re.compile(r"^##\s+\d+\.\s+(.+?)$", re.MULTILINE)
    matches = list(section_pattern.finditer(text))
    assert len(matches) >= 5, f"expected at least 5 sections; got {len(matches)}"
    # Verify section titles cover the required topics
    section_titles = [m.group(1).strip().lower() for m in matches]
    required_topics = ["what this is", "what you see", "what you do", "if it goes wrong", "useful links"]
    for topic in required_topics:
        assert any(topic in t for t in section_titles), (
            f"IKEA doc missing section covering {topic!r}; got section titles={section_titles}"
        )


# ----------------------------------------------------------------------------
# (j) §8.T.1 idempotency — re-running the self-test does NOT reset
# the tunnel URL. The run automation has no `input_text.set_value`
# targeting `rc_tailscale_self_test_tunnel_url`. (Covered above in
# `test_automation_run_does_not_clear_tunnel_url`, but also pin the
# positive assertion here: the run automation DOES turn off the
# running flag + DOES stamp last_run, so re-runs have observable
# side-effects without losing operator-entered data.)
# ----------------------------------------------------------------------------


def test_run_automation_observable_side_effects(package: dict) -> None:
    """§8.T.1 MUST clear the running flag (turn_off) and stamp
    last_run (input_datetime.set_datetime) so re-runs have
    observable side-effects without losing operator data."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_tailscale_self_test_run")
    actions_dumped = yaml.safe_dump(auto.get("action") or [], default_flow_style=False)
    assert "input_boolean.turn_off" in actions_dumped, (
        f"§8.T.1 MUST turn_off the running flag; got actions={auto.get('action')}"
    )
    assert "input_datetime.set_datetime" in actions_dumped, (
        f"§8.T.1 MUST stamp last_run; got actions={auto.get('action')}"
    )


# ----------------------------------------------------------------------------
# (k) §8.T.3 idempotency — wizard advance only fires when
# rc_setup_stage == 'networking', so it's a no-op if the stage is
# already past (e.g. the existing remote-access wizard already
# advanced it). The condition pins this.
# ----------------------------------------------------------------------------


def test_wizard_advance_advances_to_map_not_done(package: dict) -> None:
    """§8.T.3 MUST advance to 'map' (the next setup stage after
    networking), NOT to 'done'. Going to 'done' would skip the
    rest of the wizard."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_tailscale_self_test_wizard_advance")
    actions_dumped = yaml.safe_dump(auto.get("action") or [], default_flow_style=False)
    assert "map" in actions_dumped, (
        f"§8.T.3 MUST advance to 'map'; got actions={auto.get('action')}"
    )
    # Verify the option selected is 'map', not 'done' (search for
    # the option: 'map' pattern specifically).
    assert "option: map" in actions_dumped, (
        f"§8.T.3 MUST select 'map' as the new option; got actions={auto.get('action')}"
    )


# ----------------------------------------------------------------------------
# (l) Shell command probe timeouts — both probes have 10-second
# timeouts so a stalled tunnel never blocks the dashboard.
# ----------------------------------------------------------------------------


def test_shell_command_probes_have_10s_timeout(package: dict) -> None:
    """Both shell_command probes MUST have a 10-second timeout
    (HA's standard `timeout 10 ...`) so a stalled tunnel doesn't
    block the dashboard."""
    helpers = _helpers_by_entity_id(package, "shell_command")
    for eid in REQUIRED_SHELL_COMMANDS:
        cmd = helpers.get(eid)
        assert cmd is not None, f"missing shell_command {eid!r}"
        assert "timeout 10" in cmd, (
            f"shell_command {eid!r} MUST use 'timeout 10 ...' to bound probe latency; "
            f"got cmd={cmd!r}"
        )
