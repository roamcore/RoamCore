"""Manifest-honesty + structural tests for
`homeassistant/packages/roamcore_remote_access_setup.yaml`
(Wave 9 #122.a + #122.d.i — Phase 6 Tailscale wizard: Path A Tailscale,
Path D Wireguard, Path B/C stubs).

This is the verification rig for the new guided remote-access setup
wizard. It asserts:

  - YAML parses successfully (sanity check).
  - Every required helper is present (input_select × 2, input_text × 6,
    binary_sensor × 5, sensor × 1).
  - All 7 §8 MANDATORY automations are present with the correct
    unique_id (in `id:`) and trigger/action contract.
  - `input_text.rc_tailscale_auth_key` is `mode: password` (sensitive).
  - `input_text.rc_wireguard_server_endpoint` +
    `rc_wireguard_server_public_key` +
    `rc_wireguard_peer_private_key` +
    `rc_wireguard_peer_allowed_ips` are all `mode: password` (sensitive).
  - `sensor.rc_remote_access_setup_status` template covers all the
    stage × path × integration combinations from the slice spec
    (pure-function test — extract the template logic into a small
    helper inside this file and run it through every combo).
  - Idempotency: running the YAML through PyYAML twice produces the
    same dict (no random IDs, no timestamps).
  - rc-entity-naming compliance: every entity_id starts with
    `rc_remote_access_setup_`, `rc_tailscale_`, or `rc_wireguard_`.
  - No secrets in YAML: grep for `tskey-` or any tailnet auth-key
    pattern — must NOT find any.
  - No Wireguard hardcoded secrets (private keys, public keys,
    server endpoints, allowed IP ranges).
  - Path routing logic is correct: every path option has a
    corresponding advance-stage action in
    `automation.rc_remote_access_setup_path_pick_routing`.
  - Path D recovery automation NEVER calls `input_text.set_value`
    targeting any of the four Wireguard helpers (operator can
    retry without re-typing).

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
    "rc_wireguard_server_endpoint",
    "rc_wireguard_server_public_key",
    "rc_wireguard_peer_private_key",
    "rc_wireguard_peer_allowed_ips",
)
REQUIRED_BINARY_SENSOR_UNIQUE_IDS = (
    "rc_remote_access_setup_tailscale_installed",
    "rc_remote_access_setup_tailscale_authenticated",
    "rc_remote_access_setup_complete",
    "rc_remote_access_setup_wireguard_installed",
    "rc_remote_access_setup_wireguard_active",
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
    "rc_remote_access_setup_advance_path_d",
    "rc_remote_access_setup_recovery_wireguard",
    "rc_remote_access_setup_detect_existing_wireguard",
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
        ("wireguard", "wireguard_have_server"),
        ("skip", "done"),
    ):
        assert target_stage in actions_serialized, (
            f"path_pick_routing must route path={path_option!r} to stage={target_stage!r}; "
            f"got actions={actions}"
        )


def test_automation_advance_path_d_contract(package: dict) -> None:
    """§8.5 — Path D advance: triggers on stage → wireguard_verify,
    requires Wireguard active + endpoint + server public key + peer
    private key + peer allowed IPs + path=wireguard, advances to
    wireguard_done, fires persistent_notification."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_remote_access_setup_advance_path_d")
    triggers = auto.get("trigger") or []
    assert any(
        t.get("platform") == "state"
        and t.get("entity_id") == "input_select.rc_remote_access_setup_stage"
        and t.get("to") == "wireguard_verify"
        for t in triggers
    ), f"advance_path_d must trigger on stage → wireguard_verify; got triggers={triggers}"
    conds = auto.get("condition") or []
    cond_serialized = " ".join(str(c) for c in conds)
    assert "rc_remote_access_setup_wireguard_active" in cond_serialized, (
        f"advance_path_d condition must reference wireguard_active; got {conds}"
    )
    assert "rc_wireguard_server_endpoint" in cond_serialized, (
        f"advance_path_d condition must reference rc_wireguard_server_endpoint; got {conds}"
    )
    assert "rc_wireguard_server_public_key" in cond_serialized, (
        f"advance_path_d condition must reference rc_wireguard_server_public_key; got {conds}"
    )
    assert "rc_wireguard_peer_private_key" in cond_serialized, (
        f"advance_path_d condition must reference rc_wireguard_peer_private_key; got {conds}"
    )
    assert "rc_wireguard_peer_allowed_ips" in cond_serialized, (
        f"advance_path_d condition must reference rc_wireguard_peer_allowed_ips; got {conds}"
    )
    actions = auto.get("action") or []
    actions_serialized = " ".join(str(a) for a in actions)
    assert "wireguard_done" in actions_serialized, (
        f"advance_path_d must advance stage to wireguard_done; got actions={actions}"
    )
    # The advance MUST also flip the global setup-wizard past
    # `networking` so the operator can move on to `map` (this is
    # what the rc_setup_advance_after_remote_access automation
    # depends on for the done-transition wired in
    # `roamcore_setup_wizard.yaml`).
    assert "rc_setup_stage" in actions_serialized, (
        f"advance_path_d must advance rc_setup_stage (so the global "
        f"setup wizard moves past networking); got actions={actions}"
    )
    assert "persistent_notification.create" in actions_serialized, (
        f"advance_path_d must fire persistent_notification.create; got actions={actions}"
    )
    assert "input_text.set_value" not in actions_serialized, (
        f"advance_path_d must NEVER call input_text.set_value (would clear "
        f"operator secrets); got actions={actions}"
    )


def test_automation_recovery_wireguard_contract(package: dict) -> None:
    """§8.6 — Wireguard recovery: triggers on stage → wireguard_verify
    FOR > 60s, advances to recovery, does NOT clear any of the four
    Wireguard peer helpers."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_remote_access_setup_recovery_wireguard")
    triggers = auto.get("trigger") or []
    assert any(
        t.get("platform") == "state"
        and t.get("entity_id") == "input_select.rc_remote_access_setup_stage"
        and t.get("to") == "wireguard_verify"
        and t.get("for") is not None
        for t in triggers
    ), f"recovery_wireguard must trigger on stage → wireguard_verify with a `for` clause; got triggers={triggers}"
    actions = auto.get("action") or []
    actions_serialized = " ".join(str(a) for a in actions)
    assert "recovery" in actions_serialized, (
        f"recovery_wireguard must advance stage to recovery; got actions={actions}"
    )
    # Plain-English error copy: NOT "wg-quick: interface not found", NOT
    # "errno: ENETUNREACH".
    # Idempotent: never clears any of the four Wireguard peer helpers
    # (so the operator can retry without re-typing them).
    assert "input_text.set_value" not in actions_serialized, (
        f"recovery_wireguard must NEVER call input_text.set_value (would "
        f"clear operator-entered Wireguard keys); got actions={actions}"
    )
    # Must NOT reference upstream service codes in the message — the
    # plain-English "check that the server is reachable from your van's
    # internet connection and that UDP 51820 is open" hint is required.
    action_dump = yaml.safe_dump(actions, default_flow_style=False)
    assert "udp 51820" in action_dump.lower() or "UDP 51820" in action_dump, (
        f"recovery_wireguard must surface a plain-English nudge about UDP "
        f"51820 (not 'wg-quick: interface not found' or 'errno: ENETUNREACH'); "
        f"got actions={action_dump}"
    )


def test_automation_detect_existing_wireguard_contract(package: dict) -> None:
    """§8.7 — Path D detect existing: triggers on stage → detect_existing,
    waits 5s, branches on wireguard_active state, advances to
    wireguard_done or path_pick."""
    autos = _automations(package)
    auto = next(a for a in autos if a.get("id") == "rc_remote_access_setup_detect_existing_wireguard")
    triggers = auto.get("trigger") or []
    assert any(
        t.get("platform") == "state" and t.get("to") == "detect_existing"
        for t in triggers
    ), f"detect_existing_wireguard must trigger on stage → detect_existing; got triggers={triggers}"
    actions = auto.get("action") or []
    actions_serialized = " ".join(str(a) for a in actions)
    assert "delay" in actions_serialized, (
        f"detect_existing_wireguard must include a delay (5-second wait); got actions={actions}"
    )
    assert "wireguard_done" in actions_serialized, (
        f"detect_existing_wireguard must advance to wireguard_done when "
        f"already set up; got actions={actions}"
    )
    assert "path_pick" in actions_serialized, (
        f"detect_existing_wireguard must fall through to path_pick when not "
        f"set up; got actions={actions}"
    )


# ----------------------------------------------------------------------------
# (d) Secrets — auth_key + Wireguard helpers must be mode: password (sensitive)
# ----------------------------------------------------------------------------


def test_auth_key_helper_is_password_mode(package: dict) -> None:
    helpers = _helpers_by_entity_id(package, "input_text")
    auth_key = helpers.get("rc_tailscale_auth_key")
    assert auth_key is not None, "rc_tailscale_auth_key helper missing"
    assert auth_key.get("mode") == "password", (
        f"rc_tailscale_auth_key MUST be mode: password (sensitive); got mode={auth_key.get('mode')!r}"
    )


def test_wireguard_helpers_are_password_mode(package: dict) -> None:
    """All four Path D Wireguard helpers MUST be `mode: password`
    (sensitive — peer private keys are secrets; server endpoint +
    server public key + peer allowed IPs are operator-typed values
    we keep masked for visual consistency with the private key)."""
    helpers = _helpers_by_entity_id(package, "input_text")
    for eid in (
        "rc_wireguard_server_endpoint",
        "rc_wireguard_server_public_key",
        "rc_wireguard_peer_private_key",
        "rc_wireguard_peer_allowed_ips",
    ):
        h = helpers.get(eid)
        assert h is not None, f"Wireguard helper {eid!r} missing"
        assert h.get("mode") == "password", (
            f"Wireguard helper {eid!r} MUST be mode: password (sensitive); "
            f"got mode={h.get('mode')!r}"
        )


# ----------------------------------------------------------------------------
# (e) Status sensor template — covers all stage × path × integration combos
# ----------------------------------------------------------------------------


# The branches the template must cover (stage × path × integration
# combination → expected plain-English phrase). The test runs a pure-
# function reimplementation of the template and asserts the slice
# spec's branches all produce non-empty strings (no hidden
# fall-through to the catch-all `else`).
#
# `wg_installed` is a generic "is the Wireguard integration installed"
# gate that drives the Path D flow.
EXPECTED_STATUS_BRANCHES: tuple[tuple[tuple, str], ...] = (
    # (stage, path, tailscale_installed, wireguard_installed) → expected substring (lowercase)
    # Tailscale (Path A) flow
    (("welcome", "tailscale", True, False), "ready to help you set up tailscale"),
    (("welcome", "tailscale", False, False), "ready to help you set up tailscale"),
    (("welcome", "wireguard", False, True), "ready to help you set up wireguard"),
    (("welcome", "wireguard", False, False), "ready to help you set up wireguard"),
    (("welcome", "cloudflare", True, False), "ready to help you set up remote access"),
    (("detect_existing", "tailscale", True, False), "checking whether remote access"),
    (("path_pick", "tailscale", True, False), "pick one of the remote-access"),
    (("tailscale_have_account", "tailscale", True, False), "do you already have a tailscale"),
    (("tailscale_paste_key", "tailscale", False, False), "install the tailscale add-on"),
    (("tailscale_paste_key", "tailscale", True, False), "testing your tailscale connection"),
    (("tailscale_verify", "tailscale", True, False), "verifying your tailscale"),
    (("tailscale_done", "tailscale", True, False), "tailscale is set up"),
    (("cloudflare_stub", "tailscale", True, False), "coming soon"),
    (("nabu_casa_stub", "tailscale", True, False), "coming soon"),
    # Wireguard (Path D) flow
    (("wireguard_have_server", "wireguard", False, True), "do you already run your own wireguard"),
    (("wireguard_paste_keys", "wireguard", False, False), "install the wireguard add-on"),
    (("wireguard_paste_keys", "wireguard", False, True, "partial"), "paste your wireguard server endpoint"),
    (("wireguard_paste_keys", "wireguard", False, True, "full"), "testing your wireguard connection"),
    (("wireguard_verify", "wireguard", False, True), "verifying your wireguard"),
    (("wireguard_done", "wireguard", False, True), "wireguard is set up"),
    # Recovery / done
    (("recovery", "tailscale", True, False), "couldn't reach your remote-access server"),
    (("recovery", "wireguard", False, True), "couldn't reach your remote-access server"),
    (("done", "tailscale", True, False), "remote access setup complete"),
    (("done", "wireguard", False, True), "remote access setup complete"),
)


def _status_pure(stage: str, path: str, tailscale_installed: bool, wireguard_installed: bool, wg_keys: str = "full") -> str:
    """Pure-function reimplementation of `sensor.rc_remote_access_setup_status`.

    Extracted out of the YAML template so the test can call it with
    every required combination without spinning up Home Assistant.
    Keep this in lockstep with the YAML template; the test asserts
    the YAML still contains the strings this function emits, so the
    two cannot drift silently.

    `tailscale_installed` drives the Path A Tailscale flow;
    `wireguard_installed` drives the Path D Wireguard flow. When
    `tailscale_installed=True`, the auth key is assumed to be filled
    (idempotent re-typing); same for the Wireguard peer keys when
    `wireguard_installed=True`. This is a simplification that matches
    the YAML template's per-flow branches.

    `wg_keys` is "full" (all 4 wireguard keys filled), "partial" (at
    least one key empty — the wizard should prompt the operator to
    fill in the missing details), or "empty" (all 4 keys empty —
    the wizard should prompt the operator to type them in).
    """
    # The Tailscale branch's "key | trim == ''" check: the YAML uses
    # `states('input_text.rc_tailscale_auth_key')` directly, which is
    # empty when the operator hasn't typed one yet. The pure function
    # assumes the key is empty UNLESS the wizard is on the
    # tailscale_paste_key stage AND installed=True (i.e. add-on is
    # installed, so the operator has presumably typed one).
    key = "fake-key" if (stage == "tailscale_paste_key" and tailscale_installed) else ""
    # Same shape for the Wireguard branch — fill in keys per the
    # wg_keys parameter.
    if stage == "wireguard_paste_keys" and wireguard_installed:
        if wg_keys == "full":
            wg_endpoint = "wg.example.com:51820"
            wg_server_pub = "fake-server-pub-key"
            wg_peer_priv = "fake-peer-priv-key"
            wg_peer_ips = "10.0.0.2/32"
        elif wg_keys == "partial":
            # Endpoint filled, but peer private key empty.
            wg_endpoint = "wg.example.com:51820"
            wg_server_pub = "fake-server-pub-key"
            wg_peer_priv = ""
            wg_peer_ips = "10.0.0.2/32"
        else:  # empty
            wg_endpoint = ""
            wg_server_pub = ""
            wg_peer_priv = ""
            wg_peer_ips = ""
    else:
        wg_endpoint = ""
        wg_server_pub = ""
        wg_peer_priv = ""
        wg_peer_ips = ""

    if stage == "welcome" and path == "tailscale":
        return "Ready to help you set up Tailscale."
    if stage == "welcome" and path == "wireguard":
        return "Ready to help you set up Wireguard."
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
    if stage == "wireguard_have_server":
        return "Do you already run your own Wireguard VPN?"
    if stage == "wireguard_paste_keys" and not wireguard_installed:
        return "Install the Wireguard add-on, then paste your server details."
    if stage == "wireguard_paste_keys" and (
        wg_endpoint.strip() == ""
        or wg_server_pub.strip() == ""
        or wg_peer_priv.strip() == ""
        or wg_peer_ips.strip() == ""
    ):
        return "Paste your Wireguard server endpoint, public key, peer private key, and allowed IPs."
    if stage == "wireguard_paste_keys":
        return "Testing your Wireguard connection..."
    if stage == "wireguard_verify":
        return "Verifying your Wireguard connection."
    if stage == "wireguard_done":
        return "Wireguard is set up. You're good to go."
    if stage == "recovery":
        return "We couldn't reach your remote-access server. Check your internet connection."
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
        f"status template branch for combo={combo!r} must "
        f"include {expected_substr!r}; got {result!r}"
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
        "ready to help you set up wireguard",
        "checking whether remote access",
        "pick one of the remote-access",
        "do you already have a tailscale",
        "install the tailscale add-on",
        "paste your tailscale auth key below",
        "testing your tailscale connection",
        "verifying your tailscale",
        "tailscale is set up",
        "do you already run your own wireguard vpn",
        "install the wireguard add-on",
        "paste your wireguard server endpoint",
        "testing your wireguard connection",
        "verifying your wireguard",
        "wireguard is set up",
        "coming soon",
        "couldn't reach your remote-access server",
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
    "rc_wireguard_",
)


def _all_entity_ids(package: dict) -> list[str]:
    ids: list[str] = []
    for kind in ("input_select", "input_text", "input_boolean", "input_number", "input_datetime"):
        for eid in (_helpers_by_entity_id(package, kind).keys()):
            ids.append(eid)
    return ids


def test_entity_ids_comply_with_rc_naming(package: dict) -> None:
    """Every helper entity_id MUST start with `rc_remote_access_setup_`,
    `rc_tailscale_`, or `rc_wireguard_` (per docs/reference/rc-entity-
    naming.md)."""
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
# (i) No Wireguard hardcoded secrets — peer private keys + server public
# keys + server endpoints + allowed IP ranges must NEVER appear in the YAML.
# ----------------------------------------------------------------------------


# Wireguard private keys are 44-character base64 strings ending in `=`
# (the trailing base64 padding). Wireguard public keys are the same
# length without the trailing `=`. We block any base64-looking 40+ char
# block in the YAML unless it's wrapped in our own quote-protected
# `name:` field (the helper names themselves are operator-visible
# strings, not secrets). The `name:` fields are allowlisted below.
WIREGUARD_SECRET_PATTERNS = (
    # Private key: 43-char base64 + trailing `=` (operator's actual key).
    # We catch the actual 44-character base64 block here.
    re.compile(r"\b[A-Za-z0-9+/]{40,}=(?:\s|$|\")"),
    # Public key: 43-char base64 (no trailing `=`).
    re.compile(r"\b[A-Za-z0-9+/]{43}(?=\s|$|\")"),
    # IPv4 CIDR ranges commonly used as peer allowed_ips (10.x, 192.168.x,
    # 172.16-31.x) — operator's actual network configuration. The YAML
    # must NOT hardcode a specific operator's allowed_ips.
    re.compile(r"\b(?:10|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}\b"),
    # Real-looking Wireguard server endpoints (FQDN:port or IP:port with
    # 4-digit port — the default Wireguard port 51820 is operator-specific
    # when used with a real domain).
    re.compile(r"\b(?:wg|vpn|wireguard)\.[a-z0-9.-]+\.(?:com|net|org|io):\d{4,5}\b", re.IGNORECASE),
)


# Allowlist substrings — strings that legitimately appear in the YAML
# and would otherwise trigger the regex. These are public-portal
# references + operator-visible name fields.
ALLOWED_WIREGUARD_PHRASES = (
    # The 4 input_text helper `name:` fields (operator-visible strings).
    "RC Wireguard Server Endpoint (e.g. wg.example.com:51820",
    "RC Wireguard Peer Allowed IPs (e.g. 10.0.0.2/32",
    # Public-portal-style references that are intentionally user-facing
    # copy in the recovery notice.
)


def test_no_wireguard_hardcoded_secrets_in_yaml() -> None:
    """Operator Wireguard credentials MUST NEVER appear in this YAML.
    The wizard exposes them as four `input_text.rc_wireguard_*`
    helpers (all `mode: password`) and reads the active state from
    the upstream HA Core `wireguard` integration. Hardcoding a
    server endpoint / peer private key / allowed IP range would
    both (a) leak an operator's VPN configuration + (b) be a tier
    promotion we explicitly do NOT ship at tier-b."""
    text = PACKAGE_PATH.read_text(encoding="utf-8")
    # Strip the allowlist phrases from the text before running the
    # regexes, so legitimate `name:` field examples don't trip the
    # guard.
    scrubbed = text
    for phrase in ALLOWED_WIREGUARD_PHRASES:
        scrubbed = scrubbed.replace(phrase, "")
    for pat in WIREGUARD_SECRET_PATTERNS:
        matches = pat.findall(scrubbed)
        assert not matches, (
            f"hardcoded Wireguard secret pattern {pat.pattern!r} found in "
            f"YAML: {matches[:3]} — operator VPN credentials MUST NOT be "
            f"committed"
        )


# ----------------------------------------------------------------------------
# (j) Path routing logic — every path option has a corresponding advance.
# ----------------------------------------------------------------------------


def test_every_path_option_routed(package: dict) -> None:
    """The path input_select has 5 options; the routing automation must
    reference all 5 (else an operator picks a path that goes nowhere)."""
    path_select = _helpers_by_entity_id(package, "input_select").get("rc_remote_access_setup_path")
    assert path_select is not None, "missing rc_remote_access_setup_path"
    path_options = set(path_select.get("options") or [])
    assert path_options == {"tailscale", "cloudflare", "nabu_casa", "wireguard", "skip"}, (
        f"path options must match the slice spec; got {path_options}"
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
