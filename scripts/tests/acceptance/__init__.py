# RoamCore — Acceptance tests package marker.
#
# Wave 9 #123.d.i — Phase 7 — Acceptance tests foundation + Gate A.
#
# This file marks ``scripts/tests/acceptance/`` as a Python package so
# pytest can collect the Gate A test rig under the import path
# ``scripts.tests.acceptance``. It is intentionally empty (no module
# docstring; no imports; no constants) — the conftest.py at the same
# level carries the fixtures the rig depends on, and
# test_gate_a_clean_install.py carries the test cases.
#
# The directory itself lives in ``scripts/`` (operator-facing
# developer plumbing) and not in ``tests/`` because the Gate A bash
# script + the pytest rig are best understood as a single acceptance
# test surface that ships with the repository, not as part of any
# individual integration's pytest bench.
