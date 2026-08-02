# Time (atomic) (NTP-synchronized time with offline-resilience)

**Tier:** C (recipe)
**Category:** time
**Status:** recipe_published

## What this connection is

Time (atomic) (NTP-synchronized time with offline-resilience) — the umbrella for "keep HA's clock accurate even when offline (in a van with intermittent connectivity)" — is the time-category complement to the existing RoamCore time helpers (`homeassistant/packages/roamcore_weather_time.yaml` + `sensor.rc_time_zone` override contract) and to the Wave 3 #54 timezone-geolocator connection (which handles "what timezone IS it?"; this slice handles "what time IS it?"). The single "is the clock NTP-synced?" tile aggregates HA core's `time` integration's last-sync state into one dashboard indicator; the "is the clock stale?" tile is the freshness gate (TRUE when `sensor.rc_time_last_sync_minutes_ago` > 60); the NTP-reachable binary_sensor surfaces whether the LTE / Starlink backhaul can reach an NTP server; the RTC-present binary_sensor surfaces whether the DS3231 / RV-3028 RTC module is detected on the van's NUC / SBC.

RoamCore ships **no** native atomic-clock engine. We RECIPE the upstream HA core `time` integration (since 2022.x — exposes NTP servers + `sensor.time` + `sensor.date` + date/time helpers) + a thin RoamCore automation wrapper that runs the THREE §7 automations (NTP cadence refresh on boot + GPS time correction on `device_tracker` + timezone change + RTC fallback when NTP unreachable for N minutes). The 8 `rc_time_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual time sync is done by HA core's `time` integration + the SBC's `systemd-timesyncd` + the DS3231 / RV-3028 RTC module (RoamCore does NOT fork any of these).

## Setup recipe (one-paragraph)

1. Pick a time source (one or more of):
   - **Path A — NTP via HA core `time` integration.** HA Settings → Devices & Services → Add Integration → Time (the official HA Time integration since 2022.x exposes a GUI flow). Configure NTP servers (recommended: `time.cloudflare.com` + `time.google.com` + `pool.ntp.org`).
   - **Path B — GPS-derived time.** Wire a GPS source (Traccar Wave 3 #36 server `device_tracker.rc_location_van` OR HA Companion app `device_tracker.<phone>` OR Wican Pro Wave 3 #6 OBD-II's GPS feed OR any `device_tracker.*` updating `zone.home`). GPS satellites carry atomic-clock-grade time signals — the recipe wires a periodic time-correction automation that reads GPS time when NTP is unreachable.
   - **Path C — RTC fallback.** Wire a DS3231 / RV-3028 I2C RTC module to the van's NUC / SBC. Configure `systemd-timesyncd` to fall back to the RTC when NTP is unreachable + a `hwclock --systohc` cron to keep the RTC updated. This is the offline-resilience feature — the van can lose LTE / Starlink for hours and still keep accurate time via the RTC.
2. Restart Home Assistant (HA core's `time` integration loads at startup).
3. Confirm the upstream `sensor.time` + `sensor.date` entities exist in HA.
4. Wire the THREE §7 automations (NTP cadence refresh on boot + GPS time correction on `device_tracker` + timezone change + RTC fallback when NTP unreachable for N minutes) BEFORE first use.
5. Verify: check `sensor.rc_time_current` reflects the correct time + `binary_sensor.rc_time_synced` is TRUE.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-c, not tier-b

Tier-b would require a RoamCore-owned atomic-clock engine + integration code + integration tests against a real time-sync bench (a controlled NTP server + a GPS source simulator + a DS3231 / RV-3028 RTC module). We have no operator-side atomic-clock bench on the CI to integration-test against (the bench requires all three paths wired together in a controlled environment — NTP server reachability, GPS source coordinates, RTC module battery + drift). Tier-c is the honest tier: HA core's `time` integration is upstream HA core code (not RoamCore-owned); the RoamCore wrapper is a few thin automations + a contract layer. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (`docs/catalog/time/atomic-time.md` — created in this slice as the legacy spec pointer) listed "Support tier: C" with no recipe + no contract + no automations — that placeholder is now superseded by this tier-c recipe connection.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "time_atomic"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (created + now superseded by this slice): [`docs/catalog/time/atomic-time.md`](../../docs/catalog/time/atomic-time.md)
- HA core `time` integration: https://www.home-assistant.io/integrations/time/
- Traccar connection (the canonical GPS source for Path B; Wave 3 #36): `connections/traccar/`
- Wican Pro OBD-II connection (the optional GPS source for Path B; Wave 3 #6): `connections/wican-pro/`
- Timezone geolocator connection (Wave 3 #54 — handles "what timezone IS it?"; this slice handles "what time IS it?"): `connections/timezone-geolocator/`
- Teltonika (the optional LTE/5G router for vans; Wave 3 #39): `connections/teltonika/`
- HA Companion app (the operator-side GPS source for Path B): upstream integration
- Time / weather contract (the existing time helpers; Wave 2 #14 + Wave 2 #15 + Wave 3 #54): `homeassistant/packages/roamcore_weather_time.yaml`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
