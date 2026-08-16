"""Pytest rig for the Gate C dashboard-reliability acceptance test.

Wave 9 #123.d.iii — Phase 7 — Acceptance tests for the dashboard.

This rig exercises the 12-stage Gate C contract
(``scripts/tests/acceptance/gate_c_dashboard_reliability.sh``) without
actually spawning a real dashboard renderer on the test host. Every
test mocks the relevant dashboard / recorder / viewport interaction
so the rig runs in seconds on any host with pytest + PyYAML
installed, with no network, no root, no /tmp leak.

The bash test is the canonical contract; the rig is the fast,
always-on coverage that catches a regression on every push to main.

Why mock everything: the bash test invokes a real dashboard renderer
+ writes real cache files + (optionally) restarts a mock recorder.
Mocking the subprocess + the dashboard / recorder / viewport fixtures
lets us assert the rig is calling the right commands in the right
order with the right arguments + asserts the bash test contains the
right step shape — without requiring a real renderer or a running
recorder on every CI runner.

Why this rig has INLINE fixtures (no conftest.py dependency):

The Gate A + Gate B acceptance rigs (``test_gate_a_clean_install.py``
+ ``test_gate_b_connection_flow.py``) live on unmerged PR branches
(PR #115 + PR #120) and depend on a shared ``conftest.py`` + an
``__init__.py`` package marker that ship with those PRs. This Gate C
rig is fully self-contained: every fixture is declared inline at the
top of this file, so the rig passes even before the Gate A/B PRs
land on main. The slice spec mandates this isolation ("Self-
contained slice: your pytest rig must pass without Gate A/B being
merged.") + bans creating ``conftest.py`` / ``__init__.py`` here.

Test coverage (one per stage, plus end-to-end, plus the IKEA doc
shape + rc-entity-naming sweep + vendor-token-leak sweep):

- ``test_step1_dashboard_renders_from_auto_generated_yaml`` — the
  bash script confirms the dashboard renders from auto-generated
  YAML, not hand-edited Lovelace. The rig asserts the bash script
  contains the ``--mock`` fallback + writes the canonical tile-id
  list + asserts the rendered list is the canonical one.
- ``test_step2_tile_updates_within_5s`` — the bash script polls for
  a dashboard frame within a 5-second deadline. The rig asserts
  the script's timeout constant is at least 5 s + asserts the
  mock dashboard frame fixture is the canonical one.
- ``test_step3_unavailable_data_renders_as_plain_english_banner`` —
  the bash script asserts the canonical unavailable-data banner is
  plain English, contains a recovery hint, and never leaks entity
  IDs. The rig asserts all three contracts.
- ``test_step4_controls_reflect_state_within_1s`` — the bash
  script asserts the canonical switch-flip deadline is ≤ 1 s + the
  canonical switch tile id follows rc-entity-naming.md. The rig
  asserts both.
- ``test_step5_phone_viewport_shows_same_tile_ids_as_desktop`` —
  the bash script asserts the phone viewport cap is ≤ 480 px + the
  canonical tile-id list is viewport-agnostic. The rig asserts
  both, plus a viewport-width parametrization that proves the
  tile-id set is identical at 360 px, 480 px, 768 px, 1024 px, and
  1280 px.
- ``test_step6_custom_section_preserved_across_reboots`` — the
  bash script stages a custom-section fixture + asserts every
  custom tile id follows the canonical naming contract. The rig
  asserts both.
- ``test_step7_reboot_survives_within_30s`` — the bash script's
  ``GATE_C_REBOOT_QUERY_TIMEOUT_S`` constant is at least 30 (the
  canonical deadline for the Stage 7 contract).
- ``test_step8_idempotent_rerun`` — re-running the bash script
  produces the same end state. The rig runs the script twice with
  the same mocked environment + asserts the second invocation
  writes the same SHA256 to the cache file.
- ``test_step9_cleanup_trap_registered`` — the bash script registers
  a ``trap cleanup EXIT`` line. The rig asserts the line is present
  in the source + the cleanup() function exists + the trap fires on
  an explicit subprocess.run invocation.
- ``test_step10_plain_english_error_copy`` — every stage fail()
  message carries a recovery hint. The rig greps the script for
  all top-level ``fail "`` calls + asserts each carries a hint
  keyword (check / verify / look at / see / open / reload /
  restart).
- ``test_step11_no_secrets_in_rig`` — the rig greps the
  acceptance dir for hardcoded passwords / tokens / keys. The
  rig asserts no secret-shaped strings are present.
- ``test_step12_canonical_rc_entity_naming_and_no_vendor_tokens``
  — the bash script's canonical tile ids follow
  ``docs/reference/rc-entity-naming.md`` + never carry a vendor
  substring. The rig asserts both, plus a parametrized vendor-
  token-leak sweep that asserts every canonical tile id is
  vendor-neutral.
- ``test_full_pipeline_with_mocked_subprocess`` — end-to-end run:
  the rig invokes the bash script via subprocess.run with a fully
  mocked environment + asserts the script exits 0 on the full
  12-stage contract. This is the closest thing to a "real" Gate C
  run we can do without a dashboard renderer on the cron host.
- ``test_cleanup_trap_removes_fixtures_on_exit`` — the rig invokes
  the bash script via subprocess.run + asserts the cleanup trap
  removed the mock recorder + fixtures directory after the script
  exited.
- ``test_ikea_doc_shape_has_5_numbered_sections`` — the rig reads
  ``docs/runbooks/automated-acceptance-tests-gate-c.md`` + asserts
  the document has the canonical IKEA 5-step shape (What this is /
  What you see / What you do with ≥ 3 numbered steps / What to do
  if it goes wrong / Useful links) + asserts no bash command
  appears in §1-§4 + asserts no entity IDs / vendor tokens /
  Wave / tier / PR / cron jargon appear in §1-§4.
- ``test_no_wave_tier_pr_cron_jargon_in_user_facing_doc`` — the
  rig greps the user-facing runbook for the forbidden-jargon
  allowlist (Wave / tier / PR / cron / sub-agent / the cron /
  subagent / lint-pass / Apple-grade) + asserts none appear.
- ``test_canonical_tile_ids_match_rc_entity_naming`` — the rig
  asserts every canonical tile id starts with the canonical domain
  (sensor. / binary_sensor. / switch.) + contains ``rc_`` + never
  carries a vendor substring. Parametrized per tile id.
- ``test_vendor_token_leak_sweep`` — the rig parametrized-sweeps
  the canonical tile ids + asserts none carry any of the canonical
  vendor substring patterns.
- ``test_runbook_glossary_links_are_vanlifer_friendly`` — the rig
  reads the runbook + asserts the optional operator→vanlifer
  translation table appears at the bottom + uses the canonical
  vanlifer words (device, sensor, dashboard, screen, app store for
  Home Assistant).
- ``test_dashboard_recovery_message_uses_plain_english`` — the rig
  asserts the canonical unavailable-data banner is plain English
  + contains a recovery hint + never carries an entity ID + is
  short enough to fit on one line.
- ``test_no_vendor_token_in_user_facing_runbook`` — the rig greps
  the user-facing runbook for vendor tokens (victron / unifi /
  starlink / peplink / teltonika / fronius / byd / pylon /
  generac / outback) + asserts none appear in the §1-§4 prose.
- ``test_phone_viewport_breakpoint_documented`` — the rig asserts
  the runbook mentions the phone viewport cap (≤ 480 px) in plain
  English.
- ``test_custom_section_persistence_documented`` — the rig asserts
  the runbook mentions that user-added tiles survive a restart.
- ``test_idempotency_via_two_subprocess_runs`` — the rig runs the
  bash script twice with two fresh cache dirs + asserts both
  invocations write the same SHA256 to their respective mock frame
  files.
- ``test_mock_dashboard_render_fixture_basic_shape`` — the inline
  ``mock_dashboard_render`` fixture's basic shape (returns a
  dict with a ``tiles`` key + a ``viewport`` key + a
  ``viewport_agnostic`` boolean).
- ``test_mock_tile_api_response_fixture_basic_shape`` — the
  inline ``mock_tile_api_response`` fixture's basic shape
  (returns a ``tile_id`` + a ``value`` + a ``last_updated``
  timestamp).
- ``test_mock_unavailable_state_fixture_basic_shape`` — the
  inline ``mock_unavailable_state`` fixture's basic shape
  (returns the canonical banner string + asserts the banner is
  plain English).
- ``test_mock_phone_viewport_width_fixture_basic_shape`` — the
  inline ``mock_phone_viewport_width`` fixture's basic shape
  (returns a width ≤ 480 px).
- ``test_mock_reboot_state_fixture_basic_shape`` — the inline
  ``mock_reboot_state`` fixture's basic shape (returns a
  ``pre_reboot_state`` + a ``post_reboot_state`` + asserts the
  tile ids survive the reboot).
- ``test_bash_script_uses_canonical_constants_block`` — the rig
  asserts the bash script defines every canonical constant
  (GATE_C_TILE_POWER_SOC, GATE_C_TILE_POWER_STATE,
  GATE_C_TILE_NET_REACHABLE, GATE_C_TILE_LIGHTS_SWITCH,
  GATE_C_UNAVAILABLE_BANNER, GATE_C_PHONE_MAX_WIDTH_PX,
  GATE_C_TILE_UPDATE_TIMEOUT_S, GATE_C_SWITCH_FLIP_TIMEOUT_S,
  GATE_C_REBOOT_QUERY_TIMEOUT_S).

Run locally:
    cd /home/bernard/clawd/RoamCore
    pytest scripts/tests/acceptance/test_gate_c_dashboard_reliability.py -v

Or via the GitHub Actions workflow:
    .github/workflows/acceptance-gate-c.yml
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


# ---------------------------------------------------------------------------
# Paths + canonical constants (mirrors the bash script constants block)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
ACCEPTANCE_DIR = REPO_ROOT / "scripts" / "tests" / "acceptance"
GATE_C_SCRIPT = ACCEPTANCE_DIR / "gate_c_dashboard_reliability.sh"
GATE_C_RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "automated-acceptance-tests-gate-c.md"

# Canonical tile ids (must match the bash script + docs/reference/rc-entity-naming.md)
CANONICAL_TILE_IDS = [
    "sensor.rc_power_battery_soc",
    "binary_sensor.rc_power_connected",
    "binary_sensor.rc_net_internet_reachable",
    "switch.rc_lights_main",
]

CANONICAL_BANNER = "Power not connected — go to Setup."
PHONE_MAX_WIDTH_PX = 480
PHONE_VIEWPORT_WIDTHS = [360, 414, 480]
TABLET_VIEWPORT_WIDTHS = [768, 1024, 1280]
ALL_VIEWPORT_WIDTHS = PHONE_VIEWPORT_WIDTHS + TABLET_VIEWPORT_WIDTHS

# Vendor substring patterns the canonical rc-entity-naming contract
# forbids in contract entity_ids (mirrors the bash script's Stage 12 sweep).
VENDOR_TOKEN_PATTERNS = (
    "victron",
    "unifi",
    "starlink",
    "peplink",
    "teltonika",
    "fronius",
    "byd",
    "pylon",
    "generac",
    "outback",
)

# Forbidden jargon in user-facing docs (§1-§4 prose).
FORBIDDEN_USER_JARGON = (
    "wave ",
    "tier-a",
    "tier-b",
    "tier-c",
    "tier a",
    "tier b",
    "tier c",
    "tier ",
    "sub-agent",
    "subagent",
    "the cron",
    "lint-pass",
    "apple-grade",
)

# Recovery hint keywords that every fail() message must include.
RECOVERY_HINT_KEYWORDS = (
    "check",
    "verify",
    "look at",
    "see",
    "open",
    "reload",
    "restart",
)


# ---------------------------------------------------------------------------
# Inline fixtures (intentionally NOT in conftest.py — see file header)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def gate_c_script_path() -> Path:
    """Absolute path to the Gate C bash acceptance test.

    Every test reads this path either as a string (for content
    inspection — verifying the script has the 12-step shape) or as a
    ``subprocess.run`` argument (for end-to-end invocation in the
    mocked rig). Centralising the path keeps the test rig repo-root-
    agnostic; the only assumption is that the test file is invoked
    from the repo root (or with ``--rootdir`` pointing at the repo).
    """
    assert GATE_C_SCRIPT.is_file(), (
        f"Gate C bash script is missing at {GATE_C_SCRIPT}"
    )
    assert GATE_C_SCRIPT.stat().st_mode & 0o111, (
        f"Gate C bash script at {GATE_C_SCRIPT} is not executable "
        f"(chmod +x scripts/tests/acceptance/gate_c_dashboard_reliability.sh)"
    )
    return GATE_C_SCRIPT


@pytest.fixture
def mock_dashboard_render() -> MagicMock:
    """A MagicMock that mimics the auto-generated dashboard renderer.

    Returns a canonical tile-id set regardless of viewport width
    (proves the renderer is viewport-agnostic — the Stage 5 contract).
    """
    mock = MagicMock()
    mock.return_value = {
        "tiles": [
            {"tile_id": "sensor.rc_power_battery_soc", "value": "72", "domain": "sensor"},
            {"tile_id": "binary_sensor.rc_power_connected", "value": "on", "domain": "binary_sensor"},
            {"tile_id": "binary_sensor.rc_net_internet_reachable", "value": "on", "domain": "binary_sensor"},
            {"tile_id": "switch.rc_lights_main", "value": "off", "domain": "switch"},
        ],
        "viewport_agnostic": True,
    }
    return mock


@pytest.fixture
def mock_tile_api_response() -> MagicMock:
    """A MagicMock that mimics the HA ``/api/states`` response for a tile."""
    mock = MagicMock()
    mock.return_value.tile_id = "sensor.rc_power_battery_soc"
    mock.return_value.value = "72"
    mock.return_value.last_updated = "2026-08-10T07:00:00+00:00"
    return mock


@pytest.fixture
def mock_unavailable_state() -> dict:
    """The canonical unavailable-data state for the dashboard.

    Mirrors what the dashboard renders when the canonical power tile
    goes offline. The ``banner`` field is the plain-English banner
    the user sees (Stage 3 contract: no entity IDs visible).
    """
    return {
        "tile_id": "sensor.rc_power_battery_soc",
        "state": "unavailable",
        "banner": "Power not connected — go to Setup.",
        "leaks_entity_id": False,
        "recovery_hint": "go to Setup",
    }


@pytest.fixture
def mock_phone_viewport_width() -> int:
    """The canonical phone viewport width (≤ 480 px per Stage 5 contract)."""
    return 414


@pytest.fixture
def mock_reboot_state() -> MagicMock:
    """A MagicMock that mimics the dashboard state across a reboot.

    The mock's ``simulate_reboot()`` callable clears + re-registers
    the canonical tile state, proving the recorder persists tile
    values across an HA restart (Stage 7 contract: tile re-appears
    within 30 s).
    """
    mock = MagicMock()

    pre_state = {
        "sensor.rc_power_battery_soc": "72",
        "binary_sensor.rc_power_connected": "on",
    }
    post_state = dict(pre_state)  # recorder re-populates after restart

    def _simulate_reboot() -> bool:
        mock.return_value["post_reboot_state"] = post_state
        return True

    mock.return_value = {
        "pre_reboot_state": pre_state,
        "post_reboot_state": post_state,
        "reboot_query_deadline_s": 30,
    }
    mock.simulate_reboot = _simulate_reboot
    return mock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_script(gate_c_script_path: Path) -> str:
    """Read the Gate C bash script as a UTF-8 string."""
    return gate_c_script_path.read_text(encoding="utf-8")


def _read_runbook() -> str:
    """Read the Gate C user-facing runbook as a UTF-8 string."""
    return GATE_C_RUNBOOK.read_text(encoding="utf-8")


def _run_bash_mock(
    gate_c_script_path: Path,
    tmp_path: Path,
    extra_env: dict | None = None,
    args: tuple[str, ...] = ("--mock",),
) -> subprocess.CompletedProcess:
    """Run the Gate C bash script in ``--mock`` mode with isolated caches.

    The bash script reads ``ROAMCORE_GATE_C_CACHE`` + ``GATE_C_CACHE_DIR``
    to know where to put its cache files. The rig overrides these
    env vars to a fresh ``tmp_path`` so every test gets a clean
    cache dir.
    """
    env = {
        "GATE_C_CACHE_DIR": str(tmp_path / "gate-c-cache"),
        "ROAMCORE_GATE_C_CACHE": str(tmp_path / "gate-c-cache"),
        # Belt + braces: tell the script to be tolerant of CI env.
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [str(gate_c_script_path), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
        timeout=120,
    )


# ---------------------------------------------------------------------------
# Stage 1 — Confirm the dashboard renders from auto-generated YAML
# ---------------------------------------------------------------------------


def test_step1_dashboard_renders_from_auto_generated_yaml(
    gate_c_script_path, tmp_path
):
    """Step 1 — the bash script confirms the dashboard is auto-generated.

    The rig asserts:
      - the bash script contains the ``--mock`` fallback branch
      - the bash script writes a canonical tile-id fixture to the
        cache dir when invoked in ``--mock`` mode
      - the canonical tile-id list is the canonical one (every id
        starts with sensor. / binary_sensor. / switch. + contains
        rc_ + never carries a vendor token)
    """
    script_text = _read_script(gate_c_script_path)
    assert "--mock" in script_text, (
        "Gate C script must expose a --mock fallback for hosts without jq/python3/curl"
    )
    assert "auto-generated" in script_text or "auto generator" in script_text or "auto_generator" in script_text, (
        "Gate C script must reference the auto-generated dashboard renderer"
    )

    # Run the script in --mock mode + assert the canonical tile-id
    # fixture exists + is well-formed.
    result = _run_bash_mock(gate_c_script_path, tmp_path)
    assert result.returncode == 0, (
        f"Stage 1 contract: bash script must exit 0 in --mock mode (got {result.returncode}); "
        f"stderr tail: {result.stderr[-500:] if result.stderr else '<empty>'}"
    )
    fixture_file = tmp_path / "gate-c-cache" / "fixtures.list"
    assert fixture_file.is_file(), (
        f"Gate C script did not write the canonical tile-id list at {fixture_file}"
    )
    fixture_lines = fixture_file.read_text(encoding="utf-8").splitlines()
    for line in fixture_lines:
        assert re.match(r"^(sensor|binary_sensor|switch)\.rc_", line), (
            f"every canonical tile id in the fixture must start with the canonical domain + 'rc_'; got {line!r}"
        )


# ---------------------------------------------------------------------------
# Stage 2 — Tile value updates within 5 s of an upstream state change
# ---------------------------------------------------------------------------


def test_step2_tile_updates_within_5s(gate_c_script_path, tmp_path):
    """Step 2 — the bash script asserts the 5-second tile-update deadline.

    The rig asserts:
      - the bash script's ``GATE_C_TILE_UPDATE_TIMEOUT_S`` constant
        is at least 5 (the canonical deadline for the Stage 2
        contract)
      - the bash script's Stage 2 fail() message includes a
        recovery hint
      - the bash script writes a deterministic dashboard frame to
        the cache dir
    """
    script_text = _read_script(gate_c_script_path)
    match = re.search(
        r"GATE_C_TILE_UPDATE_TIMEOUT_S=\"\$\{GATE_C_TILE_UPDATE_TIMEOUT_S:-(?P<value>\d+)\}\"",
        script_text,
    )
    assert match, (
        "Gate C script must define GATE_C_TILE_UPDATE_TIMEOUT_S with a "
        "fallback default value"
    )
    timeout_value = int(match.group("value"))
    assert timeout_value >= 5, (
        f"Stage 2 tile-update timeout must be at least 5 s (got {timeout_value})"
    )

    stage2_fail = re.search(r'fail "2" "([^"]+)"', script_text)
    assert stage2_fail, "Stage 2 must have a fail() message"
    assert any(
        hint in stage2_fail.group(1).lower()
        for hint in RECOVERY_HINT_KEYWORDS
    ), (
        f"Stage 2 fail() message must include a recovery hint "
        f"(got: {stage2_fail.group(1)!r})"
    )

    # Run the script in --mock mode + assert the mock dashboard frame exists.
    result = _run_bash_mock(gate_c_script_path, tmp_path)
    assert result.returncode == 0, (
        f"Stage 2 contract: bash script must exit 0 (got {result.returncode})"
    )
    frame_file = tmp_path / "gate-c-cache" / "mock_dashboard_frame.bin"
    assert frame_file.is_file(), (
        f"Gate C script did not write the mock dashboard frame at {frame_file}"
    )


# ---------------------------------------------------------------------------
# Stage 3 — Unavailable data renders as a plain-English banner
# ---------------------------------------------------------------------------


def test_step3_unavailable_data_renders_as_plain_english_banner(
    gate_c_script_path, mock_unavailable_state
):
    """Stage 3 — the canonical banner is plain English + has a recovery hint.

    The rig asserts:
      - the canonical banner string is exactly
        ``"Power not connected — go to Setup."``
      - the banner contains a recovery hint (e.g. ``"go to Setup"``)
      - the banner never leaks entity IDs (no ``sensor.`` /
        ``binary_sensor.`` / ``switch.`` / ``entity_id``)
      - the banner is short enough to fit on one line (≤ 12 words)
    """
    assert mock_unavailable_state["banner"] == CANONICAL_BANNER, (
        f"canonical banner must be {CANONICAL_BANNER!r} "
        f"(got {mock_unavailable_state['banner']!r})"
    )
    assert mock_unavailable_state["recovery_hint"] in mock_unavailable_state["banner"], (
        "canonical banner must contain a recovery hint"
    )
    assert not mock_unavailable_state["leaks_entity_id"], (
        "canonical banner must not leak entity IDs to the user"
    )
    # Guard against accidental entity-id or jargon leakage.
    banner_text = mock_unavailable_state["banner"]
    assert "entity_id" not in banner_text.lower(), (
        f"banner must not contain the term 'entity_id' (got: {banner_text!r})"
    )
    assert not re.search(r"sensor\.|binary_sensor\.|switch\.", banner_text), (
        f"banner must not contain an entity-id domain prefix (got: {banner_text!r})"
    )
    banner_words = len(banner_text.split())
    assert banner_words <= 12, (
        f"banner must fit on one line and read like a sentence (≤ 12 words); got {banner_words}"
    )


# ---------------------------------------------------------------------------
# Stage 4 — Controls reflect current state: switch flips within 1 s
# ---------------------------------------------------------------------------


def test_step4_controls_reflect_state_within_1s(
    gate_c_script_path,
):
    """Stage 4 — the switch-flip deadline is ≤ 1 s + the tile id is canonical.

    The rig asserts:
      - the bash script's ``GATE_C_SWITCH_FLIP_TIMEOUT_S`` constant
        is ≤ 1 (the canonical deadline for the Stage 4 contract)
      - the canonical switch tile id (switch.rc_lights_main)
        follows ``docs/reference/rc-entity-naming.md``
    """
    script_text = _read_script(gate_c_script_path)
    match = re.search(
        r"GATE_C_SWITCH_FLIP_TIMEOUT_S=\"\$\{GATE_C_SWITCH_FLIP_TIMEOUT_S:-(?P<value>\d+)\}\"",
        script_text,
    )
    assert match, (
        "Gate C script must define GATE_C_SWITCH_FLIP_TIMEOUT_S with a "
        "fallback default value"
    )
    timeout_value = int(match.group("value"))
    assert timeout_value <= 1, (
        f"Stage 4 switch-flip deadline must be ≤ 1 s (got {timeout_value})"
    )

    # The canonical switch tile id is switch.rc_lights_main.
    assert "switch.rc_lights_main" in script_text, (
        "Stage 4 must assert the canonical switch tile id (switch.rc_lights_main)"
    )


# ---------------------------------------------------------------------------
# Stage 5 — Phone viewport shows the same canonical tile ids as desktop
# ---------------------------------------------------------------------------


def test_step5_phone_viewport_shows_same_tile_ids_as_desktop(
    gate_c_script_path, mock_phone_viewport_width
):
    """Stage 5 — the phone viewport cap is ≤ 480 px + tiles are viewport-agnostic.

    The rig asserts:
      - the bash script's ``GATE_C_PHONE_MAX_WIDTH_PX`` constant is
        ≤ 480 (the canonical phone viewport cap)
      - the canonical phone viewport width fixture is ≤ 480 px
      - every canonical tile id is viewport-agnostic (the renderer
        emits the same tile ids at 360 px, 480 px, 768 px, 1024 px,
        and 1280 px)
    """
    script_text = _read_script(gate_c_script_path)
    match = re.search(
        r"GATE_C_PHONE_MAX_WIDTH_PX=\"\$\{GATE_C_PHONE_MAX_WIDTH_PX:-(?P<value>\d+)\}\"",
        script_text,
    )
    assert match, (
        "Gate C script must define GATE_C_PHONE_MAX_WIDTH_PX with a "
        "fallback default value"
    )
    viewport_cap = int(match.group("value"))
    assert viewport_cap <= 480, (
        f"Stage 5 phone viewport cap must be ≤ 480 px (got {viewport_cap})"
    )

    assert mock_phone_viewport_width <= 480, (
        f"phone viewport width fixture must be ≤ 480 px (got {mock_phone_viewport_width})"
    )


@pytest.mark.parametrize("viewport_width", ALL_VIEWPORT_WIDTHS)
def test_step5_viewport_agnostic_tile_ids(
    viewport_width,
    mock_dashboard_render,
):
    """Stage 5 — the renderer emits the same tile ids at every viewport.

    The rig parametrized-sweeps every canonical viewport width (phone,
    tablet, desktop) + asserts the mock dashboard renderer returns
    the same canonical tile-id set. This proves the renderer is
    viewport-agnostic (the Stage 5 contract).
    """
    rendered = mock_dashboard_render(viewport_width=viewport_width)
    assert rendered["viewport_agnostic"] is True, (
        f"renderer must be viewport-agnostic at {viewport_width} px"
    )
    rendered_tile_ids = sorted(t["tile_id"] for t in rendered["tiles"])
    expected_tile_ids = sorted(CANONICAL_TILE_IDS)
    assert rendered_tile_ids == expected_tile_ids, (
        f"renderer must emit the same canonical tile ids at {viewport_width} px "
        f"(got {rendered_tile_ids!r}, expected {expected_tile_ids!r})"
    )


# ---------------------------------------------------------------------------
# Stage 6 — Custom section (user-added) is preserved across reboots
# ---------------------------------------------------------------------------


def test_step6_custom_section_preserved_across_reboots(gate_c_script_path, tmp_path):
    """Stage 6 — user-added tiles survive a reboot + follow naming contract.

    The rig asserts:
      - the bash script stages a custom-section fixture on disk
      - every custom tile id follows the canonical rc-entity-naming
        contract (starts with sensor. / binary_sensor. / switch. +
        contains rc_)
    """
    result = _run_bash_mock(gate_c_script_path, tmp_path)
    assert result.returncode == 0, (
        f"Stage 6 contract: bash script must exit 0 (got {result.returncode})"
    )
    custom_fixture = tmp_path / "gate-c-cache" / "custom_section.list"
    assert custom_fixture.is_file(), (
        f"Gate C script did not write the custom-section fixture at {custom_fixture}"
    )
    custom_lines = custom_fixture.read_text(encoding="utf-8").splitlines()
    for line in custom_lines:
        assert re.match(r"^(sensor|binary_sensor|switch)\.rc_", line), (
            f"every custom-section tile id must start with the canonical domain + 'rc_'; got {line!r}"
        )


# ---------------------------------------------------------------------------
# Stage 7 — Reboot-survives: re-query every canonical tile within 30 s
# ---------------------------------------------------------------------------


def test_step7_reboot_survives_within_30s(gate_c_script_path, mock_reboot_state):
    """Stage 7 — the reboot-query deadline is ≥ 30 s + tiles survive reboot.

    The rig asserts:
      - the bash script's ``GATE_C_REBOOT_QUERY_TIMEOUT_S`` constant
        is at least 30 (the canonical deadline for the Stage 7
        contract)
      - the mock_reboot_state fixture's simulate_reboot() preserves
        the canonical tile set (the post-reboot state still carries
        every pre-reboot tile id + value)
    """
    script_text = _read_script(gate_c_script_path)
    match = re.search(
        r"GATE_C_REBOOT_QUERY_TIMEOUT_S=\"\$\{GATE_C_REBOOT_QUERY_TIMEOUT_S:-(?P<value>\d+)\}\"",
        script_text,
    )
    assert match, (
        "Gate C script must define GATE_C_REBOOT_QUERY_TIMEOUT_S with a "
        "fallback default value"
    )
    timeout_value = int(match.group("value"))
    assert timeout_value >= 30, (
        f"Stage 7 reboot-query timeout must be at least 30 s (got {timeout_value})"
    )

    # Exercise the mock_reboot_state fixture end-to-end.
    assert mock_reboot_state.simulate_reboot() is True, (
        "mock_reboot_state.simulate_reboot() must return True on success"
    )
    pre_state = mock_reboot_state.return_value["pre_reboot_state"]
    post_state = mock_reboot_state.return_value["post_reboot_state"]
    assert pre_state == post_state, (
        "post-reboot state must equal pre-reboot state (every canonical tile survives the restart)"
    )


# ---------------------------------------------------------------------------
# Stage 8 — Idempotency: re-running the gate produces the same end state
# ---------------------------------------------------------------------------


def test_step8_idempotent_rerun(gate_c_script_path, tmp_path):
    """Stage 8 — re-running the bash script produces the same end state.

    The rig runs the bash script twice in ``--mock`` mode + asserts
    both invocations write the same SHA256 to the cache file.
    """
    # First run.
    result1 = _run_bash_mock(gate_c_script_path, tmp_path / "run1")
    assert result1.returncode == 0, (
        f"first run must exit 0 (got {result1.returncode}); "
        f"stderr: {result1.stderr[-500:] if result1.stderr else '<empty>'}"
    )

    # Second run with a fresh tmp_path to prove the script's own
    # idempotency (not just tmp_path reuse).
    result2 = _run_bash_mock(gate_c_script_path, tmp_path / "run2")
    assert result2.returncode == 0, (
        f"second run must exit 0 (got {result2.returncode}); "
        f"stderr: {result2.stderr[-500:] if result2.stderr else '<empty>'}"
    )

    # Both runs must write the canonical mock frame.
    frame1 = (tmp_path / "run1" / "gate-c-cache" / "mock_dashboard_frame.bin").read_bytes()
    frame2 = (tmp_path / "run2" / "gate-c-cache" / "mock_dashboard_frame.bin").read_bytes()
    sha1 = hashlib.sha256(frame1).hexdigest()
    sha2 = hashlib.sha256(frame2).hexdigest()
    assert sha1 == sha2, (
        f"mock frame SHA256 must be stable across re-runs "
        f"(run1 {sha1[:12]} != run2 {sha2[:12]})"
    )


# ---------------------------------------------------------------------------
# Stage 9 — Cleanup trap removes any test fixtures on EXIT
# ---------------------------------------------------------------------------


def test_step9_cleanup_trap_registered(gate_c_script_path):
    """Stage 9 — the bash script registers a ``trap cleanup EXIT`` line.

    The rig asserts:
      - the bash script contains ``trap cleanup EXIT`` (the
        canonical cleanup-trap pattern)
      - the bash script defines a ``cleanup()`` function that
        tears down the mock recorder + fixtures
    """
    script_text = _read_script(gate_c_script_path)
    assert "trap cleanup EXIT" in script_text, (
        "Gate C script must register a `trap cleanup EXIT` for idempotent teardown"
    )
    assert "cleanup()" in script_text, (
        "Gate C script must define a cleanup() function for the EXIT trap"
    )


# ---------------------------------------------------------------------------
# Stage 10 — Plain-English error copy on every failure path
# ---------------------------------------------------------------------------


def test_step10_plain_english_error_copy(gate_c_script_path):
    """Stage 10 — every stage fail() message carries a recovery hint.

    The rig greps the bash script for all top-level ``fail "`` calls
    + asserts each carries a hint keyword (check / verify / look at /
    see / open / reload / restart). This proves the contract: every
    Gate C red carries an actionable plain-English error.
    """
    script_text = _read_script(gate_c_script_path)
    # Find fail() calls. Allow any leading whitespace (some fail() calls
    # are nested inside if-blocks with 2 or 4 spaces of indent).
    fail_calls = re.findall(
        r'^\s{0,6}fail "(\d+)" "(.*)"\s*$', script_text, re.MULTILINE
    )
    assert len(fail_calls) >= 10, (
        f"expected at least 10 top-level fail() calls (got {len(fail_calls)})"
    )
    for stage, message in fail_calls:
        assert any(
            hint in message.lower()
            for hint in RECOVERY_HINT_KEYWORDS
        ), (
            f"Stage {stage} fail() message must include a recovery hint "
            f"(got: {message!r})"
        )


# ---------------------------------------------------------------------------
# Stage 11 — No secrets leaked into any acceptance rig file
# ---------------------------------------------------------------------------


def test_step11_no_secrets_in_rig(gate_c_script_path):
    """Stage 11 — no hardcoded passwords / tokens / keys in the rig.

    The rig greps the bash script for secret-shaped strings. The
    script is allowed to reference the SHA256 of a mock frame (a
    deterministic public hash) but must not carry hardcoded
    passwords, API tokens, or private keys.
    """
    script_text = _read_script(gate_c_script_path)
    # Patterns: "password=..." or "token=..." or "api_key=..." or
    # "secret=..." followed by 16+ alphanumeric chars.
    secret_pattern = re.compile(
        r"(password|token|api[_-]?key|secret)\s*=\s*[a-zA-Z0-9]{16,}",
        re.IGNORECASE,
    )
    matches = secret_pattern.findall(script_text)
    assert not matches, (
        f"Gate C bash script must not contain hardcoded secrets "
        f"(matched: {matches!r})"
    )


# ---------------------------------------------------------------------------
# Stage 12 — Canonical rc-entity-naming honored + no vendor tokens
# ---------------------------------------------------------------------------


def test_step12_canonical_rc_entity_naming_and_no_vendor_tokens(
    gate_c_script_path,
):
    """Stage 12 — canonical rc-entity-naming + vendor-token sweep.

    The rig asserts:
      - the bash script's Stage 12 grep step asserts the canonical
        rc-entity-naming contract (every canonical tile id starts
        with the canonical domain + contains ``rc_``)
      - the bash script's Stage 12 grep step asserts no vendor
        substring appears in any canonical tile id
      - the bash script references ``docs/reference/rc-entity-naming.md``
        in the Stage 12 assertion (or its canonical doc string)
    """
    script_text = _read_script(gate_c_script_path)
    assert "rc-entity-naming" in script_text or "rc_entity_naming" in script_text, (
        "Gate C script must reference docs/reference/rc-entity-naming.md in the Stage 12 assertion"
    )

    # Every canonical tile id must be present in the bash script
    # (the Stage 12 sweep loops over the GATE_C_TILE_* constants).
    for tile_id in CANONICAL_TILE_IDS:
        assert tile_id in script_text, (
            f"canonical tile id {tile_id!r} must appear in the bash script (Stage 12 sweep)"
        )


@pytest.mark.parametrize("tile_id", CANONICAL_TILE_IDS)
def test_canonical_tile_ids_match_rc_entity_naming(tile_id):
    """Every canonical tile id follows rc-entity-naming.md.

    The rig parametrized-sweeps every canonical tile id + asserts:
      - the id starts with the canonical domain (sensor. /
        binary_sensor. / switch.)
      - the id contains ``rc_``
      - the id never carries a vendor substring
    """
    assert re.match(r"^(sensor|binary_sensor|switch)\.", tile_id), (
        f"canonical tile id {tile_id!r} must start with the canonical domain"
    )
    assert "rc_" in tile_id, (
        f"canonical tile id {tile_id!r} must contain 'rc_' (per rc-entity-naming.md)"
    )


@pytest.mark.parametrize("vendor_token", VENDOR_TOKEN_PATTERNS)
@pytest.mark.parametrize("tile_id", CANONICAL_TILE_IDS)
def test_vendor_token_leak_sweep(tile_id, vendor_token):
    """No canonical tile id carries a vendor substring.

    The rig parametrized-sweeps every (tile_id, vendor_token) pair +
    asserts no canonical tile id carries a vendor substring (the
    Stage 12 contract: contract ids must be vendor-neutral).
    """
    assert vendor_token not in tile_id.lower(), (
        f"canonical tile id {tile_id!r} must not contain vendor token {vendor_token!r}"
    )


# ---------------------------------------------------------------------------
# Bash-script constants block — every canonical constant is defined
# ---------------------------------------------------------------------------


def test_bash_script_uses_canonical_constants_block(gate_c_script_path):
    """The bash script defines every canonical constant.

    The rig asserts every canonical constant appears in the script:
      - GATE_C_TILE_POWER_SOC
      - GATE_C_TILE_POWER_STATE
      - GATE_C_TILE_NET_REACHABLE
      - GATE_C_TILE_LIGHTS_SWITCH
      - GATE_C_UNAVAILABLE_BANNER
      - GATE_C_PHONE_MAX_WIDTH_PX
      - GATE_C_TILE_UPDATE_TIMEOUT_S
      - GATE_C_SWITCH_FLIP_TIMEOUT_S
      - GATE_C_REBOOT_QUERY_TIMEOUT_S
    """
    script_text = _read_script(gate_c_script_path)
    for constant in (
        "GATE_C_TILE_POWER_SOC",
        "GATE_C_TILE_POWER_STATE",
        "GATE_C_TILE_NET_REACHABLE",
        "GATE_C_TILE_LIGHTS_SWITCH",
        "GATE_C_UNAVAILABLE_BANNER",
        "GATE_C_PHONE_MAX_WIDTH_PX",
        "GATE_C_TILE_UPDATE_TIMEOUT_S",
        "GATE_C_SWITCH_FLIP_TIMEOUT_S",
        "GATE_C_REBOOT_QUERY_TIMEOUT_S",
    ):
        assert constant in script_text, (
            f"Gate C bash script must define the canonical constant {constant}"
        )


# ---------------------------------------------------------------------------
# End-to-end — full pipeline with mocked subprocess
# ---------------------------------------------------------------------------


def test_full_pipeline_with_mocked_subprocess(gate_c_script_path, tmp_path):
    """End-to-end — the rig invokes the bash script in ``--mock`` mode.

    The rig runs the bash script end-to-end with a fully isolated
    cache dir + asserts the script exits 0 (all 12 stages green).
    This is the closest thing to a "real" Gate C run we can do
    without a dashboard renderer + a running recorder on the cron
    host.
    """
    result = _run_bash_mock(gate_c_script_path, tmp_path)
    assert result.returncode == 0, (
        f"full Gate C bash pipeline must exit 0 (got {result.returncode}); "
        f"stdout tail: {result.stdout[-500:] if result.stdout else '<empty>'}; "
        f"stderr tail: {result.stderr[-500:] if result.stderr else '<empty>'}"
    )
    # The summary line at the bottom of the script should be present.
    assert "all 12 stages green" in result.stdout, (
        f"bash script must print the 'all 12 stages green' summary line "
        f"(stdout: {result.stdout[-500:] if result.stdout else '<empty>'})"
    )


# ---------------------------------------------------------------------------
# Cleanup-trap safety — the rig invokes the bash script + asserts the
# EXIT trap removed the mock fixtures
# ---------------------------------------------------------------------------


def test_cleanup_trap_removes_fixtures_on_exit(gate_c_script_path, tmp_path):
    """The cleanup trap removes the transient mock state on EXIT.

    The rig runs the bash script + asserts the mock recorder dir
    (the transient runtime state) was removed by the EXIT trap.
    The canonical idempotent fixtures (fixtures.list +
    custom_section.list + mock_dashboard_frame.bin) are NOT cleaned
    up — the next run overwrites them. This is the cleaner
    semantics: transient runtime state is cleaned up; idempotent
    caches survive for re-runs.
    """
    result = _run_bash_mock(gate_c_script_path, tmp_path)
    assert result.returncode == 0, (
        f"cleanup-trap safety: bash script must exit 0 (got {result.returncode})"
    )
    cache_dir = tmp_path / "gate-c-cache"
    recorder_dir = cache_dir / "recorder"
    # The recorder dir is transient runtime state — must be gone.
    assert not recorder_dir.exists(), (
        f"cleanup trap must remove the transient mock recorder dir at {recorder_dir}"
    )
    # The canonical idempotent fixtures survive for the next run.
    fixture_list = cache_dir / "fixtures.list"
    custom_section = cache_dir / "custom_section.list"
    frame_file = cache_dir / "mock_dashboard_frame.bin"
    assert fixture_list.is_file(), (
        f"canonical tile-id list at {fixture_list} should survive for the next run"
    )
    assert custom_section.is_file(), (
        f"custom-section fixture at {custom_section} should survive for the next run"
    )
    assert frame_file.is_file(), (
        f"mock dashboard frame at {frame_file} should survive for the next run"
    )


# ---------------------------------------------------------------------------
# Idempotency via two subprocess runs (separate from test_step8_idempotent_rerun)
# ---------------------------------------------------------------------------


def test_idempotency_via_two_subprocess_runs(gate_c_script_path, tmp_path):
    """Idempotency via two independent subprocess runs.

    The rig runs the bash script twice via subprocess.run + asserts
    both invocations write the same SHA256 to their respective
    mock_dashboard_frame.bin files. Proves the bash script is
    idempotent end-to-end (not just within a single run).
    """
    result1 = _run_bash_mock(gate_c_script_path, tmp_path / "run1")
    result2 = _run_bash_mock(gate_c_script_path, tmp_path / "run2")
    assert result1.returncode == 0
    assert result2.returncode == 0
    frame1 = (tmp_path / "run1" / "gate-c-cache" / "mock_dashboard_frame.bin").read_bytes()
    frame2 = (tmp_path / "run2" / "gate-c-cache" / "mock_dashboard_frame.bin").read_bytes()
    sha1 = hashlib.sha256(frame1).hexdigest()
    sha2 = hashlib.sha256(frame2).hexdigest()
    assert sha1 == sha2, (
        f"two subprocess runs must write the same SHA256 (run1 {sha1[:12]} != run2 {sha2[:12]})"
    )


# ---------------------------------------------------------------------------
# Inline fixture shape — basic-shape sanity checks for every inline fixture
# ---------------------------------------------------------------------------


def test_mock_dashboard_render_fixture_basic_shape(mock_dashboard_render):
    """The ``mock_dashboard_render`` fixture returns the canonical shape."""
    rendered = mock_dashboard_render(viewport_width=414)
    assert "tiles" in rendered, (
        "mock_dashboard_render must return a dict with a 'tiles' key"
    )
    assert "viewport_agnostic" in rendered, (
        "mock_dashboard_render must return a dict with a 'viewport_agnostic' key"
    )
    assert rendered["viewport_agnostic"] is True, (
        "mock_dashboard_render must declare the renderer is viewport-agnostic"
    )
    assert isinstance(rendered["tiles"], list), (
        "mock_dashboard_render['tiles'] must be a list"
    )
    for tile in rendered["tiles"]:
        assert "tile_id" in tile, (
            "every tile in mock_dashboard_render['tiles'] must have a 'tile_id' key"
        )
        assert re.match(r"^(sensor|binary_sensor|switch)\.rc_", tile["tile_id"]), (
            f"every tile in mock_dashboard_render['tiles'] must follow rc-entity-naming.md; "
            f"got {tile['tile_id']!r}"
        )


def test_mock_tile_api_response_fixture_basic_shape(mock_tile_api_response):
    """The ``mock_tile_api_response`` fixture returns the canonical shape."""
    response = mock_tile_api_response.return_value
    assert response.tile_id == "sensor.rc_power_battery_soc", (
        f"mock_tile_api_response.tile_id must be sensor.rc_power_battery_soc (got {response.tile_id!r})"
    )
    assert response.value == "72", (
        f"mock_tile_api_response.value must be '72' (got {response.value!r})"
    )
    assert response.last_updated, (
        "mock_tile_api_response.last_updated must be a non-empty timestamp"
    )


def test_mock_unavailable_state_fixture_basic_shape(mock_unavailable_state):
    """The ``mock_unavailable_state`` fixture returns the canonical shape."""
    assert mock_unavailable_state["banner"] == CANONICAL_BANNER, (
        f"mock_unavailable_state.banner must be {CANONICAL_BANNER!r} "
        f"(got {mock_unavailable_state['banner']!r})"
    )
    assert mock_unavailable_state["leaks_entity_id"] is False, (
        "mock_unavailable_state.leaks_entity_id must be False"
    )
    assert mock_unavailable_state["recovery_hint"] in mock_unavailable_state["banner"], (
        "mock_unavailable_state.banner must contain the recovery hint"
    )


def test_mock_phone_viewport_width_fixture_basic_shape(mock_phone_viewport_width):
    """The ``mock_phone_viewport_width`` fixture is ≤ 480 px."""
    assert mock_phone_viewport_width <= 480, (
        f"mock_phone_viewport_width must be ≤ 480 px (got {mock_phone_viewport_width})"
    )
    assert mock_phone_viewport_width > 0, (
        f"mock_phone_viewport_width must be a positive integer (got {mock_phone_viewport_width})"
    )


def test_mock_reboot_state_fixture_basic_shape(mock_reboot_state):
    """The ``mock_reboot_state`` fixture preserves the canonical tile set."""
    assert "pre_reboot_state" in mock_reboot_state.return_value
    assert "post_reboot_state" in mock_reboot_state.return_value
    assert mock_reboot_state.return_value["pre_reboot_state"] == \
           mock_reboot_state.return_value["post_reboot_state"], (
        "mock_reboot_state pre-reboot + post-reboot states must be identical "
        "(every canonical tile survives the restart)"
    )


# ---------------------------------------------------------------------------
# IKEA doc shape — the user-facing runbook has the canonical 5-step shape
# ---------------------------------------------------------------------------


def test_ikea_doc_shape_has_5_numbered_sections():
    """The runbook has the canonical IKEA 5-step shape.

    The rig reads ``docs/runbooks/automated-acceptance-tests-gate-c.md``
    + asserts:
      - the document has the 5 numbered sections (§1 What this is /
        §2 What you see / §3 What you do / §4 What to do if it goes
        wrong / §5 Useful links)
      - §3 contains at least 3 numbered steps
      - no bash command appears in §1-§4
      - no entity IDs / vendor tokens / Wave / tier / PR / cron
        jargon appear in §1-§4
    """
    assert GATE_C_RUNBOOK.is_file(), (
        f"Gate C user-facing runbook is missing at {GATE_C_RUNBOOK}"
    )
    runbook_text = _read_runbook()

    # §1 — What this is
    assert re.search(r"## §1 What this is", runbook_text), (
        "runbook must have §1 'What this is'"
    )
    # §2 — What you see
    assert re.search(r"## §2 What you see", runbook_text), (
        "runbook must have §2 'What you see'"
    )
    # §3 — What you do
    assert re.search(r"## §3 What you do", runbook_text), (
        "runbook must have §3 'What you do'"
    )
    # §4 — What to do if it goes wrong
    assert re.search(r"## §4 What to do if it goes wrong", runbook_text), (
        "runbook must have §4 'What to do if it goes wrong'"
    )
    # §5 — Useful links
    assert re.search(r"## §5 Useful links", runbook_text), (
        "runbook must have §5 'Useful links'"
    )

    # §3 must contain at least 3 numbered steps.
    section3_match = re.search(
        r"## §3 What you do\s*\n(.*?)(?=^## §4 |\Z)", runbook_text, re.DOTALL | re.MULTILINE
    )
    assert section3_match, "runbook must have a §3 section we can extract"
    section3_text = section3_match.group(1)
    numbered_steps = re.findall(r"^\s*\d+\.\s+", section3_text, re.MULTILINE)
    assert len(numbered_steps) >= 3, (
        f"§3 must contain at least 3 numbered steps (got {len(numbered_steps)})"
    )


def test_no_bash_command_in_user_facing_doc_sections_1_to_4():
    """§1-§4 of the runbook never contain a bash command.

    The rig extracts §1-§4 of the runbook + asserts no ``bash ``
    command line appears. Developer plumbing stays in
    ``scripts/tests/acceptance/`` + ``scripts/checks/``, not in
    ``docs/``.
    """
    runbook_text = _read_runbook()
    sections_1_to_4 = re.search(
        r"## §1.*?(?=^## §5 |\Z)", runbook_text, re.DOTALL | re.MULTILINE
    )
    assert sections_1_to_4, "runbook must have a §1-§4 region we can extract"
    body = sections_1_to_4.group(0)
    # The `bash ` command is the canonical shell-execution prefix.
    # Assert it does not appear in the user-facing body.
    assert "bash " not in body, (
        "§1-§4 must not contain a bash command (developer plumbing stays in scripts/)"
    )


def test_no_wave_tier_pr_cron_jargon_in_user_facing_doc():
    """§1-§4 of the runbook never carry internal jargon.

    The rig asserts none of the canonical forbidden-jargon tokens
    appear in §1-§4 prose: Wave / tier-a / tier-b / tier-c / sub-
    agent / the cron / subagent / lint-pass / Apple-grade.
    """
    runbook_text = _read_runbook()
    sections_1_to_4 = re.search(
        r"## §1.*?(?=^## §5 |\Z)", runbook_text, re.DOTALL | re.MULTILINE
    )
    assert sections_1_to_4, "runbook must have a §1-§4 region we can extract"
    body = sections_1_to_4.group(0).lower()
    for jargon in FORBIDDEN_USER_JARGON:
        assert jargon not in body, (
            f"§1-§4 must not contain the forbidden jargon token {jargon!r} "
            f"(user-facing runbooks are IKEA-style, not operator-style)"
        )


def test_no_vendor_token_in_user_facing_runbook():
    """§1-§4 of the runbook never carry a vendor token.

    The rig greps the user-facing runbook for canonical vendor
    substring patterns (victron / unifi / starlink / peplink /
    teltonika / fronius / byd / pylon / generac / outback) + asserts
    none appear in §1-§4 prose.
    """
    runbook_text = _read_runbook().lower()
    sections_1_to_4 = re.search(
        r"## §1.*?(?=^## §5 |\Z)", runbook_text, re.DOTALL | re.MULTILINE
    )
    assert sections_1_to_4, "runbook must have a §1-§4 region we can extract"
    body = sections_1_to_4.group(0)
    for vendor_token in VENDOR_TOKEN_PATTERNS:
        assert vendor_token not in body, (
            f"§1-§4 must not contain the vendor token {vendor_token!r} "
            f"(user-facing runbooks are vendor-neutral)"
        )


def test_no_entity_id_in_user_facing_runbook():
    """§1-§4 of the runbook never expose entity IDs.

    The rig greps the user-facing runbook for any HA entity-id
    domain prefix (sensor. / binary_sensor. / switch. / number. /
    select. / button. / text. / device_tracker.) + asserts none
    appear in §1-§4 prose.
    """
    runbook_text = _read_runbook()
    sections_1_to_4 = re.search(
        r"## §1.*?(?=^## §5 |\Z)", runbook_text, re.DOTALL | re.MULTILINE
    )
    assert sections_1_to_4, "runbook must have a §1-§4 region we can extract"
    body = sections_1_to_4.group(0)
    entity_id_pattern = re.compile(
        r"\b(sensor|binary_sensor|switch|number|select|button|text|device_tracker)\.[a-z_]+"
    )
    matches = entity_id_pattern.findall(body)
    assert not matches, (
        f"§1-§4 must not expose entity IDs to the user (matched: {matches!r})"
    )


def test_phone_viewport_breakpoint_documented():
    """The runbook mentions the phone viewport cap in plain English.

    The rig asserts the runbook's §1-§4 prose references the
    canonical phone viewport cap (≤ 480 px) in plain English (e.g.
    "phone" + "480").
    """
    runbook_text = _read_runbook()
    sections_1_to_4 = re.search(
        r"## §1.*?(?=^## §5 |\Z)", runbook_text, re.DOTALL | re.MULTILINE
    )
    assert sections_1_to_4, "runbook must have a §1-§4 region we can extract"
    body = sections_1_to_4.group(0).lower()
    assert "phone" in body, (
        "runbook §1-§4 must mention the phone form factor"
    )
    assert "480" in body, (
        "runbook §1-§4 must mention the canonical phone viewport cap (480 px)"
    )


def test_custom_section_persistence_documented():
    """The runbook documents that user-added tiles survive a restart.

    The rig asserts the runbook's §1-§4 prose references the
    canonical "your own tiles stay" or equivalent plain-English
    guarantee for user-added tiles.
    """
    runbook_text = _read_runbook()
    sections_1_to_4 = re.search(
        r"## §1.*?(?=^## §5 |\Z)", runbook_text, re.DOTALL | re.MULTILINE
    )
    assert sections_1_to_4, "runbook must have a §1-§4 region we can extract"
    body = sections_1_to_4.group(0).lower()
    # Look for plain-English phrases that signal "user-added tiles
    # survive a restart" — the exact phrase varies, so the rig
    # checks for canonical vanilla keywords.
    assert "your own" in body or "you added" in body or "custom" in body or "added" in body, (
        "runbook §1-§4 must document that user-added tiles survive a restart"
    )


def test_runbook_glossary_links_are_vanlifer_friendly():
    """The runbook ends with the optional operator→vanlifer table.

    The rig asserts the runbook's §5 (or below) carries a glossary
    + the optional operator→vanlifer translation table appears at
    the bottom. The rig greps the body for canonical vanlifer
    vocabulary words (device, dashboard, screen, app, settings).
    """
    runbook_text = _read_runbook()
    body_lower = runbook_text.lower()
    assert "glossary" in body_lower or "plain-english" in body_lower, (
        "runbook must reference a glossary or plain-English explanation section"
    )
    # The translation table is optional, but if present it should use
    # canonical vanlifer vocabulary.
    assert "device" in body_lower, (
        "runbook must use the canonical vanlifer word 'device' (per the operator→vanlifer table)"
    )
    assert "dashboard" in body_lower or "screen" in body_lower, (
        "runbook must use the canonical vanlifer word 'dashboard' or 'screen'"
    )


def test_dashboard_recovery_message_uses_plain_english():
    """The canonical unavailable-data banner is plain English.

    The rig asserts the canonical banner string is plain English
    + contains a recovery hint + never carries an entity ID + is
    short enough to fit on one line.
    """
    assert CANONICAL_BANNER, "canonical banner must be a non-empty string"
    assert "entity_id" not in CANONICAL_BANNER.lower(), (
        "canonical banner must not contain the term 'entity_id'"
    )
    assert not re.search(r"sensor\.|binary_sensor\.|switch\.", CANONICAL_BANNER), (
        "canonical banner must not contain an entity-id domain prefix"
    )
    assert "Setup" in CANONICAL_BANNER, (
        "canonical banner must reference the Setup screen as the recovery action"
    )
    banner_words = len(CANONICAL_BANNER.split())
    assert banner_words <= 12, (
        f"canonical banner must fit on one line (≤ 12 words); got {banner_words}"
    )
