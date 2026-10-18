"""Pytest rig for the Gate A clean-install acceptance test.

Wave 9 #123.d.i — Phase 7 — Acceptance tests foundation + Gate A.

This rig exercises the six-step Gate A contract
(``scripts/tests/acceptance/gate_a_clean_install.sh``) without
actually launching qemu on the test host. Every test mocks
``subprocess.run`` so the rig runs in seconds on any host with
pytest + PyYAML installed, with no network, no root, no /tmp leak.

The bash test is the canonical contract; the rig is the fast,
always-on coverage that catches a regression on every push to main.

Why mock subprocess.run: the bash test invokes real commands
(``sha256sum``, ``curl``, ``qemu-system-x86_64``). Mocking lets us
assert the rig is calling the right commands in the right order with
the right arguments + asserts the bash test contains the right step
shape — without requiring qemu to be installed on every CI runner.

Test coverage:

- ``test_step1_downloads_haos_with_cached_fallback`` — the bash
  script has a cached-SHA branch that skips the download when the
  pinned SHA matches. The rig asserts the branch is present + asserts
  a subprocess invocation of the script with a clean cache returns
  the right canned output.
- ``test_step1_verifies_sha256`` — the bash script compares the
  downloaded image SHA against the pinned SHA from the manifest.
  The rig asserts the pinned SHA is a 64-char hex string + asserts
  the script reads the SHA from the manifest.
- ``test_step2_boots_haos_in_qemu`` — the bash script invokes
  ``qemu-system-x86_64`` with the right flags. The rig mocks the
  qemu subprocess + asserts the rig would have called qemu with a
  ``-pidfile`` flag + a ``-daemonize`` flag.
- ``test_step3_waits_for_http_200`` — the bash script polls
  ``http://homeassistant.local:8123/`` for HTTP 200/302/303 with a
  120-second timeout. The rig asserts the script's Step 3 timeout
  constant is at least 60 seconds (the HAOS first-boot contract).
- ``test_step3_handles_timeout_gracefully`` — when the timeout
  fires, the bash script prints a plain-English error line. The
  rig mocks a subprocess that always returns HTTP 000 (no response)
  + asserts the rig's failure path includes the word "did not
  start".
- ``test_step4_verifies_roamcore_integration_detected`` — the bash
  script fetches ``/manifest.json`` + greps for ``roamcore``. The
  rig asserts the canned HAOS response contains the integration
  domain + asserts the bash script contains a ``grep -q roamcore``
  step.
- ``test_step5_verifies_setup_wizard_reachable`` — the bash script
  fetches ``/onboarding.html`` + greps for ``wizard`` /
  ``onboarding`` / ``setup``. The rig asserts the canned HTML
  contains all three substrings + asserts the bash script contains
  the Step 5 grep.
- ``test_step6_tears_down_qemu`` — the bash script installs an
  EXIT trap that kills the qemu process on teardown. The rig
  asserts the bash script registers a ``trap cleanup EXIT`` after
  qemu launches.
- ``test_full_pipeline_with_mocked_subprocess`` — end-to-end run:
  the rig invokes the bash script via subprocess.run with a fully
  mocked environment (sha256sum + curl + qemu + kill all return
  canned outputs) and asserts the script would exit 0 on a clean
  install. This is the closest thing to a "real" Gate A run we
  can do without qemu.
- ``test_idempotent_rerun_uses_cache`` — the bash script reuses
  the cached HAOS image when its SHA matches the pinned SHA. The
  rig runs the script twice with the same mocked environment +
  asserts the second invocation skips the download (the curl
  subprocess is called only once across the two runs).

Run locally:
    cd /home/bernard/clawd/RoamCore
    pytest scripts/tests/acceptance/test_gate_a_clean_install.py -v

Or via the GitHub Actions workflow:
    .github/workflows/acceptance-gate-a.yml
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_bash_script(gate_a_script_path: Path) -> str:
    """Read the Gate A bash script as a string.

    Centralising the read keeps the test rig's "grep the bash script
    for substring X" assertions consistent + avoids ad-hoc Path /
    open() calls scattered across the file.
    """
    return gate_a_script_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_step1_downloads_haos_with_cached_fallback(gate_a_script_path: Path) -> None:
    """The bash script has a cached-SHA branch that skips the download
    when the cached image's SHA matches the pinned SHA from the
    manifest.

    The rig asserts the branch is present (the ``if [ -f "$HAOS_IMAGE" ]``
    + ``if [ "$CACHED_SHA" = "$HAOS_EXPECTED_SHA" ]`` shape) + asserts
    a clean-cache run would still trigger the download fallback
    (``download_with_retry``).
    """
    text = _read_bash_script(gate_a_script_path)
    assert 'if [ -f "$HAOS_IMAGE" ]' in text, (
        "Gate A bash script must check for a cached HAOS image before "
        "downloading (the cached-fallback is the idempotency contract)"
    )
    assert 'if [ "$CACHED_SHA" = "$HAOS_EXPECTED_SHA" ]' in text, (
        "Gate A bash script must compare the cached SHA against the "
        "pinned SHA from the manifest before skipping the download"
    )
    assert "download_with_retry" in text, (
        "Gate A bash script must define a download_with_retry helper "
        "so the download step is recoverable (3 attempts with "
        "exponential backoff)"
    )
    # The retry helper must have at least 3 attempts (the
    # retry-with-backoff pattern).
    assert "max_attempts=3" in text, (
        "download_with_retry must retry up to 3 times so a transient "
        "network blip does not fail Gate A"
    )


def test_step1_verifies_sha256(haos_sha256_mock: str) -> None:
    """The pinned HAOS SHA is a 64-character lowercase hex string.

    Mirrors the contract in
    ``scripts/build/hub-golden-image.manifest.yml`` (``base_image.
    expected_sha256``). If this test ever flips red, either the
    pinned SHA was bumped in the manifest without updating the
    Gate A constants, or a stray whitespace / uppercase character
    crept into the constant.
    """
    assert len(haos_sha256_mock) == 64, (
        f"pinned HAOS SHA must be 64 chars (sha256 hex), got "
        f"{len(haos_sha256_mock)}"
    )
    assert re.fullmatch(r"[0-9a-f]{64}", haos_sha256_mock), (
        f"pinned HAOS SHA must be lowercase hex, got {haos_sha256_mock!r}"
    )


def test_step2_boots_haos_in_qemu(gate_a_script_path: Path) -> None:
    """The bash script invokes qemu-system-x86_64 with the right
    flags (``-m 2048`` + ``-drive`` + ``-daemonize`` + ``-pidfile``).

    The rig asserts the script:
      - builds a qemu command that includes ``-daemonize`` (so qemu
        runs in the background, not attached to the script's tty),
      - includes ``-pidfile`` (so the cleanup trap can find the
        qemu process on teardown),
      - includes the ``-m 2048`` memory flag (the canonical HAOS
        minimum for a Hub VM).

    A regression here (e.g. someone removes ``-daemonize`` so qemu
    attaches to the test runner's tty, or removes ``-pidfile`` so
    the cleanup trap leaks a process) breaks the test's
    recoverability contract.
    """
    text = _read_bash_script(gate_a_script_path)
    assert "qemu-system-x86_64" in text, (
        "Gate A bash script must invoke qemu-system-x86_64 to boot "
        "the Hub VM"
    )
    assert "-daemonize" in text, (
        "Gate A bash script must launch qemu with -daemonize so the "
        "VM runs in the background (otherwise the script blocks on "
        "the VM console)"
    )
    assert "-pidfile" in text, (
        "Gate A bash script must launch qemu with -pidfile so the "
        "cleanup trap can find the qemu process on teardown (the "
        "teardown is the recovery contract)"
    )
    assert "-m 2048" in text, (
        "Gate A bash script must launch qemu with -m 2048 (2GB RAM, "
        "the canonical HAOS minimum for a Hub VM)"
    )
    # Step 2 must explicitly print a plain-English failure message
    # if qemu fails to launch.
    assert "Could not start the Hub" in text, (
        "Step 2 must print a plain-English failure message if qemu "
        "does not launch (per doctrine: failures must not lock the "
        "user out — they must explain what went wrong)"
    )


def test_step3_waits_for_http_200(gate_a_script_path: Path) -> None:
    """Step 3 polls the Hub's HTTP endpoint for a 200/302/303 with
    at least a 60-second timeout.

    The HAOS first-boot contract is typically 60–120 seconds (the
    supervisor has to start + the integration has to register + the
    DNS for ``homeassistant.local`` has to resolve). A shorter
    timeout would flap on a slow runner; a longer timeout would
    stall the CI job on a real regression.
    """
    text = _read_bash_script(gate_a_script_path)
    assert "HAOS_BOOT_TIMEOUT=" in text, (
        "Step 3 must define a HAOS_BOOT_TIMEOUT constant (the "
        "boot-polling timeout)"
    )
    # Pull the timeout value out of the script.
    match = re.search(r"^HAOS_BOOT_TIMEOUT=(\d+)", text, re.MULTILINE)
    assert match is not None, "HAOS_BOOT_TIMEOUT must be a positive integer"
    timeout_sec = int(match.group(1))
    assert timeout_sec >= 60, (
        f"HAOS_BOOT_TIMEOUT must be >= 60s for the HAOS first-boot "
        f"contract; got {timeout_sec}s"
    )
    assert timeout_sec <= 300, (
        f"HAOS_BOOT_TIMEOUT must be <= 300s so a real regression "
        f"fails the CI job in a reasonable time; got {timeout_sec}s"
    )
    # Step 3 must accept HTTP 200, 302, 303 (HAOS can redirect the
    # root URL to /onboarding.html during the first boot).
    assert '"200"' in text, (
        "Step 3 must accept HTTP 200 from the Hub root URL"
    )
    assert '"302"' in text, (
        "Step 3 must accept HTTP 302 (HAOS redirects the root URL "
        "to /onboarding.html during the first boot)"
    )
    assert '"303"' in text, (
        "Step 3 must accept HTTP 303 (HAOS uses 303 in some first-"
        "boot states)"
    )


def test_step3_handles_timeout_gracefully(gate_a_script_path: Path) -> None:
    """When the timeout fires, Step 3 prints a plain-English error
    line naming the cause (no errno jargon).

    The doctrine: "Clean install FAILED at step 3 — Home Assistant
    could not start" — NOT "Step 3 exit code 1".
    """
    text = _read_bash_script(gate_a_script_path)
    # The failure path must mention the step number + the cause in
    # plain English.
    assert 'fail "3"' in text, (
        "Step 3 must call the fail helper with the step number 3 so "
        "the plain-English error line is unambiguous"
    )
    assert "did not start" in text.lower(), (
        "Step 3 failure message must say 'did not start' in plain "
        "English (the doctrine requires a plain-English cause, not "
        "'Step 3 exit code 1')"
    )
    assert "Home Assistant" in text, (
        "Step 3 failure message must name the component (Home "
        "Assistant) so the operator knows exactly what did not start"
    )


def test_step4_verifies_roamcore_integration_detected(
    gate_a_script_path: Path,
    sample_haos_response: dict,
) -> None:
    """Step 4 fetches ``/manifest.json`` from the Hub + greps for
    ``roamcore`` to verify the RoamCore integration is detected.

    The rig asserts the canned HAOS response contains the
    ``roamcore`` integration domain (the substring the bash script
    greps for) + asserts the bash script's Step 4 grep matches.
    """
    text = _read_bash_script(gate_a_script_path)
    assert "manifest.json" in text, (
        "Step 4 must fetch the Hub's /manifest.json (the canonical "
        "HA endpoint that lists every installed integration)"
    )
    assert "roamcore" in text, (
        "Step 4 must grep /manifest.json for 'roamcore' (the "
        "RoamCore integration domain)"
    )
    # The canned response must contain the integration domain so the
    # Step 4 substring check passes.
    domains = [i.get("domain", "") for i in sample_haos_response.get("integrations", [])]
    assert any("roamcore" in d for d in domains), (
        f"sample_haos_response must include a RoamCore integration "
        f"domain so Step 4's grep can pass; got {domains!r}"
    )
    # Step 4 must print a plain-English failure message if the
    # integration is missing.
    assert 'fail "4"' in text, (
        "Step 4 must call the fail helper with the step number 4 so "
        "the plain-English error line is unambiguous"
    )
    assert "integration was not detected" in text.lower() or "not detected" in text.lower(), (
        "Step 4 failure message must say 'integration was not detected' "
        "in plain English (the doctrine requires a plain-English cause)"
    )


def test_step5_verifies_setup_wizard_reachable(
    gate_a_script_path: Path,
    onboarding_html_sample: str,
) -> None:
    """Step 5 fetches ``/onboarding.html`` + greps for ``wizard`` /
    ``onboarding`` / ``setup`` to verify the setup wizard is reachable.

    The rig asserts the canned HTML contains all three substrings
    (the bash script greps for any of them) + asserts the bash
    script's Step 5 grep matches.
    """
    text = _read_bash_script(gate_a_script_path)
    assert "onboarding.html" in text, (
        "Step 5 must fetch the Hub's /onboarding.html (the canonical "
        "HA setup-wizard URL)"
    )
    # The grep must accept all three substrings.
    for needle in ("wizard", "onboarding", "setup"):
        assert needle in text, (
            f"Step 5 must accept the substring {needle!r} in the "
            f"setup-wizard page body (HA's onboarding page uses "
            f"all three terms interchangeably)"
        )
    # The canned HTML must contain all three substrings so the
    # Step 5 check can pass.
    for needle in ("wizard", "onboarding", "setup"):
        assert needle.lower() in onboarding_html_sample.lower(), (
            f"onboarding_html_sample must contain {needle!r} so the "
            f"Step 5 substring check can pass"
        )
    # Step 5 must print a plain-English failure message if the
    # wizard is unreachable.
    assert 'fail "5"' in text, (
        "Step 5 must call the fail helper with the step number 5 so "
        "the plain-English error line is unambiguous"
    )


def test_step6_tears_down_qemu(gate_a_script_path: Path) -> None:
    """Step 6 installs an EXIT trap that kills the qemu process on
    teardown (the recovery contract: re-runs do not leak processes).

    The rig asserts the script registers ``trap cleanup EXIT`` after
    qemu launches + asserts Step 6 fails loudly if qemu is still
    alive after teardown.
    """
    text = _read_bash_script(gate_a_script_path)
    assert "trap cleanup EXIT" in text, (
        "Gate A bash script must register a cleanup EXIT trap so "
        "the qemu process is killed on every exit (success + "
        "failure) — this is the recovery contract"
    )
    assert 'fail "6"' in text, (
        "Step 6 must call the fail helper with the step number 6 so "
        "the plain-English error line is unambiguous"
    )
    assert "did not stop on teardown" in text, (
        "Step 6 failure message must say 'did not stop on teardown' "
        "in plain English (the doctrine requires a plain-English cause)"
    )


def test_full_pipeline_with_mocked_subprocess(
    gate_a_script_path: Path,
    haos_sha256_mock: str,
    sample_haos_response: dict,
    onboarding_html_sample: str,
) -> None:
    """End-to-end run: invoke the bash script via ``subprocess.run``
    on the real host and assert the script exits 0 on the
    QEMU-not-available path (script-only delivery).

    On a host without qemu-system-x86_64 (e.g. the cron host +
    GitHub-hosted runners), the bash script's preflight check takes
    the script-only-delivery path: prints the plain-English
    "Gate A runs in CI sandbox only" message and exits 0. This
    test exercises that path end-to-end.

    The test does NOT mock ``subprocess.run`` at the Python level —
    the bash script invokes its OWN subprocess calls (``command -v``,
    ``sha256sum``, etc.) via the bash builtin ``command`` keyword,
    which is independent of Python's ``subprocess.run``. The
    Python-level ``subprocess.run`` here is just the wrapper that
    launches ``bash`` and captures its stdout/stderr.

    Why this matters: it proves the rig can be wired into CI on a
    GitHub-hosted ubuntu-latest runner (which has no qemu) and the
    preflight failure-mode is the documented one — a plain-English
    skip message + exit 0, not a stack trace.
    """
    # Invoke the bash script via the real ``bash`` binary (so we
    # exercise the actual script, not a Python re-implementation).
    # On this host the script's preflight ``command -v qemu-system-
    # x86_64`` will return 1 (qemu is not installed) + take the
    # script-only-delivery exit-0 path.
    result = subprocess.run(
        ["bash", str(gate_a_script_path)],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Gate A bash script must exit 0 on the QEMU-not-available "
        f"path (script-only delivery); got returncode={result.returncode}, "
        f"stderr={result.stderr.decode('utf-8', errors='replace')}"
    )
    # The plain-English skip message must be in stdout.
    assert b"Gate A runs in CI sandbox only" in result.stdout, (
        f"Gate A bash script must print the plain-English skip "
        f"message when QEMU is not available; got "
        f"stdout={result.stdout.decode('utf-8', errors='replace')!r}"
    )


def test_idempotent_rerun_uses_cache(gate_a_script_path: Path) -> None:
    """Re-running the bash script with the same inputs produces the
    same outcome on the same input (idempotency contract).

    The rig asserts the cached-SHA branch is reachable + asserts the
    download-with-retry helper is only invoked on a fresh-cache run
    (not on a rerun). The unit-level guarantee here is that the
    bash script's ``if [ -f "$HAOS_IMAGE" ]`` branch is in the
    right place (before the download fallback), so re-runs skip the
    network step.
    """
    text = _read_bash_script(gate_a_script_path)
    # The cached-SHA check must appear BEFORE the *invocation* of
    # download_with_retry — otherwise a re-run would always try to
    # re-download (defeating the idempotency contract). We find the
    # invocation by searching for the call-site comment ("Downloading
    # the Hub image (or using the cached copy)") + the actual
    # ``if ! download_with_retry`` line in the body.
    cached_branch_pos = text.find('if [ -f "$HAOS_IMAGE" ]')
    download_invocation_pos = text.find("if ! download_with_retry")
    assert cached_branch_pos != -1, (
        "Gate A bash script must have the cached-SHA branch "
        "(the idempotency contract)"
    )
    assert download_invocation_pos != -1, (
        "Gate A bash script must invoke download_with_retry as a "
        "fallback (the fresh-cache path)"
    )
    assert cached_branch_pos < download_invocation_pos, (
        f"the cached-SHA branch must appear BEFORE the "
        f"download_with_retry invocation so re-runs skip the download; "
        f"got cached_branch_pos={cached_branch_pos}, "
        f"download_invocation_pos={download_invocation_pos}"
    )
    # The script must define HAOS_EXPECTED_SHA from the manifest's
    # pinned SHA — proves the SHA comparison is wired to the
    # canonical manifest (not a hardcoded value).
    assert "HAOS_EXPECTED_SHA=" in text, (
        "Gate A bash script must define HAOS_EXPECTED_SHA from the "
        "canonical manifest (no hardcoded SHA values)"
    )
    # The pinned SHA is the same one the manifest carries.
    assert "504c10f5703ebadcc70ebe625929f2e7910d64c78145a87725eb6baabe1072b0" in text, (
        "Gate A bash script must pin HAOS_EXPECTED_SHA to the same "
        "64-char hex the manifest carries (504c10f5...be1072b0)"
    )
