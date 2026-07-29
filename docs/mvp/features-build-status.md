# RoamCore MVP — Features Build Status

Last updated: 2026-07-29

This is an internal status page for the remaining MVP feature build-out.

## Shipped (repo)

- Weather + time contract sensors
  - `homeassistant/packages/roamcore_weather_time.yaml`

- Timezone override contract sensor (no HA restart required)
  - `sensor.rc_time_zone` via `input_text.rc_time_zone_override`

- Levelling contract (HA-only beta)
  - `homeassistant/packages/roamcore_level.yaml`
  - auto-maps common ESPHome pitch/roll sensors into stable `rc_level_*` entities

- Map view wiring
  - `dashboard/lovelace/storage/lovelace.roamcore.json` includes `/lovelace/roamcore/map`
  - `homeassistant/packages/roamcore_location.yaml` maps a configurable `device_tracker` → `rc_location_*`

- Trip Wrapped (MVP HTML export)
  - tool: `homeassistant/tools/trip_wrapped/`
  - HA wiring: `homeassistant/packages/roamcore_trip_wrapped.yaml`
  - output: `/local/roamcore/trip_wrapped/latest.html`

- OpenClaw JSON API (HA-native)
  - endpoint: `/api/roamcore/openclaw/summary`
  - docs: `docs/reference/openclaw-json-api.md`

- Traccar live map (embedded)
  - RoamCore Map page embeds Traccar add-on **web UI** via iframe (configurable).
  - Helper: `input_text.rc_traccar_ui_url`

- HACS packaging (Wave 2 #19)
  - `hacs.json` (repo root) declares the repo as a HACS custom-repo with
    `content_in_root: false`, `country: "ALL"`, and
    `domains: ["roamcore", "roamcore_tileserver", "roamcore_traccar_proxy"]`
    — all three RoamCore integrations are HACS-discoverable from one repo.
  - `homeassistant/custom_components/roamcore/info.md` — HACS-published
    integration metadata (title, description, install prerequisites,
    usage, support links, MIT license). This is what HACS shows users
    before they install.
  - `homeassistant/custom_components/roamcore/branding/icon.png` and
    `branding/logo.png` — brand-agnostic 512×512 placeholders (deep
    navy + warm amber; simple `RC` / `ROAMCORE` wordmark). No
    third-party logos.
  - `homeassistant/custom_components/roamcore/manifest.json` — version
    bumped from `0.1.0-beta.1` to `0.2.0` to mark the polished HACS
    release. `codeowners`, `iot_class`, and `config_flow` retained.
  - `homeassistant/custom_components/roamcore_tileserver/hacs.json` —
    NEW per-sub-integration HACS declaration (single-domain,
    `category: "integration"`, `country: "ALL"`).
  - `homeassistant/custom_components/roamcore_traccar_proxy/hacs.json` —
    NEW per-sub-integration HACS declaration.
  - `scripts/checks/hacs-packaging-smoke.sh` — NEW smoke check that
    validates the package (parses every `hacs.json`, asserts all 3
    integrations have a manifest with `domain/name/version`, asserts
    `branding/icon.png` + `branding/logo.png` are valid PNGs ≥256×256,
    asserts `info.md` exists and is non-empty, asserts each sub-
    integration's `hacs.json` self-references its own domain).
    Wired into `scripts/check.sh --core-only`.
  - `scripts/check.sh` — brought back onto `main` from the trip-stats
    branch's latest known-good copy (it had been living only on
    wave-2 slice branches). The new HACS smoke runs in the core-only
    path.
  - `docs/howto/hacs-custom-repo-install.md` — updated with a
    `Wave 2 #19` block noting the polished HACS metadata, the three
    integrations HACS will surface, and the new smoke check.
  - The auto-provision logic in `__init__.py` and the
    `roamcore.provision_assets` service in `services.yaml` are
    **untouched** — the install flow still works exactly as before.

## Next steps (needs HAOS setup / UI wiring)

1) **Setup Wizard dashboard**
   - Add a Lovelace dashboard YAML for setup flow.
   - Wire stubs to OpenWrt API + Victron connect UI.

2) **HACS default-store listing**
   - Now that the package is polished (info.md + branding +
     sub-integration hacs.json + smoke), the next step is to submit
     RoamCore to the HACS default store so users don't have to add a
     custom repository.
