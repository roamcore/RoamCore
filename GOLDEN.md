# RoamCore — GOLDEN.md

**Project constitution. Read this before any non-trivial work.**

## What RoamCore is

A novice-first van/RV telemetry dashboard with mission-critical networking, LTE/Starlink failover, Victron integration, Trip Wrapped shareables, and an OpenClaw agent bridge.

**One sentence:** A van owner should be able to glance at a single dashboard and know whether everything is fine, and an OpenClaw agent should be able to answer "is the van OK?" using the same data.

## Product principles

1. **Novice-first UX** — Apple-grade onboarding. Power users get an "Advanced mode." Fail-softly UI everywhere.
2. **Mission-critical connectivity** — LTE primary, Starlink failover, Tailscale-like remote access. Network failures must not lose data or lock the user out.
3. **Victron-centric power MVP** — auto-discovery + capability-driven tiles. Don't hand-configure.
4. **Trip Wrapped as core USP** — shareable maps + summaries. The thing people tell their friends about.
5. **AI as trust-first summary/translation layer** — agentic control comes later, not first.
6. **OpenClaw as a first-class citizen** — every visible data point is also readable from OpenClaw. "Chat with the van."

## Engineering principles

1. **Customer-facing repo** — RoamCore GitHub is what the world sees. Internal engineering logs, sensitive infra details, and unfiltered agent run transcripts stay local (`memory/roamcore/`).
2. **Documentation-driven** — MkDocs site is the public surface. `docs/` is the source of truth for users. Runbooks/scripts are sanitised.
3. **Backup + rollback discipline** — anything that touches Proxmox, HA, OpenWrt, or networking requires a snapshot + HA full backup + git commit *before* the change. See `Cron-handoff/roamcore-backup-rollback` skill.
4. **Git fast mode** — direct-to-main pushes are fine for RoamCore. No PRs. No force-pushes. Tag known-good states.
5. **Safety rule: do not touch `vmbr0`** — Bernard's bridge is immutable unless explicitly overridden. Treat as off-limits.
6. **HACS-friendly layout** — must install as one-line command or HACS custom repo.
7. **Naming follows `rc-entity-naming.md`** — Home Assistant entities use the canonical convention. Reference the doc, don't hardcode.

## Active mission (as of 2026-06-19)

Phase 3 of the cross-project cron mission — paused until Caste Phase 1 + 2 are done. Cron handoff doc at `Cron-handoff/north-star.md`. Build order: OpenWrt networking (3a) → HA dashboard (3b) → support infra (3c).

## Architecture invariants

- **MkDocs site** in `site-home/` and `docs/`. Built and deployed as the public site.
- **Home Assistant custom integration** in `homeassistant/` with `hacs.json`. Standard layout.
- **OpenWrt VM** on the Proxmox host (VP2430, 192.168.1.10). VMID 100. Dev mgmt IP 192.168.1.250.
- **Proxmox host** is `roamcore-proxmox` SSH alias. Root access via `~/.ssh/vancore_clawdbot`.
- **MUST NOT TOUCH `vmbr0`** — immutable.
- **HA token** stored at `~/.clawdbot/secrets/homeassistant.token` (mode 600). Never committed.

## What success looks like

A new user can:
1. Find the GitHub repo.
2. Install via one-line command or HACS custom repo.
3. See a pre-configured dashboard on first run.
4. Run the setup wizard that connects Victron, OpenClaw, networking.
5. Glance at the dashboard and immediately understand van state.
6. Connect OpenClaw and chat with the van.
7. Share a Trip Wrapped after a trip.

See `memory/roamcore-beta-user-flow.md` for the canonical user journey.

## Anti-patterns

- ❌ Hand-configuring Victron instead of using capability discovery
- ❌ Touching `vmbr0` without explicit Bernard override
- ❌ Committing secrets or HA tokens to the repo
- ❌ Adding "advanced" features before the novice path is solid
- ❌ Wide PRs that mix networking + UI + infra changes
- ❌ Pulling Caste/manufacturing context into RoamCore work
- ❌ Putting internal engineering logs on the public GitHub
