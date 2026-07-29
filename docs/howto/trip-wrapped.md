# Trip Wrapped — How-To

RoamCore's Trip Wrapped turns your Traccar trip history into a shareable
HTML + JSON recap (distance, drive time, top trip, stops, map).

## First-run (no Traccar yet)

A brand-new RoamCore install shows a fully-rendered demo report with one tap:

1. **Map** page → **Trip Wrapped** tile → **Options**.
2. Tap **Generate demo trip**. The one-tap CTA only appears when no
   `latest.json` exists yet.
3. Open **/local/roamcore/trip_wrapped/latest.html** to view the report.

This is powered by the local demo seed generator:

```bash
python3 /config/tools/trip_wrapped/demo_seed.py \
  --out /config/www/roamcore/trip_wrapped/latest.json
```

The seed is **stdlib-only**, makes **zero outbound HTTP calls**, and points
the map image at the local RoamCore tileserver add-on
(`http://localhost:8000/...`). It is privacy-compliant by construction;
see the smoke check at `scripts/checks/trip-wrapped-seamless-smoke.sh`.

To call it from a service instead of the UI:

```yaml
service: roamcore.trip_wrapped_demo
data:
  out: /config/www/roamcore/trip_wrapped/latest.json
```

## Switching to real trips (Traccar configured)

Once you have Traccar installed and reachable from HA:

1. Configure your token (see `homeassistant/tools/trip_wrapped/README.md`).
2. Turn **Settings → Helpers → `input_boolean.rc_trip_wrapped_real`** to **ON**.
3. The dashboard stops showing the demo CTA. The automation
   `rc_trip_wrapped_real_turns_off_demo` also turns `rc_trip_wrapped_demo`
   **OFF** so the two flags stay mutually exclusive.
4. Tap **Generate** in the Trip Wrapped modal to pull live data via the
   existing `shell_command.rc_trip_wrapped_export` path.

## Privacy contract

Trip data stays on-device by default. The trip pipeline refuses any
outbound HTTP call unless the target is loopback or the local add-on CIDR.
External hosts must be opted in via `input_text.rc_trip_opt_in_domains` or
the `homeassistant/tools/trip_wrapped/privacy_allowlist.json` allowlist.
See `docs/feature-checklist.md` (Map / Trip section) for the full contract
and `scripts/checks/trip-tracking-privacy-smoke.sh` for enforcement.

## Troubleshooting

- **No Trip Wrapped appears.** Check `sensor.rc_trip_wrapped_latest_status`
  in Developer Tools → States. Values: `ok`, `needs_setup`, `no_data`,
  `missing`, `demo`.
- **Demo CTA doesn't show.** Confirm `sensor.rc_trip_wrapped_latest_status`
  is `missing` or `unknown`. If `latest.json` already exists, the dashboard
  shows the real CTA instead.
- **Map background is blank.** The local tileserver add-on must be running
  at `http://localhost:8000/`. The demo seed points there by design.