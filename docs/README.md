# Documentation structure

This repository is intended to become **customer-facing**.

## Principles

- `docs/` should trend toward **user/customer documentation** (setup guides, concepts, troubleshooting).
- Avoid infrastructure-sensitive detail in customer docs (IPs, internal hostnames, credentials, backup vault specifics).
- Internal engineering notes and day-to-day development logs live **outside GitHub** in Clawdbot’s local memory.

## Where internal notes live

Clawdbot maintains private, local memory files on the Clawdbot host:

- `memory/YYYY-MM-DD.md` — development log (raw)
- `MEMORY.md` — curated long-term decisions and preferences

These are not committed to GitHub.

## Current state

Some existing documents under:
- `docs/runbook/`
- `docs/architecture/`

are **engineering/internal** and will be moved/rewritten into customer-safe docs over time.
