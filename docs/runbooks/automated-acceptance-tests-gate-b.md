# RoamCore — Automated Acceptance Tests for Gate B (connection flow)

## §1 What this is

An automated test that simulates a fresh device being plugged into
your van and walks it through every step RoamCore should handle
automatically — finding the device, recognising what it is, mapping
it to a tile on your dashboard, and confirming it still works after
the system restarts.

## §2 What you see

When RoamCore is healthy, you see a green check mark called
"Acceptance — Gate B (connection flow)" in the GitHub Actions tab.
When something is wrong, that check is red and you can click into
the failed run to see exactly which step broke.

There are 15 steps in this test, and each one prints a short
plain-English message when it runs. If a step fails, the message
tells you what went wrong in words a normal person can understand
("the dashboard tile did not appear within 30 seconds, check that
the capability mapping layer is loaded") instead of showing you a
wall of code.

## §3 What you do

1. Push your change to the `main` branch (or open a pull request).
2. Open the **Actions** tab at the top of the GitHub repository.
3. Click on the run called "Acceptance — Gate B (connection flow)".
4. If the run is green, you are done. If the run is red, click
   into the failed step to see which one broke and what it says.

## §4 What to do if it goes wrong

When the test fails, the failed step's plain-English message tells
you what is wrong and what to check first. The most common
reasons a step fails are:

- **The discovery layer cannot find the device.** This usually means
  a wiring change in the upstream integration broke the
  auto-detection. Check that the integration's manifest is
  reachable.
- **The capability mapper mapped the device to the wrong thing.**
  This means a rule in `connections/_schema/mapping_rules.json`
  no longer matches the device. Open the rule and the device's
  capability advertisement side by side and confirm the match.
- **The dashboard tile did not appear.** This usually means the
  dashboard generator is not listening for the
  capability-mapping event. Open the generator and confirm it
  reacts to new mappings.
- **The tile disappeared after the restart.** This means the
  integration is not persisting its state through the recorder.
  Check that the integration's recorder flags include the tile.

If the plain-English message does not help, scroll down in the
run log to find the pytest report — every assertion in the test
quotes the specific contract element it was checking.

## §5 Useful links

- The full Phase 7 directive (all 6 release gates):
  `memory/roamcore/2026-08-03-directive.md` — section "6 release
  gates", Gate B.
- The Gate A acceptance test (clean install), which ships the
  foundation + the pytest rig pattern this gate reuses:
  `docs/runbooks/automated-acceptance-tests.md`.
- The bash test (the canonical contract) lives at
  `scripts/tests/acceptance/gate_b_connection_flow.sh`.
- The pytest rig (the fast, always-on coverage) lives at
  `scripts/tests/acceptance/test_gate_b_connection_flow.py`.
- The GitHub Actions workflow lives at
  `.github/workflows/acceptance-gate-b.yml`.
