# RoamCore — Automated Acceptance Tests

## §1 What this is

RoamCore runs an automated test every time someone pushes code to
make sure the dashboard still works the way you expect it to. Each
test simulates a real thing happening with your van — a fresh
install, plugging in a new device, loading the dashboard from your
phone while you are away — and confirms the system handles it the
way it should.

## §2 What you see

When RoamCore is healthy, you see a green check mark for each gate
in the GitHub Actions tab. When something is wrong, that check is
red and you can click into the failed run to see exactly which step
broke.

Each gate has its own short, plain-English message that runs when
the test starts. If a step fails, the message tells you what went
wrong in words a normal person can understand — never a wall of
code, never a jargon-only error.

## §3 What you do

1. Push your change to the `main` branch (or open a pull request).
2. Open the **Actions** tab at the top of the GitHub repository.
3. Click on the run for the gate that broke to see the plain-
   English error.
4. If the run is green for every gate, you are done.

## §4 What to do if it goes wrong

When a test fails, the failed step's plain-English message tells
you what is wrong and what to check first. If the message does not
help, scroll down in the run log to find the step-by-step output —
every step in every test quotes the specific contract element it
was checking.

If a gate stays red across multiple runs, the issue is probably a
regression in the slice that owns that gate. Each gate has its own
runbook with the full step-by-step recovery guide.

## §5 Useful links

- The full Phase 7 directive (all 6 release gates):
  `memory/roamcore/2026-08-03-directive.md` — section "6 release
  gates".
- The individual gate runbooks, one per release gate:
  - **Gate E — remote access**: see the runbook that ships with
    this gate.

---

**Operator → vanlifer translation**

| If you see this in the test log | It means this for you |
| -------------------------------- | --------------------- |
| "Acceptance gate"                | "an automated check that the system works" |
| "workflow_dispatch"              | "running the test on demand" |
| "GitHub Actions"                 | "the place on GitHub where the test results live" |

---

### Gate E — remote access

This gate proves you can reach your dashboard from your phone when
you are away from your van, and that your local WiFi connection
keeps working even if the remote one drops — so you never lose
access to your van. The full vanlifer-facing guide is in the
runbook that ships with this gate.