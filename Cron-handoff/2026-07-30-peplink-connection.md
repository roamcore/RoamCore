# Wave 3 #40 — Connection: Peplink (tier-b) slice handoff

## Context

Promote the legacy tier-c `docs/catalog/networking/peplink.md` spec
into a tier-b recipe connection at `connections/peplink/`. Follows
the same pattern proven by Wave 3 #35 Frigate / #36 Starlink / #37
DNS blocker / #38 NAS / #39 Teltonika. Peplink is the multi-WAN glue
of RoamCore for vans — sits between Teltonika (single cellular WAN)
and Starlink (long-range WAN) — and the recipe documents both the
single-router HA-core-SNMP path (Path A) and the fleet-operator
Peplink-InControl-2-via-HACS-`hass-incontrol2` path (Path B).

This slice does NOT edit `connections/teltonika/` (the parent branch
territory), nor any other connection folder, nor the build-status
Teltonika row. Only the Peplink files + the
`scripts/check.sh` wire-up + the legacy-doc supersession banner +
the new build-status row for Wave 3 #40.

## Changes

- **New** `connections/peplink/connection.yml` (tier-b manifest; 11
  contract tiles + 8 OpenClaw queries + 6 OpenClaw summary keys +
  4 tier_warnings honesty markers; mirrors Teltonika manifest
  shape verbatim with Peplink-specific substitutions).
- **New** `connections/peplink/__init__.py` (DOMAIN marker stub;
  mirrors Teltonika `__init__.py` shape with Peplink-specific
  docstring describing both paths).
- **New** `connections/peplink/README.md` (folder overview; mirrors
  Teltonika README shape with Peplink-specific setup recipe +
  cross-references to Teltonika + Starlink + MQTT siblings).
- **New** `connections/peplink/docs/recipe.md` (~870-line howto;
  required sections §1 "What is Peplink in RoamCore?" / §2
  Prerequisites / §3 Path A — HA core SNMP / §4 Path B — InControl
  2 REST API / §5 RoamCore contract entities / §6 Automations /
  §7 Troubleshooting (8 entries) / §8 Privacy / §9 Promoting to
  tier-a).
- **New** `connections/peplink/tests/test_connection_yml.py` (7
  manifest-honesty tests: id matches folder / tier-b without tier-a
  markers / docs recipe published / category matches legacy doc /
  dashboard tiles follow rc naming / status reflects no real
  peplink / agent failover action is allowlisted).
- **Modify** `scripts/check.sh` — append a `run_if_present` entry
  for `connections/peplink/tests/test_connection_yml.py` directly
  after the existing Teltonika entry (alphabetical-ish ordering:
  dns-blocker → frigate → mqtt → nas → starlink → teltonika →
  peplink).
- **Modify** `docs/catalog/networking/peplink.md` — add a
  supersession banner at the top pointing at the new connection
  folder (matches the Wave 3 #39 Teltonika supersession banner
  shape; legacy content below the banner is preserved for
  historical context).
- **Modify** `docs/mvp/features-build-status.md` — add a "Shipped
  (repo)" row for Wave 3 #40 mirroring the recent Wave 3
  connection-row shape (manifest + recipe size + manifest-honesty
  smoke + contract entities + supersession banner + PR link
  placeholder `PR #N`).
- **New** `Cron-handoff/2026-07-30-peplink-connection.md` (this
  file — slice summary with Context / Changes / Verification /
  Rollback).

## Verification

Run locally before pushing:

```bash
cd /home/bernard/clawd/RoamCore
git status                                    # clean or only the new files
python3 -m pytest connections/peplink/tests/test_connection_yml.py -v
                                               # expect 7/7 PASS
bash scripts/check.sh --core-only              # expect "✓ all requested smoke checks passed."
git log --oneline -3                          # confirm new commit on feat/connections/peplink
git push -u origin feat/connections/peplink   # push
gh pr create --base main --head feat/connections/peplink \
  --title "Wave 3 #40: Connection: Peplink (tier-b) — multi-WAN router for vans" \
  --body "<commit body>"                        # open PR
gh pr list --state open --head feat/connections/peplink
                                               # confirm one PR exists
```

## Rollback

If something goes wrong post-merge:

1. Revert the merge commit on `main` (`git revert -m 1 <merge-sha>`).
2. The legacy `docs/catalog/networking/peplink.md` already carries a
   supersession banner pointing at `connections/peplink/`, so even
   post-revert operators have a pointer to the previous tier-c
   spec.
3. Delete the `feat/connections/peplink` branch
   (`git branch -d feat/connections/peplink` + `git push origin
   --delete feat/connections/peplink`) once the PR is closed.
4. If the smoke check itself needs to be removed pre-merge, drop
   the `run_if_present "connections/peplink/tests/..."` line from
   `scripts/check.sh` — the connection folder can exist without
   the wire-up until tier-a promotion lands.

## Notes for next slice

- The Peplink recipe references the Teltonika + Starlink connection
  folders as "companion multi-WAN slices" — keep the cross-refs
  intact as those slices evolve.
- The recipe's `rest_command.peplink_force_failover` and
  `rest_command.peplink_set_wan_priority` blocks (Path A) plus the
  InControl 2 equivalents (Path B) are documented in §A.5 / §B.5 —
  operators wire those manually until tier-a promotion lands.
- The §5.1 mode-aware automation is mode-aware (prefers cellular
  in Travel/Boost, Starlink in Home/Shore) and respects Stealth —
  same pattern as Teltonika's §5.3 suppress-reboot-in-Stealth.