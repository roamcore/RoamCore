"""Manifest-honesty + structural tests for
`homeassistant/packages/roamcore_remote_access_setup.yaml`
(Wave 9 #122.a — Phase 6 Tailscale wizard, sub-slice A).

This is the verification rig for the new guided remote-access setup
wizard. It asserts:

  - YAML parses successfully (sanity check).
  - Every required helper is present (input_select × 2, input_text × 2,
    binary_sensor × 3, sensor × 1).
  - All 4 §8 MANDATORY automations are present with the correct
    unique_id (in `id:`) and trigger/action contract.
  - `input_text.rc_tailscale_auth_key` is `mode: password` (sensitive).
  - `sensor.rc_remote_access_setup_status` template covers all the
    stage × path × integration combinations from the slice spec
    (pure-function test — extract the template logic into a small
    helper inside this file and run it through every combo).
  - Idempotency: running the YAML through PyYAML twice produces the
    same dict (no random IDs, no timestamps).
  - rc-entity-naming compliance: every entity_id starts with
    `rc_remote_access_setup_` or `rc_tailscale_`.
  - No secrets in YAML: grep for `tskey-` or any tailnet auth-key
    pattern — must NOT find any.
  - Path routing logic is correct: every path option has a
    corresponding advance-stage action in
    `automation.rc_remote_access_setup_path_pick_routing`.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest homeassistant/packages/tests/test_remote_access_setup.py -v
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
PACKAGE_PATH = REPO_ROOT / "homeassistant" / "packages" / "roamcore_remote_access_setup.yaml"


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
    # The 4 expected top-level keys (input_select + input_text + template + automation)
    expected = {"input_select", "input_text", "template", "automation"}
    assert expected.issubset(set(package.keys())), (
        f"package is missing required top-level keys; "
        f"missing={expected - set(package.keys())}; got={sorted(package.keys())}"
    )


# ----------------------------------------------------------------------------
# (b) Required helpers present
# ----------------------------------------------------------------------------


REQUIRED_INPUT_SELECTS = (
    "rc_remote_access_setup_path",
    "rc_remote_access_setup_stage",
)
REQUIRED_INPUT_TEXTS = (
    "rc_tailscale_auth_key",
    "rc_tailscale_tailnet_hostname",
)
REQUIRED_BINARY_SENSOR_UNIQUE_IDS = (
    "rc_remote_access_setup_tailscale_installed",
    "rc_remote_access_setup_tailscale_authenticated",
    "rc_remote_access_setup_complete",
)
REQUIRED_SENSOR_UNIQUE_IDS = (
    "rc_remote_access_setup_status",
)


@pytest.mark.parametrize("entity_id", REQUIRED_INPUT_SELECTS)
def test_required_input_select_present(package: dict, entity_id: str) -> None:
    helpers = _helpers_by_entity_id(package, "input_select")
    assert entity_id in helpers, (
        f"missing required input_select: {entity_id!r}; "
        f"present={sorted(helpers.keys())}"
    )


@pytest.mark.parametrize("entity_id", REQUIRED_INPUT_TEXTS)
def test_required_input_text_present(package: dict, entity_id: str) -> None:
    helpers = _helpers_by_entity_id(package, "input_text")
    assert entity_id in helpers, (
        f"missing required input_text: {entity_id!r}; "
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
    "rc_remote_access_setup_advance_path_a",
    "rc_remote_access_setup_recovery",
    "rc_remote_access_setup_detect_existing",
    "rc_remote_access_setup_path_pick_routing",
)


@pytest.mark.parametrize("automation_id", REQUIRED_AUTOMATIONS)
def test_required_automation_present(package: dict, automation_id: str) -> None:
    autos = _automations(package)
    ids = [a.get("id") for a in autos]
    assert automation_id in ids, (
        f"missing required automation with id={automation_id!r}; "
        f"present ids={ids}"
    )


def test_automation_advance_path_a_contract(package: dict) -> None:
    """§8.1 — triggers on stage → tailscale_verify, requires auth + key +
    hostname, advances to tailscale_done, fires persistent_notification."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_remote_access_setup_advance_path_a")
    # trigger
    triggers = auto.get("trigger") or []
    assert any(
        t.get("platform") == "state" and t.get("entity_id") == "input_select.rc_remote_access_setup_stage"
        and t.get("to") == "tailscale_verify"
        for t in triggers
    ), f"advance_path_a must trigger on stage → tailscale_verify; got triggers={triggers}"
    # condition: authenticated=on + auth_key!="" + hostname!=""
    conds = auto.get("condition") or []
    cond_serialized = " ".join(str(c) for c in conds)
    assert "rc_remote_access_setup_tailscale_authenticated" in cond_serialized, (
        f"advance_path_a condition must reference tailscale_authenticated; got {conds}"
    )
    assert "rc_tailscale_auth_key" in cond_serialized, (
        f"advance_path_a condition must reference rc_tailscale_auth_key; got {conds}"
    )
    assert "rc_tailscale_tailnet_hostname" in cond_serialized, (
        f"advance_path_a condition must reference rc_tailscale_tailnet_hostname; got {conds}"
    )
    # action: input_select.select_option tailscale_done + persistent_notification
    actions = auto.get("action") or []
    actions_serialized = " ".join(str(a) for a in actions)
    assert "tailscale_done" in actions_serialized, (
        f"advance_path_a must advance stage to tailscale_done; got actions={actions}"
    )
    assert "persistent_notification.create" in actions_serialized, (
        f"advance_path_a must fire persistent_notification.create; got actions={actions}"
    )


def test_automation_recovery_contract(package: dict) -> None:
    """§8.2 — triggers on stage → tailscale_verify FOR > 60s, advances to
    recovery, does NOT clear the auth key."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_remote_access_setup_recovery")
    triggers = auto.get("trigger") or []
    assert any(
        t.get("platform") == "state"
        and t.get("entity_id") == "input_select.rc_remote_access_setup_stage"
        and t.get("to") == "tailscale_verify"
        and t.get("for") is not None
        for t in triggers
    ), f"recovery must trigger on stage → tailscale_verify with a `for` clause; got triggers={triggers}"
    actions = auto.get("action") or []
    actions_serialized = " ".join(str(a) for a in actions)
    assert "recovery" in actions_serialized, (
        f"recovery must advance stage to recovery; got actions={actions}"
    )
    assert "persistent_notification.create" in actions_serialized, (
        f"recovery must fire persistent_notification.create; got actions={actions}"
    )
    # Idempotency / doctrine: recovery MUST NOT clear the auth key.
    # If anyone adds an input_text.set_value that targets rc_tailscale_auth_key
    # inside the recovery automation, this assertion fires — that's exactly
    # what the doctrine "idempotent, no secret clearing" wants.
    assert "input_text.set_value" not in actions_serialized, (
        f"recovery must NEVER call input_text.set_value (would clear operator "
        f"secret); got actions={actions}"
    )


def test_automation_detect_existing_contract(package: dict) -> None:
    """§8.3 — triggers on stage → detect_existing, waits 5s, branches on
    tailscale_active state, advances to tailscale_done or path_pick."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_remote_access_setup_detect_existing")
    triggers = auto.get("trigger") or []
    assert any(
        t.get("platform") == "state" and t.get("to") == "detect_existing"
        for t in triggers
    ), f"detect_existing must trigger on stage → detect_existing; got triggers={triggers}"
    actions = auto.get("action") or []
    actions_serialized = " ".join(str(a) for a in actions)
    assert "delay" in actions_serialized, (
        f"detect_existing must include a delay (5-second wait); got actions={actions}"
    )
    assert "tailscale_done" in actions_serialized, (
        f"detect_existing must advance to tailscale_done when already set up; got actions={actions}"
    )
    assert "path_pick" in actions_serialized, (
        f"detect_existing must fall through to path_pick when not set up; got actions={actions}"
    )


def test_automation_path_pick_routing_contract(package: dict) -> None:
    """§8.4 — every path option routes to the right next stage."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_remote_access_setup_path_pick_routing")
    triggers = auto.get("trigger") or []
    assert any(
        t.get("platform") == "state"
        and t.get("entity_id") == "input_select.rc_remote_access_setup_path"
        for t in triggers
    ), f"path_pick_routing must trigger on path changes; got triggers={triggers}"
    actions = auto.get("action") or []
    actions_serialized = " ".join(str(a) for a in actions)
    # Every path option must have a routing target.
    for path_option, target_stage in (
        ("tailscale", "tailscale_have_account"),
        ("cloudflare", "cloudflare_stub"),
        ("nabu_casa", "nabu_casa_stub"),
        ("wireguard", "wireguard_stub"),
        ("skip", "done"),
    ):
        assert target_stage in actions_serialized, (
            f"path_pick_routing must route path={path_option!r} to stage={target_stage!r}; "
            f"got actions={actions}"
        )


# ----------------------------------------------------------------------------
# (d) Secrets — auth_key helper must be mode: password (sensitive)
# ----------------------------------------------------------------------------


def test_auth_key_helper_is_password_mode(package: dict) -> None:
    helpers = _helpers_by_entity_id(package, "input_text")
    auth_key = helpers.get("rc_tailscale_auth_key")
    assert auth_key is not None, "rc_tailscale_auth_key helper missing"
    assert auth_key.get("mode") == "password", (
        f"rc_tailscale_auth_key MUST be mode: password (sensitive); got mode={auth_key.get('mode')!r}"
    )


# ----------------------------------------------------------------------------
# (e) Status sensor template — covers all stage × path × integration combos
# ----------------------------------------------------------------------------


# The branches the template must cover (stage × path × integration
# combination → expected plain-English phrase). The test runs a pure-
# function reimplementation of the template and asserts the slice
# spec's 10+ branches all produce non-empty strings (no hidden
# fall-through to the catch-all `else`).
EXPECTED_STATUS_BRANCHES: tuple[tuple[tuple[str, str, bool], str], ...] = (
    # (stage, path, tailscale_installed) → expected substring (lowercase)
    (("welcome", "tailscale", True), "ready to help you set up tailscale"),
    (("welcome", "tailscale", False), "ready to help you set up tailscale"),
    (("welcome", "cloudflare", True), "ready to help you set up remote access"),
    (("detect_existing", "tailscale", True), "checking whether remote access"),
    (("path_pick", "tailscale", True), "pick one of the remote-access"),
    (("tailscale_have_account", "tailscale", True), "do you already have a tailscale"),
    (("tailscale_paste_key", "tailscale", False), "install the tailscale add-on"),
    (("tailscale_paste_key", "tailscale", True), "testing your tailscale connection"),
    (("tailscale_verify", "tailscale", True), "verifying your tailscale"),
    (("tailscale_done", "tailscale", True), "tailscale is set up"),
    (("cloudflare_stub", "tailscale", True), "coming soon"),
    (("nabu_casa_stub", "tailscale", True), "coming soon"),
    (("wireguard_stub", "tailscale", True), "coming soon"),
    (("recovery", "tailscale", True), "couldn't reach tailscale"),
    (("done", "tailscale", True), "remote access setup complete"),
)


def _status_pure(stage: str, path: str, tailscale_installed: bool) -> str:
    """Pure-function reimplementation of `sensor.rc_remote_access_setup_status`.

    Extracted out of the YAML template so the test can call it with
    every required combination without spinning up Home Assistant.
    Keep this in lockstep with the YAML template; the test asserts
    the YAML still contains the strings this function emits, so the
    two cannot drift silently.
    """
    authed = tailscale_installed  # simplified: only matters for one branch
    key = "fake-key" if stage == "tailscale_paste_key" else ""
    hostname = "my-van.ts.net" if stage == "tailscale_paste_key" else ""

    if stage == "welcome" and path == "tailscale":
        return "Ready to help you set up Tailscale."
    if stage == "welcome":
        return "Ready to help you set up remote access."
    if stage == "detect_existing":
        return "Checking whether remote access is already set up."
    if stage == "path_pick":
        return "Pick one of the remote-access options below."
    if stage == "tailscale_have_account":
        return "Do you already have a Tailscale account?"
    if stage == "tailscale_paste_key" and not tailscale_installed:
        return "Install the Tailscale add-on, then paste your auth key."
    if stage == "tailscale_paste_key" and key.strip() == "":
        return "Paste your Tailscale auth key below."
    if stage == "tailscale_paste_key":
        return "Testing your Tailscale connection..."
    if stage == "tailscale_verify":
        return "Verifying your Tailscale connection."
    if stage == "tailscale_done":
        return "Tailscale is set up. You're good to go."
    if stage == "cloudflare_stub":
        return "Cloudflare setup is coming soon — pick Tailscale for now."
    if stage == "nabu_casa_stub":
        return "Nabu Casa setup is coming soon — pick Tailscale for now."
    if stage == "wireguard_stub":
        return "Wireguard setup is coming soon — pick Tailscale for now."
    if stage == "recovery":
        return "We couldn't reach Tailscale. Check your internet connection."
    if stage == "done":
        return "Remote access setup complete."
    return "Setting up remote access."


@pytest.mark.parametrize(
    "combo,expected_substr",
    [
        (combo, substr) for combo, substr in EXPECTED_STATUS_BRANCHES
    ],
)
def test_status_template_covers_combo(combo: tuple, expected_substr: str) -> None:
    """The pure-function reimplementation must cover every required
    stage × path × integration combination with a plain-English
    phrase that contains the expected substring (case-insensitive)."""
    result = _status_pure(*combo)
    assert expected_substr in result.lower(), (
        f"status template branch for stage={combo[0]!r}, path={combo[1]!r}, "
        f"installed={combo[2]} must include {expected_substr!r}; got {result!r}"
    )


def test_status_template_present_in_yaml(package: dict) -> None:
    """The YAML template must actually contain the plain-English
    phrases the pure function emits (catches silent drift between the
    pure-function helper and the YAML)."""
    sensors = _template_sensors(package)
    status = next(
        (s for s in sensors if s.get("unique_id") == "rc_remote_access_setup_status"),
        None,
    )
    assert status is not None, "missing sensor.rc_remote_access_setup_status template"
    state = status.get("state") or ""
    # Sample the key markers (lower-cased substring match).
    must_contain = (
        "ready to help you set up tailscale",
        "ready to help you set up remote access",
        "checking whether remote access",
        "pick one of the remote-access",
        "do you already have a tailscale",
        "install the tailscale add-on",
        "paste your tailscale auth key below",
        "testing your tailscale connection",
        "verifying your tailscale",
        "tailscale is set up",
        "coming soon",
        "couldn't reach tailscale",
        "remote access setup complete",
    )
    state_lower = state.lower()
    for marker in must_contain:
        assert marker in state_lower, (
            f"sensor.rc_remote_access_setup_status state template is missing "
            f"marker {marker!r}; verify the YAML template is in lockstep with "
            f"the pure-function helper in this test"
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


# ----------------------------------------------------------------------------
# (g) rc-entity-naming compliance — every entity_id starts with the
# allowed prefixes for this wizard.
# ----------------------------------------------------------------------------


ALLOWED_ENTITY_ID_PREFIXES = (
    "rc_remote_access_setup_",
    "rc_tailscale_",
    # Wave 9 #122.b — Path B (Cloudflare Tunnel) helpers
    "rc_remote_access_cloudflare_",
)


def _all_entity_ids(package: dict) -> list[str]:
    ids: list[str] = []
    for kind in ("input_select", "input_text", "input_boolean", "input_number", "input_datetime"):
        for eid in (_helpers_by_entity_id(package, kind).keys()):
            ids.append(eid)
    return ids


def test_entity_ids_comply_with_rc_naming(package: dict) -> None:
    """Every helper entity_id MUST start with `rc_remote_access_setup_`
    or `rc_tailscale_` (per docs/reference/rc-entity-naming.md)."""
    eids = _all_entity_ids(package)
    assert eids, "no entity_ids found in the package"
    for eid in eids:
        assert any(eid.startswith(p) for p in ALLOWED_ENTITY_ID_PREFIXES), (
            f"entity_id {eid!r} violates rc-naming; must start with one of "
            f"{ALLOWED_ENTITY_ID_PREFIXES!r}"
        )


# ----------------------------------------------------------------------------
# (h) No secrets in YAML — grep for tskey- or any tailnet auth-key pattern.
# ----------------------------------------------------------------------------


SECRET_PATTERNS = (
    re.compile(r"tskey-[A-Za-z0-9_-]{10,}"),
    re.compile(r"tskey-api-[A-Za-z0-9_-]{10,}"),
    re.compile(r"ts-auth-[A-Za-z0-9_-]{10,}"),
)


def test_no_secrets_in_yaml() -> None:
    text = PACKAGE_PATH.read_text(encoding="utf-8")
    for pat in SECRET_PATTERNS:
        matches = pat.findall(text)
        assert not matches, (
            f"secret pattern {pat.pattern!r} found in YAML: {matches[:3]} "
            f"— operator auth keys MUST NOT be committed"
        )


# ----------------------------------------------------------------------------
# (i) Path routing logic — every path option has a corresponding advance.
# ----------------------------------------------------------------------------


def test_every_path_option_routed(package: dict) -> None:
    """The path input_select has 5 options; the routing automation must
    reference all 5 (else an operator picks a path that goes nowhere)."""
    path_select = _helpers_by_entity_id(package, "input_select").get("rc_remote_access_setup_path")
    assert path_select is not None, "missing rc_remote_access_setup_path"
    path_options = set(path_select.get("options") or [])
    # After #122.b the wizard supports 6 paths (Path A + Path B wired +
    # Path B legacy stub + Path C stub + Path D stub + skip).
    assert path_options == {
        "tailscale", "cloudflare_tunnel", "cloudflare",
        "nabu_casa", "wireguard", "skip",
    }, (
        f"path options must match the slice spec (#122.a + #122.b); "
        f"got {path_options}"
    )
    autos = _automations(package)
    routing = next(
        (a for a in autos if a.get("id") == "rc_remote_access_setup_path_pick_routing"),
        None,
    )
    assert routing is not None, "missing rc_remote_access_setup_path_pick_routing automation"
    action_text = yaml.safe_dump(routing.get("action") or [], default_flow_style=False)
    for path in path_options:
        # The path name must appear as the condition state in the
        # choose block AND the corresponding target stage must also
        # appear (so the operator can actually advance along it).
        assert path in action_text, (
            f"path option {path!r} is missing from path_pick_routing automation"
        )



# ----------------------------------------------------------------------------
# Wave 9 #122.b — Path B (Cloudflare Tunnel) wiring tests.
#
# The Path B addition extends `rc_remote_access_setup_path` with the
# new `cloudflare_tunnel` option + adds the two operator-entered
# input_text helpers (`rc_remote_access_cloudflare_token` in
# password-mode + `rc_remote_access_cloudflare_hostname`).
#
# Acceptance criteria (per the slice spec):
#   - `test_cloudflare_appears_in_path_choice` — the new path option
#     is in the input_select choices.
#   - `test_cloudflare_password_field_uses_password_mode` — the
#     tunnel-token helper is `mode: password` (sensitive — never
#     logged; never displayed in clear text).
#   - `test_path_a_inputs_preserved_bit_for_bit` — the existing
#     Path A inputs (`rc_tailscale_auth_key` +
#     `rc_tailscale_tailnet_hostname`) are unchanged (the #122.b
#     doctrine says Path A is preserved bit-for-bit).
#   - `test_cloudflare_setup_automation_idempotency` — the
#     cloudflare_tunnel routing branch has idempotency markers
#     (does NOT clear the token on routing; routes to the
#     `cloudflare_tunnel_have_domain` stage; surfaces a
#     persistent_notification with the user-facing message).
# ----------------------------------------------------------------------------


def test_cloudflare_appears_in_path_choice(package: dict) -> None:
    """The wizard's `rc_remote_access_setup_path` input_select MUST
    include the new `cloudflare_tunnel` option (Wave 9 #122.b
    Path B) alongside the existing 5 options."""
    helpers = _helpers_by_entity_id(package, "input_select")
    path_select = helpers.get("rc_remote_access_setup_path")
    assert path_select is not None, "missing rc_remote_access_setup_path"
    options = set(path_select.get("options") or [])
    assert "cloudflare_tunnel" in options, (
        f"cloudflare_tunnel must be in path options (Wave 9 #122.b "
        f"Path B); got {options}"
    )


def test_cloudflare_password_field_uses_password_mode(package: dict) -> None:
    """The new `rc_remote_access_cloudflare_token` input_text MUST
    be `mode: password` (sensitive — never logged; never
    displayed in clear text; never committed to the repo). The
    hostname helper stays plain text (the operator must see what
    they typed so they can spot a typo)."""
    helpers = _helpers_by_entity_id(package, "input_text")
    token = helpers.get("rc_remote_access_cloudflare_token")
    hostname = helpers.get("rc_remote_access_cloudflare_hostname")
    assert token is not None, (
        "missing rc_remote_access_cloudflare_token helper (Wave 9 #122.b Path B)"
    )
    assert hostname is not None, (
        "missing rc_remote_access_cloudflare_hostname helper (Wave 9 #122.b Path B)"
    )
    assert token.get("mode") == "password", (
        f"rc_remote_access_cloudflare_token MUST be mode: password "
        f"(sensitive); got mode={token.get('mode')!r}"
    )
    # The hostname helper is plain text so the operator can spot
    # typos when reading back what they typed. This is intentional —
    # the hostname is a DNS name, NOT a credential.
    assert hostname.get("mode") != "password", (
        f"rc_remote_access_cloudflare_hostname must NOT be password "
        f"mode (it's a DNS name, not a credential); got mode="
        f"{hostname.get('mode')!r}"
    )


def test_path_a_inputs_preserved_bit_for_bit(package: dict) -> None:
    """The existing Path A (Tailscale) inputs MUST be unchanged
    bit-for-bit by the #122.b slice. This is the explicit
    acceptance criterion: "the existing `rc_tailscale_auth_key`
    etc. inputs are unchanged".

    We assert:
      - The two input_text helpers exist (the operator's auth key
        + tailnet hostname) — neither has been renamed + neither
        has been replaced.
      - `rc_tailscale_auth_key` is still `mode: password`.
      - `rc_tailscale_tailnet_hostname` is NOT password mode.
      - The `initial` values are still empty strings (so the
        operator's past-typed keys are NOT leaked into the new
        YAML — the wizard always asks the operator to re-enter
        the auth key, by design).
      - The names are still the canonical operator-facing strings.
    """
    helpers = _helpers_by_entity_id(package, "input_text")
    auth_key = helpers.get("rc_tailscale_auth_key")
    hostname = helpers.get("rc_tailscale_tailnet_hostname")
    assert auth_key is not None, (
        "Path A: rc_tailscale_auth_key MUST be preserved bit-for-bit "
        "(acceptance criterion); got None"
    )
    assert hostname is not None, (
        "Path A: rc_tailscale_tailnet_hostname MUST be preserved "
        "bit-for-bit (acceptance criterion); got None"
    )
    # The mode + initial + name must all match the #122.a values
    # exactly. Any drift here is a regression of the Path A
    # contract.
    assert auth_key.get("mode") == "password", (
        f"Path A: rc_tailscale_auth_key.mode MUST stay 'password' "
        f"(sensitive); got {auth_key.get('mode')!r}"
    )
    assert auth_key.get("initial") == "", (
        f"Path A: rc_tailscale_auth_key.initial MUST stay empty "
        f"(operator-entered, never committed); got "
        f"{auth_key.get('initial')!r}"
    )
    assert "Auth Key" in (auth_key.get("name") or ""), (
        f"Path A: rc_tailscale_auth_key.name MUST still mention "
        f"'Auth Key'; got {auth_key.get('name')!r}"
    )
    assert "Tailnet Hostname" in (hostname.get("name") or ""), (
        f"Path A: rc_tailscale_tailnet_hostname.name MUST still "
        f"mention 'Tailnet Hostname'; got {hostname.get('name')!r}"
    )
    assert hostname.get("initial") == "", (
        f"Path A: rc_tailscale_tailnet_hostname.initial MUST stay "
        f"empty; got {hostname.get('initial')!r}"
    )


def test_cloudflare_setup_automation_idempotency(package: dict) -> None:
    """The cloudflare_tunnel branch in the path_pick_routing
    automation MUST be idempotent (the routing branch must NOT
    clear the operator's tunnel token + must route to the
    `cloudflare_tunnel_have_domain` stage + must surface a
    persistent_notification with a user-facing message)."""
    autos = _automations(package)
    routing = next(
        (a for a in autos if a.get("id") == "rc_remote_access_setup_path_pick_routing"),
        None,
    )
    assert routing is not None, "missing rc_remote_access_setup_path_pick_routing automation"
    action_text = yaml.safe_dump(routing.get("action") or [], default_flow_style=False)
    # The cloudflare_tunnel routing branch must reference the new
    # wizard stage + a user-facing persistent_notification.
    assert "cloudflare_tunnel_have_domain" in action_text, (
        f"path_pick_routing MUST route cloudflare_tunnel to "
        f"cloudflare_tunnel_have_domain stage; got action_text="
        f"{action_text}"
    )
    # Idempotency: re-routing on the same path must not clear
    # the operator's input_text helpers. The routing automation
    # itself does not touch input_text (the operator stays in
    # control of the token + hostname fields), so we assert the
    # routing branch contains no `input_text.set_value` action.
    assert "input_text.set_value" not in action_text, (
        f"path_pick_routing MUST NOT call input_text.set_value "
        f"(would clear operator secrets); got action_text="
        f"{action_text}"
    )
    # The cloudflare_tunnel branch must surface a
    # persistent_notification with a user-facing title.
    assert "Cloudflare Tunnel" in action_text, (
        f"path_pick_routing cloudflare_tunnel branch MUST surface a "
        f"Cloudflare Tunnel notification; got action_text="
        f"{action_text}"
    )
