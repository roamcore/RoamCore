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
- [x] Trip tracking: fully local/private end-to-end by default (slice #20 — see commit)

  _Privacy contract._ Trip data stays on-device by default. The trip pipeline (`homeassistant/tools/trip_wrapped/`, `roamcore_trip_local.yaml`, `roamcore_trip_wrapped.yaml`, `roamcore_location.yaml`) refuses any outbound HTTP call unless the target is loopback (`127.0.0.0/8`, `::1`) or the local add-on CIDR (`192.168.1.0/24`, `10.0.0.0/8`). Operators can explicitly opt in to non-local hosts by turning `input_boolean.rc_trip_local_only` OFF and listing hostnames in `input_text.rc_trip_opt_in_domains` (or annotating the source with `# PRIVACY-OPTIN:`). Defaults point at the local tileserver add-on; the smoke check (`scripts/checks/trip-tracking-privacy-smoke.sh`) fails on any unannotated external host.
- [x] RoamCore Wrapped: fully seamless USP flow (no setup friction)
  _Slice #21: Map → Trip Wrapped shows a fully-rendered demo report with one tap on a brand-new install. See `scripts/checks/trip-wrapped-seamless-smoke.sh` and `homeassistant/tools/trip_wrapped/demo_seed.py` (stdlib-only, local-tileserver map URL). The "use my real trips" CTA appears once `input_boolean.rc_trip_wrapped_real` is ON._
- [x] Amenities overlay (API-based, toggleable; e.g. iOverlander)
  _Slice #22: optional, opt-in amenities overlay (`input_boolean.rc_amenities_overlay_enabled`, default OFF). Reads `/local/roamcore/amenities/latest.json` produced by `homeassistant/tools/amenities/overpass_query.py` (stdlib-only, Overpass-based; default endpoint annotated `# PRIVACY-OPTIN:`). Smoke checks: `scripts/checks/amenities-overlay-smoke.sh` + `scripts/checks/amenities-overlay-privacy-smoke.sh` (both wired into `scripts/check.sh --core-only`). See the catalog page `docs/catalog/map/amenities-overlay.md`._

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

- [ ] Networking controls (VP2430 specific) via OpenWrt API
- [ ] Remote access
- [ ] OTA updates (GitHub-based channel, rollback-aware)
- [ ] Additional hardware support (OBD, lighting, etc)
- [ ] Hardware auto-discovery + setup flows

---

## Community

- [ ] RoamCore Labs (share setups/dashboards)
- [ ] Gamification / competitions (optional)

