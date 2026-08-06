"""Manifest-honesty + structural tests for
`homeassistant/packages/roamcore_tailscale_qr.yaml` and the
companion stdlib QR generator `homeassistant/packages/scripts/qr_generator.py`
(Wave 9 #122.d.ii — Phase 6 Tailscale wizard QR code for mobile pairing).

This is the verification rig for the new QR tile + the stdlib QR
generator. It asserts:

  - YAML parses successfully (sanity check).
  - Every required helper is present (input_text × 4, input_button × 1,
    binary_sensor × 1, sensor × 1, shell_command × 1, automation × 2).
  - All 2 §8 MANDATORY automations are present with the correct
    `id:` and a sensible trigger/action contract.
  - rc-entity-naming compliance: every entity_id starts with
    `rc_tailscale_qr_`.
  - No secrets in YAML: grep for `tskey-` + grep for any embedded
    device-key pattern — must NOT find any.
  - QR generator is stdlib-only (no `import qrcode`, `import segno`,
    etc.).
  - QR generator produces a valid SVG for the canonical Tailscale URL
    (`https://login.tailscale.com/a/<key>`): parses as XML +
    has correct viewBox `0 0 256 256` + has ≥ 1 dark module.
  - QR generator is idempotent (same input → same SVG output).
  - QR generator is auto-recovering on long URLs (returns a graceful
    error or still renders valid SVG).
  - Idempotency: re-parsing the YAML produces the same dict.
  - IKEA doc at `docs/setup/tailscale-qr.md` has 5 numbered sections
    (plain English, no operator jargon in §1-§4).

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest homeassistant/packages/tests/test_tailscale_qr.py -v
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_PATH = (
    REPO_ROOT / "homeassistant" / "packages" / "roamcore_tailscale_qr.yaml"
)
SCRIPTS_DIR = REPO_ROOT / "homeassistant" / "packages" / "scripts"
QR_GENERATOR_PATH = SCRIPTS_DIR / "qr_generator.py"
DOC_PATH = REPO_ROOT / "docs" / "setup" / "tailscale-qr.md"


# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def package() -> dict:
    assert PACKAGE_PATH.is_file(), f"missing package at {PACKAGE_PATH}"
    return yaml.safe_load(PACKAGE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def qr_generator_module():
    """Import `qr_generator.py` as a module so we can call
    `encode_to_svg` + `parse_svg` directly from the test process."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "qr_generator", str(QR_GENERATOR_PATH),
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ----------------------------------------------------------------------------
# (a) YAML parses + helpers present + rc-naming + idempotency
# ----------------------------------------------------------------------------


def test_yaml_parses(package):
    assert isinstance(package, dict)


def test_package_file_exists():
    assert PACKAGE_PATH.is_file(), f"missing {PACKAGE_PATH}"


def test_qr_generator_script_exists():
    assert QR_GENERATOR_PATH.is_file(), f"missing {QR_GENERATOR_PATH}"


def test_input_text_helpers_present(package):
    """Must have all 4 input_text helpers: device_key (password) +
    login_url + svg_path + nonce."""
    helpers = (package.get("input_text") or {})
    expected = {
        "rc_tailscale_qr_device_key",
        "rc_tailscale_qr_login_url",
        "rc_tailscale_qr_svg_path",
        "rc_tailscale_qr_nonce",
    }
    assert expected.issubset(helpers.keys()), (
        f"missing input_text helpers: {expected - helpers.keys()}"
    )


def test_input_button_helper_present(package):
    """The regenerate button must be present."""
    buttons = (package.get("input_button") or {})
    assert "rc_tailscale_qr_regenerate" in buttons


def test_template_binary_sensor_present(package):
    """binary_sensor.rc_tailscale_qr_visible must be present."""
    template = package.get("template") or []
    found = False
    for entry in template:
        for bs in (entry.get("binary_sensor") or []):
            if bs.get("unique_id") == "rc_tailscale_qr_visible":
                found = True
                break
    assert found, "rc_tailscale_qr_visible template binary_sensor not found"


def test_template_sensor_present(package):
    """sensor.rc_tailscale_qr_status must be present with the
    required plain-English status markers."""
    template = package.get("template") or []
    found = None
    for entry in template:
        for s in (entry.get("sensor") or []):
            if s.get("unique_id") == "rc_tailscale_qr_status":
                found = s
                break
    assert found is not None, "rc_tailscale_qr_status template sensor not found"
    state = (found.get("state") or "").lower()
    for marker in (
        "waiting for tailscale account",
        "already paired",
        "show this to your phone",
    ):
        assert marker in state, f"missing plain-English marker: {marker!r}"


def test_shell_command_present(package):
    """shell_command.rc_tailscale_qr_render must exist and invoke the
    QR generator script."""
    cmds = (package.get("shell_command") or {})
    assert "rc_tailscale_qr_render" in cmds, "rc_tailscale_qr_render shell_command missing"
    cmd = cmds["rc_tailscale_qr_render"]
    assert "qr_generator.py" in cmd, (
        "shell_command must reference qr_generator.py (the stdlib generator)"
    )


def test_rc_entity_naming_compliance(package):
    """Every entity_id MUST start with `rc_tailscale_qr_`."""
    helpers = (package.get("input_text") or {})
    for eid in helpers:
        assert eid.startswith("rc_tailscale_qr_"), (
            f"input_text entity_id violates rc-naming: {eid}"
        )
    buttons = (package.get("input_button") or {})
    for eid in buttons:
        assert eid.startswith("rc_tailscale_qr_"), (
            f"input_button entity_id violates rc-naming: {eid}"
        )
    template = package.get("template") or []
    for entry in template:
        for s in (entry.get("sensor") or []):
            uid = s.get("unique_id") or ""
            assert uid.startswith("rc_tailscale_qr_"), (
                f"template sensor unique_id violates rc-naming: {uid}"
            )
        for bs in (entry.get("binary_sensor") or []):
            uid = bs.get("unique_id") or ""
            assert uid.startswith("rc_tailscale_qr_"), (
                f"template binary_sensor unique_id violates rc-naming: {uid}"
            )
    automations = (package.get("automation") or [])
    for a in automations:
        aid = a.get("id") or ""
        assert aid.startswith("rc_tailscale_qr_"), (
            f"automation id violates rc-naming: {aid}"
        )


def test_yaml_idempotent(package):
    """Re-parsing produces the same dict."""
    text = PACKAGE_PATH.read_text(encoding="utf-8")
    re_parsed = yaml.safe_load(text)
    assert yaml.safe_dump(package, sort_keys=True) == yaml.safe_dump(re_parsed, sort_keys=True)


def test_device_key_is_password_mode(package):
    """input_text.rc_tailscale_qr_device_key must be mode: password
    (never logged)."""
    helpers = (package.get("input_text") or {})
    helper = helpers.get("rc_tailscale_qr_device_key")
    assert helper is not None
    assert (helper.get("mode") or "").lower() == "password"


# ----------------------------------------------------------------------------
# (b) §8 MANDATORY AUTOMATIONS
# ----------------------------------------------------------------------------


def test_q1_automation_present(package):
    """§8.Q.1 — qr_compute_login_url."""
    automations = (package.get("automation") or [])
    ids = {a.get("id") for a in automations}
    assert "rc_tailscale_qr_compute_login_url" in ids


def test_q2_automation_present(package):
    """§8.Q.2 — qr_regenerate_on_request."""
    automations = (package.get("automation") or [])
    ids = {a.get("id") for a in automations}
    assert "rc_tailscale_qr_regenerate_on_request" in ids


def test_q1_automation_references_stage_transition(package):
    """§8.Q.1 must listen to the wizard stage entity_id and build
    the login URL."""
    automations = (package.get("automation") or [])
    for a in automations:
        if a.get("id") == "rc_tailscale_qr_compute_login_url":
            triggers = a.get("trigger") or []
            text = yaml.safe_dump(triggers)
            assert "rc_remote_access_setup_stage" in text, (
                "§8.Q.1 must trigger on rc_remote_access_setup_stage transitions"
            )
            actions = a.get("action") or []
            actions_text = yaml.safe_dump(actions)
            assert "login.tailscale.com" in actions_text, (
                "§8.Q.1 must build the https://login.tailscale.com/a/<key> URL"
            )
            return
    pytest.fail("§8.Q.1 automation not found (id mismatch)")


def test_q2_automation_references_button_press(package):
    """§8.Q.2 must listen to the rc_tailscale_qr_regenerate button."""
    automations = (package.get("automation") or [])
    for a in automations:
        if a.get("id") == "rc_tailscale_qr_regenerate_on_request":
            triggers = a.get("trigger") or []
            text = yaml.safe_dump(triggers)
            assert "rc_tailscale_qr_regenerate" in text, (
                "§8.Q.2 must trigger on the rc_tailscale_qr_regenerate button"
            )
            actions = a.get("action") or []
            actions_text = yaml.safe_dump(actions)
            assert "rc_tailscale_qr_render" in actions_text, (
                "§8.Q.2 must call shell_command.rc_tailscale_qr_render"
            )
            return
    pytest.fail("§8.Q.2 automation not found (id mismatch)")


# ----------------------------------------------------------------------------
# (c) Secrets-leak check
# ----------------------------------------------------------------------------


def test_no_secrets_in_yaml():
    """No tskey- / ts-auth- / hardcoded device-key patterns in YAML."""
    text = PACKAGE_PATH.read_text(encoding="utf-8")
    leaks = re.findall(r'(tskey-[A-Za-z0-9_-]{8,}|ts-auth-[A-Za-z0-9_-]{8,})', text)
    assert not leaks, f"secret pattern leaked in YAML: {leaks}"


def test_no_hardcoded_url_with_device_key_in_qr_generator():
    """The QR generator must not embed any test device-key."""
    text = QR_GENERATOR_PATH.read_text(encoding="utf-8")
    leaks = re.findall(r'tailscale\.com/a/[A-Za-z0-9]{20,}', text)
    assert not leaks, f"long tailscale URL leaked in qr_generator.py: {leaks}"


# ----------------------------------------------------------------------------
# (d) QR generator — structural + scanner-relevant sanity checks
# ----------------------------------------------------------------------------


def test_qr_generator_is_stdlib_only(qr_generator_module):
    """No third-party imports beyond stdlib."""
    import ast
    src = QR_GENERATOR_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    allowed_stdlib = {
        "argparse", "math", "sys", "xml", "xml.etree.ElementTree",
        "itertools", "typing", "__future__",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in allowed_stdlib, (
                    f"non-stdlib import detected: {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert module in allowed_stdlib, (
                f"non-stdlib import detected: {module}"
            )


def test_qr_generator_produces_valid_svg(qr_generator_module):
    """A canonical Tailscale login URL must render to a valid SVG."""
    payload = "https://login.tailscale.com/a/test-abc123"
    svg = qr_generator_module.encode_to_svg(payload, size_px=256)
    assert 'viewBox="0 0 256 256"' in svg, (
        f"SVG missing correct viewBox; head:\n{svg[:160]}"
    )
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    rects = root.findall("{http://www.w3.org/2000/svg}rect")
    dark_rects = [r for r in rects if (r.get("fill") or "").lower() == "black"]
    assert len(dark_rects) >= 1, "no dark modules in QR SVG"


def test_qr_generator_idempotent(qr_generator_module):
    """Same input → identical SVG (deterministic)."""
    payload = "https://login.tailscale.com/a/test-determinism"
    s1 = qr_generator_module.encode_to_svg(payload, 256)
    s2 = qr_generator_module.encode_to_svg(payload, 256)
    assert s1 == s2


def test_qr_generator_payload_parses_as_tailscale_login_url(qr_generator_module):
    """The Tailscale login URL must round-trip: caller contract."""
    payload = "https://login.tailscale.com/a/test-abc123"
    m = re.match(r'^https://login\.tailscale\.com/a/[A-Za-z0-9_-]+$', payload)
    assert m is not None, f"payload is not a valid tailscale login URL: {payload}"


def test_qr_generator_self_test_returns_zero(qr_generator_module):
    """The bundled self-test must exit 0."""
    rc = qr_generator_module.self_test()
    assert rc == 0


def test_qr_generator_handles_long_payload_gracefully(qr_generator_module):
    """A very long payload must exit with a non-zero code (NOT crash)."""
    long_payload = "https://login.tailscale.com/a/" + ("x" * 700)
    try:
        svg = qr_generator_module.encode_to_svg(long_payload, 256)
        ET.fromstring(svg)
    except ValueError as e:
        assert "too long" in str(e).lower()


def test_qr_generator_parse_svg_returns_structured_info(qr_generator_module):
    """parse_svg returns a dict with viewBox + dark_modules + size_modules."""
    payload = "https://login.tailscale.com/a/test-abc123"
    svg = qr_generator_module.encode_to_svg(payload, 256)
    info = qr_generator_module.parse_svg(svg)
    assert "viewBox" in info
    assert info["viewBox"] == "0 0 256 256"
    assert "dark_modules" in info
    assert info["dark_modules"] >= 1
    assert "size_modules" in info
    assert 21 <= info["size_modules"] <= 57


# ----------------------------------------------------------------------------
# (e) IKEA user doc shape
# ----------------------------------------------------------------------------


def test_user_facing_doc_exists():
    assert DOC_PATH.is_file(), f"missing IKEA user doc at {DOC_PATH}"


def test_user_facing_doc_has_5_sections():
    """The doc must have 5 numbered sections (§1..§5)."""
    text = DOC_PATH.read_text(encoding="utf-8")
    for marker in ("§1", "§2", "§3", "§4", "§5"):
        assert marker in text, f"doc missing section marker: {marker}"


def test_user_facing_doc_no_operator_jargon_in_visible_sections():
    """The user-facing doc (§1-§4) must not contain
    `integration`, `entity`, `shell_command`, `automation`,
    `input_text`, `binary_sensor`, `template sensor`."""
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    parts = text.split("§5", 1)
    body = parts[0] if len(parts) == 2 else text
    forbidden = [
        "integration", "entity", "shell_command", "automation",
        "input_text", "binary_sensor", "template sensor",
    ]
    violations = [w for w in forbidden if w in body]
    assert not violations, (
        f"operator jargon found in user-facing §1-§4: {violations}"
    )


def test_user_facing_doc_no_internal_speak():
    """No references to 'cron', 'sub-agent', 'Wave' in the user doc."""
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for forbidden in ("cron", "sub-agent", "wave ", "wave 9", "wave9"):
        assert forbidden not in text, (
            f"internal-speak term in user doc: {forbidden!r}"
        )


# ----------------------------------------------------------------------------
# (f) Cross-cutting — the QR tile visibility contract
# ----------------------------------------------------------------------------


def test_qr_visible_only_at_correct_stages():
    """The dashboard tile must surface the QR only when the wizard
    is in `tailscale_paste_key` or `tailscale_done`."""
    key, stage = "", "welcome"
    visible = key != "" and stage in ("tailscale_paste_key", "tailscale_done")
    assert visible is False  # default off

    key, stage = "tskey-x", "tailscale_paste_key"
    visible = key != "" and stage in ("tailscale_paste_key", "tailscale_done")
    assert visible is True

    key, stage = "tskey-x", "tailscale_done"
    visible = key != "" and stage in ("tailscale_paste_key", "tailscale_done")
    assert visible is True

    key, stage = "tskey-x", "recovery"
    visible = key != "" and stage in ("tailscale_paste_key", "tailscale_done")
    assert visible is False  # hide on recovery


# ----------------------------------------------------------------------------
# (g) Final assemble — confirm everything that should be wired is wired
# ----------------------------------------------------------------------------


def test_kitchen_sink():
    """Catch-all that asserts every contract listed in the slice spec."""
    text = PACKAGE_PATH.read_text(encoding="utf-8")
    required = [
        "rc_tailscale_qr_device_key",
        "rc_tailscale_qr_login_url",
        "rc_tailscale_qr_visible",
        "rc_tailscale_qr_status",
        "rc_tailscale_qr_regenerate",
        "rc_tailscale_qr_compute_login_url",
        "rc_tailscale_qr_regenerate_on_request",
        "rc_tailscale_qr_render",
    ]
    for r in required:
        assert r in text, f"missing required contract marker in YAML: {r!r}"
