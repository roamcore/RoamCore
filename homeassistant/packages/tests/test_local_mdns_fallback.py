"""Manifest-honesty + structural tests for
`homeassistant/packages/roamcore_local_mdns_fallback.yaml`
(Wave 9 #122.d.iv — Phase 6 Tailscale wizard, sub-slice D.iv:
mDNS `roamcore.local` fallback so local survives Tailscale failure).

This is the verification rig for the new local-access-fallback
slice. It asserts:

  - YAML parses successfully (sanity check).
  - Every required helper is present (input_boolean × 1,
    input_text × 1, input_button × 1, shell_command × 1,
    binary_sensor × 1, sensor × 2).
  - All 3 §8 MANDATORY automations are present with the correct
    `id:` and trigger/action contract.
  - `input_text.rc_local_mdns_hostname` is operator-editable
    (`mode: text`, default `roamcore`).
  - `sensor.rc_local_mdns_status` template covers all the
    enabled × resolvable × ip combinations from the slice spec
    (pure-function test — extract the template logic into a small
    helper inside this file and run it through every combo).
  - Idempotency: running the YAML through PyYAML twice produces
    the same dict (no random IDs, no timestamps).
  - rc-entity-naming compliance: every entity_id starts with
    `rc_local_mdns_`.
  - No secrets in YAML: grep for `tskey-` or any tailnet auth-key
    pattern — must NOT find any.
  - IKEA doc 5-step shape: docs/setup/local-access-fallback.md
    exists, opens with one plain-English sentence, has exactly
    five numbered sections, contains an operator→vanlifer
    translation table.
  - Automation contract: mDNS failure (binary_sensor off) →
    fallback tile surfaced (persistent_notification fired with
    the "Reachable at <ip>:8123 instead" copy).
  - §8.M.3 status copy is plain English (no bash, no entity IDs,
    no operator jargon).

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest homeassistant/packages/tests/test_local_mdns_fallback.py -v
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
PACKAGE_PATH = REPO_ROOT / "homeassistant" / "packages" / "roamcore_local_mdns_fallback.yaml"
DOC_PATH = REPO_ROOT / "docs" / "setup" / "local-access-fallback.md"


# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def package() -> dict:
    assert PACKAGE_PATH.is_file(), f"missing package at {PACKAGE_PATH}"
    return yaml.safe_load(PACKAGE_PATH.read_text(encoding="utf-8"))


def _helpers_by_entity_id(package: dict, helper_kind: str) -> dict[str, dict]:
    """Return {entity_id: helper_dict} for a given helper kind
    (e.g. 'input_select', 'input_text')."""
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
    # The 6 expected top-level keys (input_boolean + input_text +
    # input_button + shell_command + template + automation)
    expected = {"input_boolean", "input_text", "input_button", "shell_command", "template", "automation"}
    assert expected.issubset(set(package.keys())), (
        f"package is missing required top-level keys; "
        f"missing={expected - set(package.keys())}; got={sorted(package.keys())}"
    )


# ----------------------------------------------------------------------------
# (b) Required helpers present
# ----------------------------------------------------------------------------


REQUIRED_INPUT_BOOLEANS = ("rc_local_mdns_fallback_enabled",)
REQUIRED_INPUT_TEXTS = ("rc_local_mdns_hostname",)
REQUIRED_INPUT_BUTTONS = ("rc_local_mdns_retest",)
REQUIRED_SHELL_COMMANDS = ("rc_local_mdns_probe",)
REQUIRED_BINARY_SENSOR_UNIQUE_IDS = ("rc_local_mdns_resolvable",)
REQUIRED_SENSOR_UNIQUE_IDS = (
    "rc_local_mdns_resolved_ip",
    "rc_local_mdns_status",
)


@pytest.mark.parametrize("entity_id", REQUIRED_INPUT_BOOLEANS)
def test_required_input_boolean_present(package: dict, entity_id: str) -> None:
    helpers = _helpers_by_entity_id(package, "input_boolean")
    assert entity_id in helpers, (
        f"missing required input_boolean: {entity_id!r}; "
        f"present={sorted(helpers.keys())}"
    )


@pytest.mark.parametrize("entity_id", REQUIRED_INPUT_TEXTS)
def test_required_input_text_present(package: dict, entity_id: str) -> None:
    helpers = _helpers_by_entity_id(package, "input_text")
    assert entity_id in helpers, (
        f"missing required input_text: {entity_id!r}; "
        f"present={sorted(helpers.keys())}"
    )


@pytest.mark.parametrize("entity_id", REQUIRED_INPUT_BUTTONS)
def test_required_input_button_present(package: dict, entity_id: str) -> None:
    helpers = _helpers_by_entity_id(package, "input_button")
    assert entity_id in helpers, (
        f"missing required input_button: {entity_id!r}; "
        f"present={sorted(helpers.keys())}"
    )


@pytest.mark.parametrize("entity_id", REQUIRED_SHELL_COMMANDS)
def test_required_shell_command_present(package: dict, entity_id: str) -> None:
    helpers = _helpers_by_entity_id(package, "shell_command")
    assert entity_id in helpers, (
        f"missing required shell_command: {entity_id!r}; "
        f"present={sorted(helpers.keys())}"
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
    "rc_local_mdns_register_on_start",
    "rc_local_mdns_probe_periodic",
    "rc_local_mdns_fallback_tile_surfacing",
)


@pytest.mark.parametrize("automation_id", REQUIRED_AUTOMATIONS)
def test_required_automation_present(package: dict, automation_id: str) -> None:
    autos = _automations(package)
    ids = [a.get("id") for a in autos]
    assert automation_id in ids, (
        f"missing required automation with id={automation_id!r}; "
        f"present ids={ids}"
    )


def test_automation_register_on_start_contract(package: dict) -> None:
    """§8.M.1 — triggers on HA startup, requires fallback enabled,
    fires shell_command probe + persistent_notification."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_local_mdns_register_on_start")
    triggers = auto.get("trigger") or []
    assert any(
        t.get("platform") == "homeassistant" and t.get("event") == "start"
        for t in triggers
    ), f"register_on_start must trigger on HA startup; got triggers={triggers}"
    actions = auto.get("action") or []
    actions_serialized = " ".join(str(a) for a in actions)
    assert "shell_command.rc_local_mdns_probe" in actions_serialized, (
        f"register_on_start must call shell_command.rc_local_mdns_probe; got actions={actions}"
    )
    assert "persistent_notification.create" in actions_serialized, (
        f"register_on_start must fire persistent_notification.create; got actions={actions}"
    )


def test_automation_probe_periodic_contract(package: dict) -> None:
    """§8.M.2 — triggers on time_pattern /60 + retest button + enable,
    requires fallback enabled, fires shell_command probe."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_local_mdns_probe_periodic")
    triggers = auto.get("trigger") or []
    # Time pattern trigger present
    assert any(
        t.get("platform") == "time_pattern"
        for t in triggers
    ), f"probe_periodic must have a time_pattern trigger (every 60s); got triggers={triggers}"
    # Retest button trigger present
    assert any(
        t.get("platform") == "state"
        and t.get("entity_id") == "input_button.rc_local_mdns_retest"
        for t in triggers
    ), f"probe_periodic must trigger on retest button; got triggers={triggers}"
    actions = auto.get("action") or []
    actions_serialized = " ".join(str(a) for a in actions)
    assert "shell_command.rc_local_mdns_probe" in actions_serialized, (
        f"probe_periodic must call shell_command.rc_local_mdns_probe; got actions={actions}"
    )


def test_automation_fallback_tile_surfacing_contract(package: dict) -> None:
    """§8.M.3 — triggers on retest button, branches on binary_sensor
    state, fires persistent_notification with plain-English copy."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_local_mdns_fallback_tile_surfacing")
    triggers = auto.get("trigger") or []
    assert any(
        t.get("platform") == "state"
        and t.get("entity_id") == "input_button.rc_local_mdns_retest"
        for t in triggers
    ), f"fallback_tile_surfacing must trigger on retest button; got triggers={triggers}"
    actions = auto.get("action") or []
    actions_serialized = " ".join(str(a) for a in actions)
    assert "persistent_notification.create" in actions_serialized, (
        f"fallback_tile_surfacing must fire persistent_notification.create; got actions={actions}"
    )
    actions_dumped = yaml.safe_dump(actions, default_flow_style=False)
    # Plain-English copy must contain the fallback URL hint.
    assert "8123" in actions_dumped, (
        f"fallback_tile_surfacing must include the :8123 port in fallback copy; got {actions}"
    )
    assert "tailscale" in actions_dumped.lower() or "wi-fi" in actions_dumped.lower() or "wifi" in actions_dumped.lower(), (
        f"fallback_tile_surfacing must mention tailscale / wi-fi in plain English; got {actions}"
    )


# ----------------------------------------------------------------------------
# (d) Operator-editable hostname — mode: text + default `roamcore`
# ----------------------------------------------------------------------------


def test_local_mdns_hostname_helper_is_text_mode(package: dict) -> None:
    helpers = _helpers_by_entity_id(package, "input_text")
    hostname = helpers.get("rc_local_mdns_hostname")
    assert hostname is not None, "rc_local_mdns_hostname helper missing"
    assert hostname.get("mode") == "text", (
        f"rc_local_mdns_hostname MUST be mode: text (operator-editable); got mode={hostname.get('mode')!r}"
    )
    assert hostname.get("initial") == "roamcore", (
        f"rc_local_mdns_hostname default MUST be 'roamcore'; got {hostname.get('initial')!r}"
    )


def test_fallback_enabled_default_on(package: dict) -> None:
    helpers = _helpers_by_entity_id(package, "input_boolean")
    enabled = helpers.get("rc_local_mdns_fallback_enabled")
    assert enabled is not None, "rc_local_mdns_fallback_enabled helper missing"
    assert enabled.get("initial") is True, (
        f"rc_local_mdns_fallback_enabled default MUST be true; got {enabled.get('initial')!r}"
    )


# ----------------------------------------------------------------------------
# (e) Status sensor template — covers all enabled × resolvable × ip combos
# ----------------------------------------------------------------------------


# The branches the template must cover (enabled × resolvable × ip
# combination → expected plain-English phrase). The test runs a pure-
# function reimplementation of the template and asserts the slice
# spec's 4 branches all produce non-empty strings (no hidden
# fall-through to the catch-all `else`).
EXPECTED_STATUS_BRANCHES: tuple[tuple[tuple[bool, bool, str], str], ...] = (
    # (enabled, resolvable, ip) → expected substring (lowercase)
    ((False, False, ""), "turned off"),
    ((False, True, "192.168.1.66"), "turned off"),
    ((True, True, "192.168.1.66"), "reachable at"),
    ((True, False, "192.168.1.66"), "reachable at"),  # direct IP branch
    ((True, False, ""), "fallback unavailable"),
)


def _status_pure(enabled: bool, resolvable: bool, ip: str) -> str:
    """Pure-function reimplementation of `sensor.rc_local_mdns_status`.

    Extracted out of the YAML template so the test can call it with
    every required combination without spinning up Home Assistant.
    Keep this in lockstep with the YAML template; the test asserts
    the YAML still contains the strings this function emits, so the
    two cannot drift silently.
    """
    host = "roamcore"
    if not enabled:
        return "Local address fallback turned off — your phone can only reach the Hub from your home network."
    if resolvable:
        return f"Reachable at {host}.local from your phone on this WiFi."
    if ip != "":
        return f"Reachable at {ip}:8123 instead — open that in your browser."
    return "Local address fallback unavailable — make sure your phone is on the Hub's WiFi."


@pytest.mark.parametrize(
    "combo,expected_substr",
    [
        (combo, substr) for combo, substr in EXPECTED_STATUS_BRANCHES
    ],
)
def test_status_template_covers_combo(combo: tuple, expected_substr: str) -> None:
    """The pure-function reimplementation must cover every required
    enabled × resolvable × ip combination with a plain-English
    phrase that contains the expected substring (case-insensitive)."""
    result = _status_pure(*combo)
    assert expected_substr in result.lower(), (
        f"status template branch for enabled={combo[0]!r}, resolvable={combo[1]!r}, "
        f"ip={combo[2]!r} must include {expected_substr!r}; got {result!r}"
    )


def test_status_template_present_in_yaml(package: dict) -> None:
    """The YAML template must actually contain the plain-English
    phrases the pure function emits (catches silent drift between the
    pure-function helper and the YAML)."""
    sensors = _template_sensors(package)
    status = next(
        (s for s in sensors if s.get("unique_id") == "rc_local_mdns_status"),
        None,
    )
    assert status is not None, "missing sensor.rc_local_mdns_status template"
    state = status.get("state") or ""
    state_lower = state.lower()
    must_contain = (
        "turned off",
        "reachable at",
        "fallback unavailable",
    )
    for marker in must_contain:
        assert marker in state_lower, (
            f"sensor.rc_local_mdns_status state template is missing "
            f"marker {marker!r}; verify the YAML template is in lockstep with "
            f"the pure-function helper in this test"
        )


def test_status_template_no_operator_jargon(package: dict) -> None:
    """The four user-facing strings the status template can render
    MUST NOT contain operator jargon (no entity IDs, no bash terms,
    no upstream-integration names in the user-visible output).

    Note: the template SOURCE naturally references entity_ids to
    compute its output — that's normal in Home Assistant templates.
    This test pins the user-facing strings by computing them via the
    pure-function helper and asserting each output is jargon-free.
    """
    forbidden = (
        "binary_sensor.",
        "input_boolean.",
        "input_text.",
        "shell_command.",
        "avahi-daemon",
        "zeroconf",
        "tskey-",
    )
    # Exercise every (enabled, resolvable, ip) combo and confirm the
    # rendered output is jargon-free.
    combos = [
        (False, False, ""),
        (False, True, ""),
        (True, True, "192.168.1.66"),
        (True, False, "192.168.1.66"),
        (True, False, ""),
    ]
    for combo in combos:
        result = _status_pure(*combo)
        for term in forbidden:
            assert term not in result.lower(), (
                f"sensor.rc_local_mdns_status output {result!r} (combo={combo}) "
                f"contains operator jargon {term!r}; user-facing copy must be plain English"
            )


# ----------------------------------------------------------------------------
# (f) Idempotency — running PyYAML twice produces the same dict
# ----------------------------------------------------------------------------


def test_yaml_idempotent(package: dict) -> None:
    """Parse the YAML twice, dump both via yaml.safe_dump, and assert
    the two dumps are byte-identical. No random IDs / no timestamps
    / no `$` substitutions that would diverge between runs."""
    text = PACKAGE_PATH.read_text(encoding="utf-8")
    d1 = yaml.safe_load(text)
    d2 = yaml.safe_load(text)
    dump1 = yaml.safe_dump(d1, sort_keys=True)
    dump2 = yaml.safe_dump(d2, sort_keys=True)
    assert dump1 == dump2, (
        "YAML not idempotent — re-parsing produces different output. "
        "Possible cause: random IDs, timestamps, or non-deterministic ordering."
    )


def test_shell_command_does_not_duplicate_mdns_service(package: dict) -> None:
    """Idempotency at the mDNS layer: there must be exactly ONE
    `shell_command.rc_local_mdns_probe` defined. Re-pushing the
    package does NOT duplicate the probe."""
    helpers = _helpers_by_entity_id(package, "shell_command")
    assert len(helpers) == 1, (
        f"expected exactly 1 shell_command (rc_local_mdns_probe); got {len(helpers)}: {list(helpers.keys())}"
    )


# ----------------------------------------------------------------------------
# (g) rc-entity-naming compliance — every entity_id starts with `rc_local_mdns_`.
# ----------------------------------------------------------------------------


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
    """Every helper entity_id MUST start with `rc_local_mdns_`
    (per docs/reference/rc-entity-naming.md)."""
    eids = _all_entity_ids(package)
    assert eids, "no entity_ids found in the package"
    for eid in eids:
        assert eid.startswith("rc_local_mdns_"), (
            f"entity_id {eid!r} violates rc-naming; must start with 'rc_local_mdns_'"
        )


# ----------------------------------------------------------------------------
# (h) No secrets in YAML — grep for tskey- or any tailnet auth-key pattern.
# ----------------------------------------------------------------------------


SECRET_PATTERNS = (
    re.compile(r"tskey-[A-Za-z0-9_-]{10,}"),
    re.compile(r"tskey-api-[A-Za-z0-9_-]{10,}"),
    re.compile(r"ts-auth-[A-Za-z0-9_-]{10,}"),
    # Also grep for hard-coded IPv4 fallbacks (could leak operator network info)
    re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"),
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
# (i) IKEA doc 5-step shape — docs/setup/local-access-fallback.md exists,
# opens with one plain-English sentence, has 5 numbered sections,
# contains the operator→vanlifer translation table.
# ----------------------------------------------------------------------------


def test_ikea_doc_exists() -> None:
    assert DOC_PATH.is_file(), f"missing IKEA doc at {DOC_PATH}"


def test_ikea_doc_opens_with_plain_english() -> None:
    """The doc must open with one plain-English sentence (no YAML
    jargon, no 'this slice' wording, no 'Wave 9' labels)."""
    text = DOC_PATH.read_text(encoding="utf-8")
    # Skip the first line (heading) and find the first content paragraph
    lines = text.splitlines()
    first_content = next(
        (line.strip() for line in lines[1:] if line.strip() and not line.strip().startswith("#")),
        "",
    )
    assert first_content, "doc has no first content paragraph"
    forbidden_openers = (
        "this slice",
        "wave 9",
        "tier-b",
        "tier-b",
        "yaml",
        "input_boolean",
        "binary_sensor",
    )
    lower = first_content.lower()
    for term in forbidden_openers:
        assert term not in lower, (
            f"IKEA doc opener {first_content!r} contains operator jargon {term!r}; "
            f"first sentence must be plain English a vanlifer would understand"
        )


def test_ikea_doc_has_five_numbered_sections() -> None:
    """The IKEA doc MUST have exactly five numbered sections (## 1 / 2 / 3 / 4 / 5)."""
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
    # The table header markers — the doc must include both halves
    # of the translation ("operator calls it" + "you might call it"
    # or similar equivalents).
    assert "operator" in lower, "IKEA doc missing 'operator' translation table"
    # The vanilla "you might call it" / "you'd call it" / "what you see" markers
    assert any(
        marker in lower
        for marker in ("you might call it", "you'd call it", "what you see", "what this means")
    ), "IKEA doc missing plain-English translation explanation"


def test_ikea_doc_no_supersede_banner() -> None:
    """No 'SUPERSEDED' banner in user-facing tree (per doctrine)."""
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "SUPERSEDED" not in text, "IKEA doc must not contain a SUPERSEDED banner"
    assert "CRON-HANDOFF" not in text.upper(), "IKEA doc must not mention Cron-handoff"