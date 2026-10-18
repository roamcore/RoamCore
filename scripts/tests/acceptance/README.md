# RoamCore — Acceptance tests (operator runbook)

This directory holds the automated acceptance tests for RoamCore. Each
test is a small, end-to-end script that proves a single release-gate
contract ("a fresh Hub boots", "the OpenClaw API is reachable", etc.)
without requiring you to set up the production Hub yourself.

This runbook is for operators: release engineers, CI maintainers, and
people who want to run Gate A (or any future gate) locally before
opening a pull request.

For the user-facing description of what these tests are, see
[`docs/runbooks/automated-acceptance-tests.md`](../../../../docs/runbooks/automated-acceptance-tests.md)
— that one is written for the vanlifer who just wants to know that
their update will not break the install.

## §1 What this is

There is one acceptance test per release gate. Today only Gate A
exists (clean install). Future slices will add Gate B (connection
flow), Gate C (dashboard reliability), Gate D (agent integration),
Gate E (remote access), and Gate F (recovery) — one file per gate,
following the same shape as the existing one.

Each gate has two halves:

- A **bash test** (`gate_<name>.sh`) — the canonical contract. Boots
  a real HAOS VM, verifies the contract, tears down. Lives on a
  Linux host with `qemu-system-x86_64` + the existing `ha-beta` smoke
  rig available. On any other host the bash test takes the
  "script-only delivery" path: it prints a plain-English "this gate
  runs in the CI sandbox only" message and exits 0.
- A **pytest rig** (`test_gate_<name>.py`) — fast, always-on
  coverage that runs on every push to main + on every PR + on the
  cron host. Mocks subprocess so it can verify the bash test
  contains the right step shape (the right flags, the right
  greps, the right plain-English failure messages) without needing
  qemu on every runner.

The fixture file `conftest.py` provides the four shared fixtures the
pytest rigs depend on (the bash script path, a mocked `subprocess.run`,
a canned HAOS response, a pinned SHA). The `__init__.py` marks the
directory as a Python package so pytest can collect the rigs under
the import path `scripts.tests.acceptance`.

## §2 What you see

When you run Gate A on a host without qemu:

```
$ bash scripts/tests/acceptance/gate_a_clean_install.sh
! QEMU not available — Gate A runs in CI sandbox only (this script is the contract; the pytest rig covers the same logic on this host)
  hint: install qemu-system-x86 + kvm-ok to run the real bash test locally
$ echo $?
0
```

When you run Gate A on a host with qemu (a real CI sandbox), the
script prints six plain-English step banners:

```
▶ Step 1 of 6 — Downloading the Hub image (or using the cached copy)
✓ Cached Hub image SHA matches the pinned SHA — skipping download
▶ Step 2 of 6 — Booting the Hub
✓ Hub booted (qemu pid 12345)
▶ Step 3 of 6 — Waiting for the Hub to respond (up to 120s)
✓ Hub responded with HTTP 200 after 87s
▶ Step 4 of 6 — Checking the RoamCore integration is detected
✓ RoamCore integration is detected
▶ Step 5 of 6 — Checking the setup wizard is reachable
✓ Setup wizard is reachable (HTTP 200)
▶ Step 6 of 6 — Tearing down the Hub
✓ Hub tore down cleanly
✓ Gate A clean install PASSED — every step finished without errors
```

When you run the pytest rig:

```
$ pytest scripts/tests/acceptance/test_gate_a_clean_install.py -v
...
collected 10 items
test_gate_a_clean_install.py::test_step1_downloads_haos_with_cached_fallback PASSED
test_gate_a_clean_install.py::test_step1_verifies_sha256                PASSED
test_gate_a_clean_install.py::test_step2_boots_haos_in_qemu             PASSED
test_gate_a_clean_install.py::test_step3_waits_for_http_200             PASSED
test_gate_a_clean_install.py::test_step3_handles_timeout_gracefully     PASSED
test_gate_a_clean_install.py::test_step4_verifies_roamcore_integration_detected PASSED
test_gate_a_clean_install.py::test_step5_verifies_setup_wizard_reachable PASSED
test_gate_a_clean_install.py::test_step6_tears_down_qemu                PASSED
test_gate_a_clean_install.py::test_full_pipeline_with_mocked_subprocess PASSED
test_gate_a_clean_install.py::test_idempotent_rerun_uses_cache          PASSED
10 passed in 0.10s
```

## §3 What you do

To run Gate A locally (no qemu needed — the rig handles that path):

```bash
pytest scripts/tests/acceptance/test_gate_a_clean_install.py -v
```

To run the bash test (with qemu present):

```bash
bash scripts/tests/acceptance/gate_a_clean_install.sh
```

To run the bash test + the rig in one go (mimics the GitHub Actions
job):

```bash
pytest scripts/tests/acceptance/test_gate_a_clean_install.py -v \
  && bash scripts/tests/acceptance/gate_a_clean_install.sh
```

The GitHub Actions workflow at
`.github/workflows/acceptance-gate-a.yml` runs the pytest rig on every
push to main + every PR + every manual dispatch. The bash test runs
in the same workflow only on hosts that set `HAS_HAOS_SANDBOX=true`
(self-hosted runners with the existing ha-beta rig).

## §4 What to do if it goes wrong

The rig is designed to fail loudly with plain-English messages. Each
step in the bash test calls a `fail "<step-number>" "<plain-English
reason>"` helper that prints the step number + the cause so a red
Gate A says exactly which step failed and why. The pytest rig's
failure messages name the assertion that flipped (e.g.
"Step 4 must call the fail helper with the step number 4") so the
diff between expected and actual is one line away.

If the bash test reports "Step N failed: ...":

1. Read the step number + the plain-English reason. That's the
   contract that flipped.
2. Open the corresponding section in `gate_a_clean_install.sh` and
   read the run + the assertion in that section. The assertion is
   the line that called `fail`.
3. Reproduce on a host with qemu + the ha-beta rig, then run the
   bash test in isolation:
   ```bash
   bash scripts/tests/acceptance/gate_a_clean_install.sh
   ```
4. If the bash test passes locally but fails in CI, the issue is the
   CI sandbox (qemu version, kernel module, network egress). Open
   an issue with the full `▶ Step N — ...` log attached.

If the pytest rig reports an `AssertionError`:

1. Read the assertion message — it names the bash-test contract
   element that flipped (e.g. "Step 3 must accept HTTP 302 from
   the Hub root URL").
2. Open `gate_a_clean_install.sh` and grep for the contract
   element. If the assertion is right and the bash test is wrong,
   fix the bash test. If the bash test is right and the assertion
   is wrong, fix the pytest rig (but check the rationale in the
   assertion docstring first — every assertion quotes the contract).

## §5 Useful links

- User-facing description of the acceptance tests:
  [`docs/runbooks/automated-acceptance-tests.md`](../../../../docs/runbooks/automated-acceptance-tests.md)
- GitHub Actions workflow for Gate A:
  [`.github/workflows/acceptance-gate-a.yml`](../../../workflows/acceptance-gate-a.yml)
- The bash test (the canonical contract):
  [`gate_a_clean_install.sh`](gate_a_clean_install.sh)
- The pytest rig (the fast, always-on coverage):
  [`test_gate_a_clean_install.py`](test_gate_a_clean_install.py)
- Shared fixtures: [`conftest.py`](conftest.py)
- Package marker: [`__init__.py`](__init__.py)
- The canonical Hub golden-image manifest (the SHA256 the bash
  test pins to):
  [`scripts/build/hub-golden-image.manifest.yml`](../../build/hub-golden-image.manifest.yml)
- The `ha-beta` smoke rig (the upstream qemu-based HAOS sandbox rig
  this gate is designed to run on):
  [`scripts/checks/ha-beta-smoke.sh`](../../checks/ha-beta-smoke.sh)
