# RoamCore Warden — standing-rule cron

**Bernard (2026-07-28 ~21:10 UTC):** "the repo must always work, and in the
event that it doesn't, you should be kicked into action straight away and
not stop until it is solved."

This cron is the enforcement mechanism for that standing rule.

## What it does

Runs `bash scripts/check.sh --quick` from `/home/bernard/clawd/RoamCore`.
This checks every layer of the core:

- Python imports (5 custom components)
- JSON parse (all `.json` in repo)
- YAML parse (with HA's `!include` permissive loader)
- Shell syntax (install scripts)
- Connections audit (when `connections/_schema/` exists)
- Connections unit tests
- MkDocs strict build (auto-installs mkdocs if missing)

Exits 0 = green (repo working). Exits 1 = at least one check failed.

## Schedule

`every 6h` — runs 4× per day. Combined with the on-push-to-main check
workflow + the per-PR check workflow, this gives 3 layers of guard:

| Layer | Cadence | What it catches |
|-------|---------|-----------------|
| Pre-commit (developer) | On `git commit` | Local lint (if configured) |
| Per-PR / per-push | Every PR + push to main | Anything bad that lands |
| Warden cron | Every 6h | Drift between cron cycles (e.g. cron drift, secret leak, runtime regression) |

## Failure protocol — "kicked into action straight away"

When `check.sh` exits non-zero:

1. **Immediate:** the warden cron surfaces the failure to Bernard via
   Telegram with a one-line summary + the failing check names + the
   last 30 lines of the log tail.
2. **First action:** the parent agent spawns a focused sub-agent with
   task="fix the failing check X" + write-scope=the affected files +
   verification="re-run check.sh, must be green".
3. **No stop until green:** the sub-agent does not stop, sleep, or
   yield until `check.sh` exits 0. If the fix is non-trivial (e.g. a
   Python API change requires updating multiple components), the
   sub-agent iterates through them all.
4. **Escalation:** if the fix requires user input (e.g. design
   decision, secret rotation, third-party API change), the sub-agent
   surfaces a single blocking question to Bernard. Do not proceed
   with speculation.
5. **Post-fix:** commit + push + announce. Update this cron brief
   with the resolution note.

## What "stop until it is solved" means in practice

- No pivoting to new work until the check is green.
- No cron cycles that don't end with a green check.
- No "I'll fix it later" — later is now.
- No silent reverts to make the check pass — that hides the bug.

## How to bypass a check (NEVER without Bernard sign-off)

A failing check is a real problem. If a check is genuinely wrong
(false positive that fails the build on legitimate code), the right
move is:

1. Surface the false positive to Bernard with a clear example.
2. Get Bernard's sign-off in writing (in this brief, in commit body,
   or on Telegram).
3. Fix the check script (e.g. tighten the regex, add a documented
   exception) and commit that fix.

**Never** edit `check.sh` to skip a check that was catching real
problems. The check is the source of truth for "the repo works."

## What the warden cron does NOT do

- Does not edit code. It only runs check.sh and reports.
- Does not commit. That's the fix-sub-agent's job.
- Does not make design decisions. If a fix requires user input, it
  surfaces a question.
- Does not start new work. It only protects the existing state.

## Cron definition (illustrative — paste into the scheduler)

```yaml
name: roamcore-warden
schedule:
  kind: every
  everyMs: 21600000  # 6 hours
sessionTarget: isolated
payload:
  kind: agentTurn
  message: |
    PROJECT: RoamCore.

    You are the RoamCore warden. Your single job is to enforce the
    standing rule: the repo must always work.

    Steps:
    1. cd /home/bernard/clawd/RoamCore
    2. bash scripts/check.sh --quick
    3. If exit 0: report "warden green at $(date -u +%FT%TZ)".
       Stop.
    4. If exit 1: read the failure log carefully. Spawn a fix sub-agent
       with task="fix check.sh failure" + write-scope=affected files +
       verification="re-run check.sh, must be green". Do not stop
       spawning sub-agents until check.sh is green. Surface any
       blocking questions to Bernard via message tool.
    5. After fix lands: commit + push. Re-run check.sh to confirm
       green. Report the fix to Bernard.

    Read /home/bernard/clawd/RoamCore/Cron-handoff/roamcore-warden.md
    for full protocol.
```

## Operational history

- **2026-07-28 ~21:10 UTC** — Initial brief written. Repo green on
  Day 0 audit (5 PASS / 0 FAIL / 3 SKIP / 1 FINDING). PR #6 open.
