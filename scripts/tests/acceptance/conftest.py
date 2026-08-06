"""Pytest config + fixtures for the Gate A clean-install acceptance rig.

Wave 9 #123.d.i — Phase 7 — Acceptance tests foundation + Gate A.

Why this file exists:

The Gate A pytest rig at
``scripts/tests/acceptance/test_gate_a_clean_install.py`` exercises the
six-step clean-install contract (download HAOS + boot qemu + wait for
HTTP 200 + verify integration detected + verify wizard reachable +
tear down) without actually launching qemu on the test host.

This conftest provides the shared fixtures the Gate A + Gate B test
rigs depend on:

- ``gate_a_script_path`` — the absolute path to
  ``scripts/tests/acceptance/gate_a_clean_install.sh``.
- ``gate_b_script_path`` — the absolute path to
  ``scripts/tests/acceptance/gate_b_connection_flow.sh``.
- ``mock_subprocess_run`` — a ``unittest.mock.MagicMock`` that mimics
  ``subprocess.run`` returning canned ``CompletedProcess`` objects.
- ``sample_haos_response`` — a canned ``requests.get`` response that
  returns HTTP 200 + the JSON body Home Assistant returns for
  ``/manifest.json`` on a fresh install.
- ``haos_sha256_mock`` — a pinned 64-char hex string that mirrors the
  ``base_image.expected_sha256`` in
  ``scripts/build/hub-golden-image.manifest.yml``.
- ``onboarding_html_sample`` — a canned setup-wizard page body.
- ``mock_victron_device`` — a MagicMock that mimics a PTY-backed
  Victron device (Gate B).
- ``mock_ha_instance`` — a MagicMock that mimics a Home Assistant
  instance (Gate B).
- ``gate_b_capability_mapping`` — the canonical Victron mapping.
- ``gate_b_mock_soc`` — the canonical mock SoC value (72).
- ``gate_b_tile_id`` — the canonical HA tile id.

All fixtures are repo-local only — they touch no network, no /tmp,
no real processes. The rig is fully idempotent: re-running pytest
on the same input produces the same outcome (mocked subprocess is a
pure function of the canned inputs).

Why this lives in ``scripts/tests/acceptance/conftest.py`` and not in
a sibling ``tests/conftest.py``: pytest auto-loads the conftest at
the test directory level, and pytest's collection treats each
``tests/`` directory as its own rootdir when running with
``pytest scripts/tests/acceptance/``. Putting the fixtures here means
the rig is runnable on its own (no global conftest dependency) +
does not accidentally affect any other test directory in the repo.

Run locally:
    cd /home/bernard/clawd/RoamCore
    pytest scripts/tests/acceptance/test_gate_a_clean_install.py -v
    pytest scripts/tests/acceptance/test_gate_b_connection_flow.py -v
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ACCEPTANCE_DIR = Path(__file__).resolve().parent
REPO_ROOT = ACCEPTANCE_DIR.parents[2]   # acceptance/ -> tests/ -> scripts/ -> repo
GATE_A_SCRIPT = ACCEPTANCE_DIR / "gate_a_clean_install.sh"
GATE_B_SCRIPT = ACCEPTANCE_DIR / "gate_b_connection_flow.sh"


# ---------------------------------------------------------------------------
# Gate A fixtures (Wave 9 #123.d.i)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def gate_a_script_path() -> Path:
    """Absolute path to the Gate A bash acceptance test.

    Every test reads this path either as a string (for content
    inspection — verifying the script has the six-step shape) or as a
    ``subprocess.run`` argument (for end-to-end invocation in the
    mocked rig). Centralising the path keeps the test rig repo-root-
    agnostic; the only assumption is that the test file is invoked
    from the repo root (or with ``--rootdir`` pointing at the repo).
    """
    assert GATE_A_SCRIPT.is_file(), (
        f"Gate A bash script is missing at {GATE_A_SCRIPT}"
    )
    assert GATE_A_SCRIPT.stat().st_mode & 0o111, (
        f"Gate A bash script at {GATE_A_SCRIPT} is not executable "
        f"(chmod +x scripts/tests/acceptance/gate_a_clean_install.sh)"
    )
    return GATE_A_SCRIPT


@pytest.fixture
def mock_subprocess_run() -> MagicMock:
    """A MagicMock that mimics ``subprocess.run``.

    Each call returns a ``MagicMock(return_value=CompletedProcess(...))``
    shape so the test rig can introspect ``result.returncode`` +
    ``result.stdout`` + ``result.stderr`` without launching a real
    subprocess.

    Defaults (the test rig overrides these per-step):
      - ``returncode`` = 0  (success)
      - ``stdout``    = b""
      - ``stderr``    = b""

    The mock is reset before every test (function scope) so tests do
    not leak canned responses into each other.
    """
    mock = MagicMock()
    mock.return_value.returncode = 0
    mock.return_value.stdout = b""
    mock.return_value.stderr = b""
    return mock


@pytest.fixture
def sample_haos_response() -> dict:
    """Canned ``requests.get`` response payload.

    Mirrors the JSON shape Home Assistant returns for ``/manifest.json``
    on a fresh HAOS install — the minimum surface that the Step 4
    substring check (`grep roamcore`) needs to pass.
    """
    return {
        "manifest_version": 1,
        "integrations": [
            {"domain": "roamcore", "name": "RoamCore"},
            {"domain": "roamcore_openclaw_api", "name": "RoamCore OpenClaw API"},
        ],
        "core": "2026.8.0",
        "supervisor": "2026.08.0",
    }


@pytest.fixture
def haos_sha256_mock() -> str:
    """Pinned HAOS 14.1 generic-x86-64 SHA256."""
    return "504c10f5703ebadcc70ebe625929f2e7910d64c78145a87725eb6baabe1072b0"


@pytest.fixture
def onboarding_html_sample() -> str:
    """Canned setup-wizard page body."""
    return (
        "<!doctype html><html><head><title>Home Assistant Onboarding</title>"
        "</head><body>"
        "<h1>Welcome to your new Home Assistant setup wizard</h1>"
        "<p>This wizard walks you through setting up your account.</p>"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# Gate B fixtures — Wave 9 #123.d.ii — Phase 7 — connection flow.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def gate_b_script_path() -> Path:
    """Absolute path to the Gate B bash acceptance test.

    Every test reads this path either as a string (for content
    inspection — verifying the script has the 15-stage shape + the
    cleanup trap + the rc-entity-naming markers) or as a
    ``subprocess.run`` argument (for end-to-end invocation in the
    mocked rig).
    """
    assert GATE_B_SCRIPT.is_file(), (
        f"Gate B bash script is missing at {GATE_B_SCRIPT}"
    )
    assert GATE_B_SCRIPT.stat().st_mode & 0o111, (
        f"Gate B bash script at {GATE_B_SCRIPT} is not executable "
        f"(chmod +x scripts/tests/acceptance/gate_b_connection_flow.sh)"
    )
    return GATE_B_SCRIPT


@pytest.fixture
def mock_victron_device():
    """A MagicMock that mimics a PTY-backed Victron device."""
    mock = MagicMock()
    mock.address = "/tmp/roamcore_gate_b_victron.pty"
    mock.read_frame.return_value = b"VICTRON-MOCK-FRAME-v1\nsoc=72\n"
    mock.connected = True
    return mock


@pytest.fixture
def mock_ha_instance():
    """A MagicMock that mimics a Home Assistant instance."""

    class _State:
        def __init__(self, entity_id, state, attributes=None):
            self.entity_id = entity_id
            self.state = state
            self.attributes = attributes or {}

    class _StatesAPI:
        def __init__(self):
            self._states = {
                "sensor.rc_power_battery_soc": _State(
                    "sensor.rc_power_battery_soc", "72",
                    {"unit_of_measurement": "%", "device_class": "battery"},
                ),
            }

        def get(self, entity_id):
            return self._states.get(entity_id)

        def all(self):
            return list(self._states.values())

    mock = MagicMock()
    mock.states = _StatesAPI()
    mock.entity_registry = MagicMock()
    mock.entity_registry.entities.get_entity_id.return_value = (
        "sensor.rc_power_battery_soc"
    )

    def _restart():
        mock.states = _StatesAPI()
        return True
    mock.restart = MagicMock(side_effect=_restart)
    return mock


@pytest.fixture
def gate_b_capability_mapping() -> str:
    """Canonical capability-mapping for the mock Victron device."""
    return "power.battery.soc"


@pytest.fixture
def gate_b_mock_soc() -> int:
    """Canonical mock SoC value (within the [0,100] SoC range)."""
    return 72


@pytest.fixture
def gate_b_tile_id() -> str:
    """Canonical HA tile id for the Victron battery SoC."""
    return "sensor.rc_power_battery_soc"
