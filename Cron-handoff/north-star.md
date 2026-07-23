# Caste → RoamCore North Star (cron handoff)

## Bernard (2026-06-16 20:11 UTC)

> "ok, please keep going with this [Caste Palantir UI redesign] as the main priority.
> Once you have finished with that, and you think its at an extremely high quality state,
> I want you to start chipping away at this document.
> Please use it as your next north star (STRICTLY AFTER THIS UI CORE PROBLEM IS SORTED OUT).
> Update whatever you need to, to get these built using the same cron recursive loop that you were using before."

## Phase 1 (CURRENT): Caste Palantir UI redesign
- All 5 role consoles + 4 nav pages migrated to the new design language
- 6 crons resumed and retargeted at the Caste UI mission (see /home/bernard/.openclaw/workspace/MEMORY.md and the cron descriptions)
- "Extremely high quality state" = the Palantir bar: every surface uses the workspace component pattern, no legacy caste-* chrome in new code, every action lands in the audit log, every page passes npm run check, design language is consistent

## Phase 2 (NEXT, after the Caste UI bar is met): RoamCore north-star build

Bernard attached two PDFs to the master session — preserved in /home/bernard/.openclaw/workspace/memory/roamcore-north-star/:

1. **roamcore-prd-and-overview.pdf** (8 pages) — full PRD. Vision: "modular hardware and software platform designed to monitor, control, and automate all essential systems in a self-sufficient van conversion or off-grid living space." Initial focus: campervans. Adaptable: boats, tiny houses, cabins, trailers, overlanding rigs, expedition vehicles, mobile workstations, surveillance vehicles. Core product statement: "RoamCore MVP is a hardened van networking + automation hub that unifies connectivity, Victron power integration, and a novice-first dashboard — while remaining fully open to advanced users."

2. **roamcore-beta-hub-mvp.pdf** (2 pages) — concrete MVP requirements:
   - OpenWrt/Networking: LAN/WAN (LTE SIM, Starlink, failover), local API, router/gateway/switch role comparable to Teltonika/Maxview
   - Home Assistant Dashboard: Power (Victron pairing), Networking (OpenWrt API controls), Van Level (IMU), Map (trip history), Weather/Time (SmartyVan)
   - Proxmox setup: networking bridges, VM/RoamCore architecture

## When to switch the crons

The crons should switch to RoamCore when **all** of the following are true:
- Every Caste role console + nav surface uses the new design language (no legacy caste-* chrome in active code)
- /clarifications, /audit, /issues, /payments, /shipments (or equivalent surfaces) exist with real data plumbing
- The 30-min intensive build loop has shipped 3 consecutive runs with no new high-leverage UI slices (i.e. the Caste UI is feature-complete and stable)
- npm run check is green on the latest commit

When that state is reached, the parent agent will:
1. Update the cron prompts to read /home/bernard/.openclaw/workspace/memory/roamcore-north-star/roamcore-prd-and-overview.pdf
2. Update the cron prompts to focus on RoamCore's beta-hub MVP (OpenWrt networking + HA dashboard tiles)
3. Re-enable any RoamCore-specific crons (bernard already has skills `roamcore-root-operator`, `roamcore-git-fast-mode`, `roamcore-github-discipline`, etc. ready to use)
4. Resume Phase 1 work on RoamCore (OpenWrt VM, HA dashboard tiles, Victron pairing, etc.)

## Repo boundary

- Caste: /home/bernard/clawd/caste → bernardc6/caste (current)
- RoamCore: /home/bernard/clawd/RoamCore → roamcore/RoamCore (next, after Phase 1)
- Caste crons must NOT touch RoamCore files (and vice versa)

## Phased deliverable ladder for RoamCore (read the full PDFs for detail)

1. **Networking** (Phase 2a): OpenWrt VM with LTE/Starlink/failover; comparable to Teltonika/Maxview; clean SSID/secrets management; Tailscale remote access; mission-critical reliability
2. **HA dashboard** (Phase 2b): Power (Victron pairing), Networking, Van Level (IMU), Map (trips), Weather/Time; novice-first; fail-softly; tile-based grid; dark/light
3. **Support infrastructure** (Phase 2c, later): Supabase Auth + Postgres + Edge Functions; device registry; remote access relay; OTA signed artifacts; fleet health telemetry
4. **Premium features** (Phase 3+): Map page trip wrapping, Pro subscription, advanced mode (Heimdall), custom dashboard sections, AI chat (LLM as translation layer only)

The crons will build phase 2a first, then 2b, then 2c, then 3.

---
This file lives at /home/bernard/clawd/RoamCore/Cron-handoff/north-star.md and is the cron-readable handoff for the Phase 1 → Phase 2 transition.
