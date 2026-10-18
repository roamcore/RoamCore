"""Pytest config + fixtures for the Gate A clean-install acceptance rig.

Wave 9 #123.d.i — Phase 7 — Acceptance tests foundation + Gate A.

Why this file exists:

The Gate A pytest rig at
``scripts/tests/acceptance/test_gate_a_clean_install.py`` exercises the
six-step clean-install contract (download HAOS + boot qemu + wait for
HTTP 200 + verify integration detected + verify wizard reachable +
tear down) without actually launching qemu on the test host.

This conftest provides the four fixtures the test rig depends on:

- ``gate_a_script_path`` — the absolute path to
  ``scripts/tests/acceptance/gate_a_clean_install.sh``. Every test
  uses this to read the script as a string + invoke subprocess.run
  against it. Centralising the path keeps the test rig repo-root-
  agnostic (no hardcoded absolute paths).
- ``mock_subprocess_run`` — a ``unittest.mock.MagicMock`` that mimics
  ``subprocess.run`` returning canned ``CompletedProcess`` objects.
  The test rig swaps this in via ``monkeypatch.setattr(subprocess,
  "run", mock_subprocess_run)`` so the six steps can be exercised
  end-to-end without qemu, without network, and without root.
- ``sample_haos_response`` — a canned ``requests.get`` response that
  returns HTTP 200 + the JSON body Home Assistant returns for
  ``/manifest.json`` on a fresh install. The Step 4 + Step 5 assertions
  read this canned response to verify the substring matches.
- ``haos_sha256_mock`` — a pinned 64-char hex string that mirrors the
  ``base_image.expected_sha256`` in
  ``scripts/build/hub-golden-image.manifest.yml``. The Step 1 SHA
  verification reads this fixture so the rig asserts the canonical
  pinned SHA is the one the bash test would compare against.

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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def gate_a_script_path() -> Path:
    """Absolute path to the Gate A bash acceptance test.

    Every test reads this path either as a string (for content
    inspection — verifying the script has the six-step shape) or as a
    ``subprocess.run`` argument (for end-to-end invocation in the
    mocked rig). Centralising the path keeps the rig repo-root-
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
    # The first call returns a generic CompletedProcess-like object;
    # individual tests override the return_value to simulate step-by-
    # step outcomes.
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

    The fixture is a plain dict so the rig can hand it to a
    ``MagicMock`` whose ``.json()`` returns it; tests do NOT import
    ``requests`` (that would require network access on the test host).
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
    """Pinned HAOS 14.1 generic-x86-64 SHA256.

    Mirrors the ``base_image.expected_sha256`` constant in
    ``scripts/build/hub-golden-image.manifest.yml``. The rig hands
    this to the bash script as the expected SHA so the Step 1
    "Cached SHA matches the pinned SHA — skipping download" path
    can be exercised without actually computing a real SHA.
    """
    return "504c10f5703ebadcc70ebe625929f2e7910d64c78145a87725eb6baabe1072b0"


@pytest.fixture
def onboarding_html_sample() -> str:
    """Canned setup-wizard page body.

    Mirrors the substring the bash script's Step 5 grep checks for
    (``wizard`` OR ``onboarding`` OR ``setup``). Tests inject this
    into a mocked ``curl`` response so Step 5 can be verified
    end-to-end without a running HAOS install.
    """
    return (
        "<!doctype html><html><head><title>Home Assistant Onboarding</title>"
        "</head><body>"
        "<h1>Welcome to your new Home Assistant setup wizard</h1>"
        "<p>This wizard walks you through setting up your account.</p>"
        "</body></html>"
    )
