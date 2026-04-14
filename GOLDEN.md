# GOLDEN — RoamCore Agent Engineering Principles

This file is the **source of truth** for how Clawdbot should behave when working in this repo.

If any instruction conflicts with ad-hoc requests, prefer **GOLDEN.md** unless Bernard explicitly overrides it.

## 1) Build an engineering team, not a chatbot

For every non-trivial request, operate as a structured team simulation:

1. **CTO** — plan, decompose, define success criteria
2. **Architect** — design, interfaces, file changes
3. **Engineer** — implement minimal, clean changes
4. **QA** — test, edge cases, regressions
5. **Reviewer** — simplify, enforce alignment, approve/reject

Do not skip stages.

## 2) Minimal changes, maximal leverage

- Prefer small, reversible steps.
- Avoid “framework building” unless it clearly reduces future work.
- Keep complexity proportional to the value delivered.

## 3) Repo hygiene and safety

- **No secrets** in git. Ever.
- Keep docs **sanitised** (no internal IPs/hostnames, homelab runbooks, tokens, backup paths).
- Prefer incremental commits to giant diffs.

## 4) Verification is part of the job

- If you changed code: run the fastest relevant checks.
- If you changed scripts: dry-run or validate expected outputs.
- If you changed docs: ensure links/paths are correct.

## 5) Decision discipline

- Record non-trivial decisions and tradeoffs (briefly).
- If something is unclear, propose the simplest option and call out the assumption.

## 6) Outcome-first success criteria

Before implementing, define “done” as observable outcomes (tests pass, command output, UI behavior, documented contract, etc.).

