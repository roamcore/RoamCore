# RoamCore MVP — Features Build Status

Last updated: 2026-07-29

This is an internal status page for the remaining MVP feature build-out.

## Shipped (repo)

- Hardware auto-discovery + setup flows — Wave 2 #31 (slice shipped)
  - Contract package: `homeassistant/packages/roamcore_hardware_discovery.yaml` (5 add-on binary_sensors + 2 summary sensors + master switch + per-add-on setup helpers)
  - Wizard snippet: `homeassistant/packages/roamcore_setup_wizard_hardware_discovery.yaml` (markdown + glance + entities card with one-tap "Set up" CTA per row)
  - Probe helper: `homeassistant/tools/hardware_discovery/probe.py` (stdlib-only Python; one TCP-connect / filesystem probe per add-on)
  - Helper README: `homeassistant/tools/hardware_discovery/README.md`
  - Setup doc: `docs/setup/hardware-auto-discovery.md` (privacy + per-add-on enable/disable + troubleshooting + what's next)
  - Custom service: `roamcore.hardware_setup_prompt(addon=...)` declared in `homeassistant/custom_components/roamcore/services.yaml` + handler in `__init__.py` (flips `input_boolean.rc_hardware_setup_<addon>_pending` ON + writes a "ready to set up" pill to `input_text.rc_hardware_setup_<addon>_message`)
  - Smoke check: `scripts/checks/hardware-auto-discovery-smoke.sh` wired into `scripts/check.sh --core-only` (39 assertions incl. privacy invariant)
  - Privacy: every probe target is loopback / RFC1918 / link-local / RFC4193 unique-local IPv6 / local filesystem — no public IP, no DNS, no WAN. The smoke grep asserts this across the package + helper and fails the build on any violation.
  - Tier-b: well-scoped, documented, smoke-verified; foundation for the follow-up Additional hardware support slice (Row #304, line 74 in `docs/feature-checklist.md`).

- OTA updates (GitHub channel + rollback-aware) — Wave 2 #30 (slice shipped)
  - Add-on: `homeassistant/addons/roamcore_ota/` (poller + 3-snapshot history at `/share/roamcore/snapshots/`)
  - Contract package: `homeassistant/packages/roamcore_ota.yaml` (sensors + helpers + auto-apply scheduler at 03:00 local)
  - Wizard snippet: `homeassistant/packages/roamcore_setup_wizard_ota.yaml` (paste-this-card for the OTA stage)
  - Setup doc: `docs/setup/ota.md`
  - Architecture doc: `docs/architecture/ota-channel.md`
  - Smoke check: `scripts/checks/ota-smoke.sh` wired into `scripts/check.sh --core-only`
  - Privacy: only outbound traffic is `api.github.com` over HTTPS (no telemetry)

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

## Next steps (needs HAOS setup / UI wiring)

1) **Setup Wizard dashboard**
   - Add a Lovelace dashboard YAML for setup flow.
   - Wire stubs to OpenWrt API + Victron connect UI.

2) **Traccar install + integration in HAOS**
   - Install Traccar add-on (or point to external).
   - Configure HA Traccar integration so `device_tracker.*` exists.
   - Set `input_text.rc_location_tracker_entity` to the correct entity.

3) **Trip stats (rc_trip_*) from real Traccar data**
   - MVP still uses mocks for distance/time/stops.
   - Implement: odometer-based + utility_meter or periodic report pulls.

4) **HACS packaging (planned)**
   - Publish a HACS integration to install RoamCore from the HA UI.
   - Auto-create dashboard + resources.
