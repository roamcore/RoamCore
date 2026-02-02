# GitHub Discipline (VanCore)

This document defines how GitHub is used in the VanCore project.

## Purpose

GitHub is the **single source of truth** for:
- VanCore software stack
- System configuration
- Documentation and operational knowledge

All meaningful work performed by Clawdbot **must result in GitHub changes**, unless explicitly stated otherwise.

## GitHub’s roles

1. **System Memory** — what was done, why, and how to undo it
2. **Documentation Hub** — future support, scaling, and commercialisation
3. **Change Log** — precise record of system evolution
4. **Recovery Anchor** — restore a known-good state

Speed is prioritised over ceremony. Clarity is prioritised over perfection.

## Branching model (intentionally simple)

- Push directly to `main`
- No feature branches
- No pull requests
- No rebasing / history rewriting
- No force pushes

## Commit philosophy

Every commit must answer:
1) What changed?
2) Why was it changed?
3) How can it be rolled back or verified?

### Commit frequency

- Commit early and often
- Prefer many small commits over large ones
- Commit whenever:
  - a config file changes
  - a script is added or modified
  - documentation is updated
  - a system state meaningfully changes

### Commit message format (strict)

```
<short summary>

Context:
- Why this change was needed
- What problem it solves
- Any assumptions made

Changes:
- Bullet list of concrete changes

Verification:
- How to confirm this works
- Commands, URLs, or checks used

Rollback:
- How to undo or revert
- Snapshot / backup reference if applicable
```

## Mandatory documentation rules

### No “silent changes”

If Clawdbot:
- modifies HA config
- touches Proxmox / VM behaviour
- changes networking assumptions
- adds automation or scripts

Then docs must be updated in the same commit or the immediately next commit.

### Documentation is not optional

If a change is complex enough to exist, it is complex enough to document.

## Decision logging

Non-trivial architectural/product decisions must be logged to:

`docs/decisions/YYYY-MM-DD-short-title.md`

Template:

```
# Decision: <Title>

Date: YYYY-MM-DD

Context:
- What decision was required
- Constraints and goals

Decision:
- What was chosen

Rationale:
- Why this option was selected
- Tradeoffs accepted

Alternatives Considered:
- Brief list of rejected options

Impact:
- What this affects downstream
```

## Golden image discipline

Before risky changes:
- Proxmox snapshot
- Home Assistant full backup

After stabilising:
- Update `docs/runbook/golden-image.md`
- Tag the commit (e.g. `golden-ha-v0.1`)

## Never do

- Force push to `main`
- Rewrite history
- Commit secrets/credentials
- Leave the system in an undocumented state
