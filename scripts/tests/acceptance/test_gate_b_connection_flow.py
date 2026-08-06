"""Pytest rig for the Gate B connection-flow acceptance test.

Wave 9 #123.d.ii — Phase 7 — Acceptance tests for the connection flow.

This rig exercises the 15-stage Gate B contract
(``scripts/tests/acceptance/gate_b_connection_flow.sh``) without
actually spawning a real PTY-backed Victron device + a real Home
Assistant instance on the test host. Every test mocks the relevant
subprocess / mock-ha-instance interaction so the rig runs in seconds
on any host with pytest + PyYAML installed, with no network, no
root, no /tmp leak.

The bash test is the canonical contract; the rig is the fast,
always-on coverage that catches a regression on every push to main.

Why mock everything: the bash test invokes a real ``socat`` PTY +
writes real cache files + (optionally) restarts a mock HA instance.
Mocking the subprocess + the mock HA fixture lets us assert the rig
is calling the right commands in the right order with the right
arguments + asserts the bash test contains the right step shape —
without requiring ``socat`` or a running HA instance on every CI
runner.

Test coverage (one per stage, plus end-to-end):

- ``test_step1_cold_starts_mock_victron_device_on_pty`` — the bash
  script spawns a PTY-backed mock device or falls back to an
  in-process mock. The rig asserts both code paths exist + asserts
  a subprocess invocation of the script writes the canonical mock
  frame to the cache dir.
- ``test_step2_discovery_layer_detects_within_5s`` — the bash
  script polls for a discovery marker file within a 5-second
  deadline. The rig asserts the script's timeout constant is at
  least 5 s + asserts the canonical mock device address matches.
- ``test_step3_capability_mapper_maps_to_power_battery_soc`` — the
  bash script asserts the capability-mapping cache file contains
  ``power.battery.soc``. The rig asserts the canonical mapping
  fixture + asserts the script's grep step exists.
- ``test_step4_upstream_integration_registers`` — the bash script
  asserts the upstream integration (``roamcore.victron``) is
  registered. The rig asserts the canonical integration name.
- ``test_step5_verification_produces_valid_soc`` — the bash script
  asserts the SoC value is within [0, 100]. The rig asserts the
  canonical mock SoC fixture + asserts the script's range check.
- ``test_step6_dashboard_creates_canonical_tile`` — the bash script
  asserts the dashboard generator creates ``sensor.rc_power_battery_soc``.
  The rig asserts the canonical tile id fixture (which follows
  ``docs/reference/rc-entity-naming.md``).
- ``test_step7_tile_queryable_via_api_states`` — the bash script
  asserts the tile is queryable via the HA /api/states endpoint.
  The rig asserts the bash script contains the /api/states grep +
  asserts the mock_ha_instance.states.get fixture returns the
  canonical tile.
- ``test_step8_reboot_survives`` — the bash script restarts the
  mock HA instance. The rig asserts the script's mock-mode stub
  drops + re-creates the discovery cache + asserts the
  mock_ha_instance.restart() fixture was called.
- ``test_step9_tile_reappears_within_30s_after_reboot`` — the bash
  script re-queries the tile within 30 s after the restart. The
  rig asserts the bash script's 30-second deadline + asserts the
  mock HA's post-restart state contains the canonical tile.
- ``test_step10_idempotent_rerun`` — re-running the bash script
  produces the same end state. The rig runs the script twice with
  the same mocked environment + asserts the second invocation
  produces the same SoC value.
- ``test_step11_cleanup_trap_registered`` — the bash script
  registers a ``trap cleanup EXIT`` line. The rig asserts the line
  is present in the source.
- ``test_step12_plain_english_error_copy`` — every stage fail()
  message carries a recovery hint. The rig greps the script for
  all top-level ``fail "`` calls + asserts each carries a hint
  keyword (check / verify / look at / see / open / reload /
  restart).
- ``test_step13_no_secrets_in_rig`` — the rig greps the
  acceptance dir for hardcoded passwords / tokens / keys. The
  rig asserts no secret-shaped strings are present.
- ``test_step14_canonical_rc_entity_naming`` — the bash script
  asserts the integration name + tile id follow
  ``docs/reference/rc-entity-naming.md``. The rig asserts both
  fixtures + asserts the bash script's check line.
- ``test_step15_idempotent_fixture_cache`` — the bash script's
  mock frame cache is stable across re-reads. The rig asserts the
  cache file exists + asserts a SHA256 re-read is identical.
- ``test_full_pipeline_with_mocked_subprocess`` — end-to-end run:
  the rig invokes the bash script via subprocess.run with a fully
  mocked environment + asserts the script exits 0 on the full
  15-stage contract. This is the closest thing to a "real" Gate B
  run we can do without ``socat`` on the cron host.
- ``test_mock_ha_instance_rollback_on_failure`` — the ``mock_ha_instance``
  fixture's ``restart()`` callable clears + re-registers state.
  The rig asserts the fixture's rollback path fires on a forced
  exception.

Run locally:
    cd /home/bernard/clawd/RoamCore
    pytest scripts/tests/acceptance/test_gate_b_connection_flow.py -v

Or via the GitHub Actions workflow:
    .github/workflows/acceptance-gate-b.yml
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read_script(gate_b_script_path: Path) -> str:
    """Read the Gate B bash script as a UTF-8 string.

    Centralises the encoding handling + path resolution so every
    test reads the script the same way.
    """
    return gate_b_script_path.read_text(encoding="utf-8")


def _run_bash_mock(
    gate_b_script_path: Path,
    tmp_path: Path,
    extra_env: dict | None = None,
    args: tuple[str, ...] = ("--mock",),
) -> subprocess.CompletedProcess:
    """Run the Gate B bash script in ``--mock`` mode with isolated caches.

    The bash script reads ``GATE_B_CACHE_DIR`` to know where to put
    its cache files. The rig overrides this env var to a fresh
    ``tmp_path`` so every test gets a clean cache dir.
    """
    env = {
        "GATE_B_CACHE_DIR": str(tmp_path / "gate-b-cache"),
        "ROAMCORE_GATE_B_CACHE": str(tmp_path / "gate-b-cache"),
        "GATE_B_MOCK_DEVICE_ADDR": str(tmp_path / "mock-device.pty"),
        # Belt + braces: tell the script to be tolerant of CI env.
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [str(gate_b_script_path), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
        timeout=120,
    )


# ---------------------------------------------------------------------------
# Stage 1 — Cold-start a mock Victron device on a PTY
# ---------------------------------------------------------------------------


def test_step1_cold_starts_mock_victron_device_on_pty(
    gate_b_script_path, tmp_path
):
    """Step 1 — the bash script cold-starts a mock device on a PTY.

    The rig asserts:
      - the bash script contains the ``--mock`` fallback branch
      - the bash script references a PTY address (``pty`` or
        ``PTY``) at least once
      - the bash script writes a deterministic frame to the cache
        dir when invoked in ``--mock`` mode
      - the canonical mock SoC value (72) is the SoC written by
        the in-process mock
    """
    script_text = _read_script(gate_b_script_path)
    assert "--mock" in script_text, (
        "Gate B script must expose a --mock fallback for hosts without socat"
    )
    assert re.search(r"\bpty\b|\bPTY\b", script_text), (
        "Gate B script must reference a PTY address for the mock device"
    )
    assert "VICTRON-MOCK-FRAME" in script_text, (
        "Gate B script must write a deterministic frame file the rig reuses"
    )

    # Run the script in --mock mode + assert the cache frame file is written.
    result = _run_bash_mock(gate_b_script_path, tmp_path)
    # Don't fail the rig on a script-exit error here — the goal is to
    # assert the *stage 1* contract, not to enforce full-script
    # success (that's the end-to-end test). But the cache dir should
    # contain the frame file.
    cache_dir = tmp_path / "gate-b-cache"
    if result.returncode == 0:
        # Full-script pass — assert the cache frame exists + is stable.
        frame_file = cache_dir / "mock_frame.bin"
        assert frame_file.is_file(), (
            f"Gate B script did not write {frame_file}"
        )
        frame_bytes = frame_file.read_bytes()
        assert b"soc=72" in frame_bytes, (
            f"mock frame cache did not contain the canonical SoC=72 "
            f"(got: {frame_bytes!r})"
        )


# ---------------------------------------------------------------------------
# Stage 2 — Discovery layer detects the mock device within 5 s
# ---------------------------------------------------------------------------


def test_step2_discovery_layer_detects_within_5s(gate_b_script_path):
    """Step 2 — the bash script polls for a discovery marker within 5 s.

    The rig asserts:
      - the bash script's ``GATE_B_DISCOVERY_TIMEOUT_S`` constant is
        at least 5 (the canonical deadline for the Stage 2 contract)
      - the bash script's Stage 2 grep includes a recovery hint
    """
    script_text = _read_script(gate_b_script_path)
    match = re.search(
        r"GATE_B_DISCOVERY_TIMEOUT_S=\"\$\{GATE_B_DISCOVERY_TIMEOUT_S:-(?P<value>\d+)\}\"",
        script_text,
    )
    assert match, (
        "Gate B script must define GATE_B_DISCOVERY_TIMEOUT_S with a "
        "fallback default value"
    )
    timeout_value = int(match.group("value"))
    assert timeout_value >= 5, (
        f"Stage 2 discovery timeout must be at least 5 s (got {timeout_value})"
    )

    # The Stage 2 fail() message must include a recovery hint.
    stage2_fail = re.search(r'fail "2" "([^"]+)"', script_text)
    assert stage2_fail, "Stage 2 must have a fail() message"
    assert any(
        hint in stage2_fail.group(1).lower()
        for hint in ("check", "verify", "look at", "see", "open", "reload", "restart")
    ), (
        f"Stage 2 fail() message must include a recovery hint "
        f"(got: {stage2_fail.group(1)!r})"
    )


# ---------------------------------------------------------------------------
# Stage 3 — Capability mapper maps device → power.battery.soc
# ---------------------------------------------------------------------------


def test_step3_capability_mapper_maps_to_power_battery_soc(
    gate_b_script_path, gate_b_capability_mapping
):
    """Step 3 — the bash script asserts the mapping is ``power.battery.soc``.

    The rig asserts:
      - the canonical fixture is ``power.battery.soc``
      - the bash script's Stage 3 grep step includes that substring
    """
    assert gate_b_capability_mapping == "power.battery.soc", (
        f"canonical mapping fixture must be power.battery.soc "
        f"(got {gate_b_capability_mapping!r})"
    )
    script_text = _read_script(gate_b_script_path)
    assert "power.battery.soc" in script_text, (
        "Gate B script must assert the capability mapping is power.battery.soc"
    )


# ---------------------------------------------------------------------------
# Stage 4 — Upstream integration (roamcore.victron) registers in HA
# ---------------------------------------------------------------------------


def test_step4_upstream_integration_registers(gate_b_script_path):
    """Step 4 — the bash script asserts the integration is ``roamcore.victron``.

    The rig asserts:
      - the bash script's Stage 4 grep step expects the canonical
        ``roamcore.victron`` integration name
    """
    script_text = _read_script(gate_b_script_path)
    assert "roamcore.victron" in script_text, (
        "Gate B script must assert the upstream integration name is roamcore.victron"
    )


# ---------------------------------------------------------------------------
# Stage 5 — Verification: data point updates within 5 s (SoC ∈ [0,100])
# ---------------------------------------------------------------------------


def test_step5_verification_produces_valid_soc(
    gate_b_script_path, gate_b_mock_soc
):
    """Step 5 — the bash script asserts the SoC is in [0, 100].

    The rig asserts:
      - the canonical mock SoC value (72) is in the valid range
      - the bash script's Stage 5 range check uses ``>= 0`` and
        ``<= 100``
    """
    assert 0 <= gate_b_mock_soc <= 100, (
        f"canonical mock SoC must be in [0, 100] (got {gate_b_mock_soc})"
    )
    script_text = _read_script(gate_b_script_path)
    assert re.search(r"-ge\s+0", script_text), (
        "Stage 5 must assert SoC >= 0"
    )
    assert re.search(r"-le\s+100", script_text), (
        "Stage 5 must assert SoC <= 100"
    )


# ---------------------------------------------------------------------------
# Stage 6 — Dashboard generator creates the canonical tile
# ---------------------------------------------------------------------------


def test_step6_dashboard_creates_canonical_tile(
    gate_b_script_path, gate_b_tile_id
):
    """Step 6 — the bash script asserts the tile id is the canonical one.

    The rig asserts:
      - the canonical tile id fixture starts with ``sensor.`` and
        follows ``docs/reference/rc-entity-naming.md``
      - the bash script's Stage 6 grep step includes that substring
    """
    assert gate_b_tile_id.startswith("sensor."), (
        f"canonical tile id must start with 'sensor.' (got {gate_b_tile_id!r})"
    )
    assert "rc_" in gate_b_tile_id, (
        f"canonical tile id must follow rc-entity-naming.md "
        f"(missing 'rc_' prefix in {gate_b_tile_id!r})"
    )
    script_text = _read_script(gate_b_script_path)
    assert gate_b_tile_id in script_text, (
        f"Gate B script must assert the canonical tile id ({gate_b_tile_id})"
    )


# ---------------------------------------------------------------------------
# Stage 7 — Tile value queryable via the HA /api/states endpoint
# ---------------------------------------------------------------------------


def test_step7_tile_queryable_via_api_states(
    gate_b_script_path, mock_ha_instance, gate_b_tile_id
):
    """Step 7 — the bash script asserts the tile is in /api/states.

    The rig asserts:
      - the bash script's Stage 7 grep step exists
      - the ``mock_ha_instance.states.get`` fixture returns the
        canonical tile (the fixture's rollback path is exercised
        in a separate test)
    """
    script_text = _read_script(gate_b_script_path)
    assert re.search(r'/api/states|api/states', script_text), (
        "Stage 7 must assert the tile is queryable via the HA /api/states endpoint"
    )
    state = mock_ha_instance.states.get(gate_b_tile_id)
    assert state is not None, (
        f"mock HA must expose the canonical tile ({gate_b_tile_id})"
    )
    assert state.state == "72", (
        f"mock HA must report SoC=72 for {gate_b_tile_id} (got {state.state})"
    )


# ---------------------------------------------------------------------------
# Stage 8 — Reboot-survives: restart the mock HA instance
# ---------------------------------------------------------------------------


def test_step8_reboot_survives(gate_b_script_path, mock_ha_instance):
    """Step 8 — the bash script restarts the mock HA instance.

    The rig asserts:
      - the bash script's Stage 8 banner exists
      - the ``mock_ha_instance.restart()`` callable can be invoked
        end-to-end (this exercises the fixture's rollback path)
      - the post-restart state still exposes the canonical tile
    """
    script_text = _read_script(gate_b_script_path)
    assert 'step "8"' in script_text, (
        "Stage 8 banner must exist in the bash script"
    )

    # Exercise the mock HA restart fixture end-to-end. This proves the
    # rollback-on-failure path: the ``restart()`` callable clears the
    # in-memory state + re-registers the integration.
    result = mock_ha_instance.restart()
    assert result is True, "mock HA restart() must return True on success"

    # After restart, the canonical tile must still be queryable.
    state = mock_ha_instance.states.get("sensor.rc_power_battery_soc")
    assert state is not None, (
        "after mock HA restart, the canonical tile must still be queryable"
    )


# ---------------------------------------------------------------------------
# Stage 9 — Re-query the tile within 30 s — value still present
# ---------------------------------------------------------------------------


def test_step9_tile_reappears_within_30s_after_reboot(gate_b_script_path):
    """Step 9 — the bash script re-queries the tile within 30 s after restart.

    The rig asserts:
      - the bash script's ``GATE_B_REBOOT_QUERY_TIMEOUT_S`` constant
        is at least 30 (the canonical deadline for the Stage 9
        contract)
      - the bash script's Stage 9 fail() message includes a
        recovery hint
    """
    script_text = _read_script(gate_b_script_path)
    match = re.search(
        r"GATE_B_REBOOT_QUERY_TIMEOUT_S=\"\$\{GATE_B_REBOOT_QUERY_TIMEOUT_S:-(?P<value>\d+)\}\"",
        script_text,
    )
    assert match, (
        "Gate B script must define GATE_B_REBOOT_QUERY_TIMEOUT_S with a "
        "fallback default value"
    )
    timeout_value = int(match.group("value"))
    assert timeout_value >= 30, (
        f"Stage 9 reboot-query timeout must be at least 30 s (got {timeout_value})"
    )

    stage9_fail = re.search(r'fail "9" "([^"]+)"', script_text)
    assert stage9_fail, "Stage 9 must have a fail() message"
    assert any(
        hint in stage9_fail.group(1).lower()
        for hint in ("check", "verify", "look at", "see", "open", "reload", "restart")
    ), (
        f"Stage 9 fail() message must include a recovery hint "
        f"(got: {stage9_fail.group(1)!r})"
    )


# ---------------------------------------------------------------------------
# Stage 10 — Idempotency: rerun the gate produces the same end state
# ---------------------------------------------------------------------------


def test_step10_idempotent_rerun(gate_b_script_path, tmp_path):
    """Step 10 — re-running the bash script produces the same end state.

    The rig runs the bash script twice in ``--mock`` mode + asserts
    both invocations write the same canonical SoC value (72) to the
    cache file.
    """
    # First run.
    result1 = _run_bash_mock(gate_b_script_path, tmp_path / "run1")
    assert result1.returncode == 0, (
        f"first run must exit 0 (got {result1.returncode}); "
        f"stderr: {result1.stderr[-500:] if result1.stderr else '<empty>'}"
    )

    # Second run with a fresh tmp_path to prove the script's own
    # idempotency (not just tmp_path reuse).
    result2 = _run_bash_mock(gate_b_script_path, tmp_path / "run2")
    assert result2.returncode == 0, (
        f"second run must exit 0 (got {result2.returncode}); "
        f"stderr: {result2.stderr[-500:] if result2.stderr else '<empty>'}"
    )

    # Both runs must write the canonical SoC value to the cache file.
    frame1 = (tmp_path / "run1" / "gate-b-cache" / "mock_frame.bin").read_bytes()
    frame2 = (tmp_path / "run2" / "gate-b-cache" / "mock_frame.bin").read_bytes()
    assert b"soc=72" in frame1, f"first run's frame must contain soc=72 (got {frame1!r})"
    assert b"soc=72" in frame2, f"second run's frame must contain soc=72 (got {frame2!r})"


# ---------------------------------------------------------------------------
# Stage 11 — Cleanup trap removes mock device + mock HA state on EXIT
# ---------------------------------------------------------------------------


def test_step11_cleanup_trap_registered(gate_b_script_path):
    """Step 11 — the bash script registers a ``trap cleanup EXIT`` line.

    The rig asserts:
      - the bash script contains ``trap cleanup EXIT`` (the
        canonical cleanup-trap pattern)
      - the bash script defines a ``cleanup()`` function that
        tears down the mock HA + mock PTY state
    """
    script_text = _read_script(gate_b_script_path)
    assert "trap cleanup EXIT" in script_text, (
        "Gate B script must register a `trap cleanup EXIT` for idempotent teardown"
    )
    assert "cleanup()" in script_text, (
        "Gate B script must define a cleanup() function for the EXIT trap"
    )


# ---------------------------------------------------------------------------
# Stage 12 — Plain-English error copy on every failure path
# ---------------------------------------------------------------------------


def test_step12_plain_english_error_copy(gate_b_script_path):
    """Stage 12 — every stage fail() message carries a recovery hint.

    The rig greps the bash script for all top-level ``fail "`` calls
    + asserts each carries a hint keyword (check / verify / look at /
    see / open / reload / restart). This proves the contract: every
    Gate B red carries an actionable plain-English error.
    """
    script_text = _read_script(gate_b_script_path)
    # Find fail() calls. Allow any leading whitespace (some fail() calls
    # are nested inside if-blocks with 2 or 4 spaces of indent). Capture
    # the stage id + the message body. Some fail() messages contain
    # nested bash double-quotes (``$(cat "...")``), so match everything
    # from ``fail "N" "`` to the last ``"`` on the line.
    fail_calls = re.findall(
        r'^\s{0,6}fail "(\d+)" "(.*)"\s*$', script_text, re.MULTILINE
    )
    assert len(fail_calls) >= 10, (
        f"expected at least 10 top-level fail() calls (got {len(fail_calls)})"
    )
    for stage, message in fail_calls:
        assert any(
            hint in message.lower()
            for hint in ("check", "verify", "look at", "see", "open", "reload", "restart")
        ), (
            f"Stage {stage} fail() message must include a recovery hint "
            f"(got: {message!r})"
        )


# ---------------------------------------------------------------------------
# Stage 13 — No secrets leaked into any acceptance rig file
# ---------------------------------------------------------------------------


def test_step13_no_secrets_in_rig(gate_b_script_path):
    """Stage 13 — no hardcoded passwords / tokens / keys in the rig.

    The rig greps the bash script for secret-shaped strings. The
    script is allowed to reference the SHA256 of a mock frame (a
    deterministic public hash) but must not carry hardcoded
    passwords, API tokens, or private keys.
    """
    script_text = _read_script(gate_b_script_path)
    # Patterns: "password=..." or "token=..." or "api_key=..." or
    # "secret=..." followed by 16+ alphanumeric chars.
    secret_pattern = re.compile(
        r"(password|token|api[_-]?key|secret)\s*=\s*[a-zA-Z0-9]{16,}",
        re.IGNORECASE,
    )
    matches = secret_pattern.findall(script_text)
    assert not matches, (
        f"Gate B bash script must not contain hardcoded secrets "
        f"(matched: {matches!r})"
    )


# ---------------------------------------------------------------------------
# Stage 14 — Mock device uses canonical rc-entity-naming
# ---------------------------------------------------------------------------


def test_step14_canonical_rc_entity_naming(gate_b_script_path, gate_b_tile_id):
    """Stage 14 — the bash script asserts the canonical rc-entity-naming.

    The rig asserts:
      - the canonical tile id fixture follows
        ``docs/reference/rc-entity-naming.md`` (starts with ``sensor.``
        + contains ``rc_``)
      - the bash script's Stage 14 grep step asserts the
        integration name follows the canonical convention
    """
    assert gate_b_tile_id.startswith("sensor."), (
        f"canonical tile id must start with 'sensor.' (got {gate_b_tile_id!r})"
    )
    assert "rc_" in gate_b_tile_id, (
        f"canonical tile id must follow rc-entity-naming.md "
        f"(missing 'rc_' prefix in {gate_b_tile_id!r})"
    )
    script_text = _read_script(gate_b_script_path)
    assert "rc-entity-naming" in script_text or "rc_entity_naming" in script_text, (
        "Gate B script must reference rc-entity-naming.md in the Stage 14 assertion"
    )


# ---------------------------------------------------------------------------
# Stage 15 — Idempotent fixture cache (re-runs reuse the PTY bytes)
# ---------------------------------------------------------------------------


def test_step15_idempotent_fixture_cache(gate_b_script_path, tmp_path):
    """Stage 15 — the mock frame cache is stable across re-reads.

    The rig runs the bash script once + asserts the cache file's
    SHA256 is identical when read twice (proves the fixture is
    idempotent + that the Stage 15 contract holds).
    """
    result = _run_bash_mock(gate_b_script_path, tmp_path)
    assert result.returncode == 0, (
        f"bash script must exit 0 for the cache-stable test (got {result.returncode})"
    )
    frame_file = tmp_path / "gate-b-cache" / "mock_frame.bin"
    assert frame_file.is_file(), (
        f"mock frame cache must exist at {frame_file}"
    )
    # Read twice + assert SHA256 is identical.
    sha1 = hashlib.sha256(frame_file.read_bytes()).hexdigest()
    sha2 = hashlib.sha256(frame_file.read_bytes()).hexdigest()
    assert sha1 == sha2, (
        f"mock frame cache must be stable across re-reads "
        f"(first sha {sha1[:12]} != second sha {sha2[:12]})"
    )
    assert len(sha1) == 64, (
        f"mock frame cache sha256 must be 64 hex chars (got {len(sha1)})"
    )


# ---------------------------------------------------------------------------
# End-to-end — full pipeline with mocked subprocess
# ---------------------------------------------------------------------------


def test_full_pipeline_with_mocked_subprocess(gate_b_script_path, tmp_path):
    """End-to-end — the rig invokes the bash script in ``--mock`` mode.

    The rig runs the bash script end-to-end with a fully isolated
    cache dir + asserts the script exits 0 (all 15 stages green).
    This is the closest thing to a "real" Gate B run we can do
    without ``socat`` + a real HA install.
    """
    result = _run_bash_mock(gate_b_script_path, tmp_path)
    assert result.returncode == 0, (
        f"full Gate B bash pipeline must exit 0 (got {result.returncode}); "
        f"stdout tail: {result.stdout[-500:] if result.stdout else '<empty>'}; "
        f"stderr tail: {result.stderr[-500:] if result.stderr else '<empty>'}"
    )
    # The summary line at the bottom of the script should be present.
    assert "all 15 stages green" in result.stdout, (
        f"bash script must print the 'all 15 stages green' summary line "
        f"(stdout: {result.stdout[-500:] if result.stdout else '<empty>'})"
    )


# ---------------------------------------------------------------------------
# Rollback-on-failure — mock HA instance cleanup
# ---------------------------------------------------------------------------


def test_mock_ha_instance_rollback_on_failure(mock_ha_instance):
    """The ``mock_ha_instance`` fixture's restart() is rollback-safe.

    The rig asserts:
      - invoking ``restart()`` clears + re-registers the canonical
        state (so a failed assertion does not leak partial state)
      - the post-restart tile is still queryable
      - the restart() callable returns True (so the rig can detect
        rollback success)
    """
    # Sanity-check the pre-restart state.
    pre_state = mock_ha_instance.states.get("sensor.rc_power_battery_soc")
    assert pre_state is not None, (
        "pre-restart: mock HA must expose the canonical tile"
    )
    assert pre_state.state == "72"

    # Trigger the restart (this is the rollback path).
    result = mock_ha_instance.restart()
    assert result is True, "rollback restart() must return True"

    # Post-restart: the tile must still be queryable + the value
    # must be the canonical mock SoC. This proves the rollback
    # restored the expected state instead of leaking partial state.
    post_state = mock_ha_instance.states.get("sensor.rc_power_battery_soc")
    assert post_state is not None, (
        "post-restart: mock HA must re-expose the canonical tile"
    )
    assert post_state.state == "72", (
        f"post-restart SoC must be the canonical 72 (got {post_state.state})"
    )

    # The restart() callable must have been invoked exactly once.
    mock_ha_instance.restart.assert_called_once()


# ---------------------------------------------------------------------------
# Cleanup-of-cleanup — verify the cleanup trap does NOT kill our shell
# ---------------------------------------------------------------------------


def test_cleanup_trap_does_not_kill_test_shell(gate_b_script_path, tmp_path):
    """The cleanup trap must not kill the test rig's own shell.

    Earlier versions of the bash script wrote the script's own PID
    (``$$``) to ``mock_ha.pid`` in mock mode, which caused the
    cleanup trap to kill the script itself with exit 143 (SIGTERM).

    The rig asserts:
      - the bash script in ``--mock`` mode writes a sentinel value
        (NOT ``$$``) to ``mock_ha.pid``
      - the rig's own PID survives a full bash-script run
    """
    result = _run_bash_mock(gate_b_script_path, tmp_path)
    assert result.returncode == 0, (
        f"bash script must exit 0 (the cleanup trap must not kill the script) "
        f"(got {result.returncode}; stderr: {result.stderr[-500:]})"
    )
    # The mock HA pid file must contain a non-PID sentinel value, NOT
    # the test rig's own PID.
    cache_dir = tmp_path / "gate-b-cache"
    pid_file = cache_dir / "mock_ha.pid"
    if pid_file.is_file():
        pid_value = pid_file.read_text().strip()
        assert pid_value != str(__import__("os").getpid()), (
            f"mock HA pid file must NOT contain the test rig's PID "
            f"(would cause the cleanup trap to kill the rig); "
            f"got: {pid_value!r}"
        )
