# RoamCore — Feature Checklist

One page. One list.

This is the simplest view of:
- what RoamCore already does today, and
- what we’re building next.

Legend:
- [x] = exists (shipping in repo)
- [ ] = planned / in progress

---

## Core (HA-only beta)

- [x] One-line installer + uninstaller (`install.sh` / `uninstall.sh`)
- [x] RoamCore custom dashboard (JS cards)
- [x] Native YAML dashboard option (easy to edit)
- [x] OpenClaw JSON API endpoints (`/api/roamcore/openclaw/summary` + `/api/roamcore/openclaw/skill`)

---

## Map / Trip

- [x] Map page (reliable raster fallback)
- [x] Trip Wrapped export (HTML + JSON output)
- [x] Trip Wrapped “first-run” degraded mode (generates output + shows setup notice if Traccar not configured)
- [ ] Trip tracking: fully local/private end-to-end by default
- [ ] RoamCore Wrapped: fully seamless USP flow (no setup friction)
- [ ] Amenities overlay (API-based, toggleable; e.g. iOverlander)

---

## Power (Victron)

- [x] Victron backend health entities (`rc_system_power_backend_*`)
- [x] Victron connect UI card (discover/connect)
- [ ] Victron pairing wizard (polished, foolproof)
- [ ] Auto-discovery of Victron GX on LAN + prompt “enable MQTT over LAN”
- [ ] Capability-driven power page (auto layout, hides missing tiles)

---

## Weather / Time

- [ ] Weather primitives that are reliable for automations
- [ ] Time + timezone sync that’s reliable for automations

---

## Automations

- [ ] Mode / automation builder (simple UI)
- [ ] Automations builder via text/LLM/MCP (OpenClaw API v2)

---

## System UX

- [ ] Advanced mode (clearly separated + safe recovery)
- [ ] Deterministic system summary (boring, consistent, trustworthy)
- [ ] AI chat (opt-in; API/Auth based)

---

## Platform

- [x] Networking controls (VP2430 specific) via OpenWrt API — slice #28 (Controls tab + Restart confirmation; see `docs/catalog/networking/openwrt-controls.md` + `homeassistant/packages/roamcore_openwrt_api.yaml`)
- [ ] Remote access
- [ ] OTA updates (GitHub-based channel, rollback-aware)
- [ ] Additional hardware support (OBD, lighting, etc)
- [ ] Hardware auto-discovery + setup flows

---

## Community

- [ ] RoamCore Labs (share setups/dashboards)
- [ ] Gamification / competitions (optional)

