# Trip Wrapped (MVP)

Generates a shareable “Trip Wrapped” report from Traccar trip data.

## What it produces

- `latest.json` — raw stats + trip list
- `latest.html` — self-contained HTML report viewable at `/local/...`

The Story template also includes an in-browser **PNG exporter** (“Download summary”) optimized for social sharing.

## 2. Real Traccar vs demo mode (Wave 4 #73)

Trip Wrapped has **two execution paths**:

1. **Real Traccar path** (default). The exporter calls the configured Traccar
   server (via Basic Auth, user token, or the HA supervisor proxy) and
   reflects the operator's actual trip data. This is the path that runs in
   normal use.
2. **Demo path** (explicit opt-in via `--demo`). The exporter skips Traccar
   entirely and returns a synthetic California road-trip payload. Use this
   for UI previews before you have Traccar configured.

**There is no silent fallback from the real path to the demo path.** If Traccar
is not configured (the configured base URL or device ID is empty / unknown /
unavailable) and `--demo` is not set, the exporter exits with code 2 and an
actionable error message instructing the operator to either configure Traccar
or pass `--demo` explicitly:

```
ERROR: Traccar not configured. Either set rc_traccar_base_url +
rc_traccar_device_id in your RoamCore config OR pass --demo to
generate a demo Trip Wrapped for UI preview.
```

The HA wiring in `homeassistant/packages/roamcore_trip_wrapped.yaml` exposes a
`binary_sensor.rc_traccar_configured` derived entity that flips TRUE when
`input_text.rc_traccar_base_url` + `input_text.rc_traccar_device_id` + (the
Traccar token or password) are all configured. The Trip Wrapped dashboard page
reads this sensor to show the “Traccar not configured — click to set up”
empty-state CTA when it is FALSE.

**How to set up real Traccar:**

1. Install Traccar (the HA Community add-on or your own server).
2. Pair your phone or GPS tracker with Traccar so it reports a position.
3. In Home Assistant, set:
   - `input_text.rc_traccar_base_url` (e.g. `http://localhost:8082`)
   - `input_number.rc_traccar_device_id` (the numeric device ID from Traccar)
   - Either:
     - `roamcore_traccar_user_token` in `/config/secrets.yaml` (recommended), OR
     - `input_text.rc_traccar_username` + `input_text.rc_traccar_password`
4. Confirm `binary_sensor.rc_traccar_configured` is ON.
5. Trigger Trip Wrapped from the dashboard.

**To preview the UI without setting up Traccar:**

- Click the Demo tile on the dashboard (which toggles `input_boolean.rc_demo_mode`).
- The shell command in `homeassistant/packages/roamcore_trip_wrapped.yaml`
  automatically appends `--demo` when `input_boolean.rc_demo_mode` is ON.

## Runtime assumptions (HAOS)

- This code lives under `/config/tools/trip_wrapped/` in Home Assistant.
- Output is written under `/config/www/roamcore/trip_wrapped/` and served at:
  - `/local/roamcore/trip_wrapped/latest.html`

## Production setup (Traccar auth)

Recommended (no stored password in HA):

1) Create a Traccar **User Token**
2) Add it to `/config/secrets.yaml`:

```yaml
roamcore_traccar_user_token: "YOUR_TOKEN"
```

Fallback (basic auth; least preferred):

```yaml
roamcore_traccar_admin_email: "you@example.com"
roamcore_traccar_admin_password: "..."
```

## Data/UX behavior

- If Traccar credentials are missing AND `--demo` is not set, the exporter
  exits with an actionable error (see §2 above). There is no silent fallback
  to demo data.
- If Traccar is reachable but no trips/routes exist for the chosen range/device,
  the exporter shows a helpful no-data notice (`meta.dataStatus = no_data`)
  instead of a blank report.
- When `--demo` is set, the exporter generates the demo payload and tags the
  output with `meta.dataStatus = demo`.

## PNG exporter notes

- The “Download summary” PNG is generated **client-side in the browser**.
- The PNG map background currently uses internet-hosted raster tiles (CORS-enabled) so export works reliably.
- If you see `SecurityError: Tainted canvases may not be exported`, it indicates a non-CORS image/tile was drawn into the export canvas.

Tip: if you suspect caching, open with a cache buster:

`/local/roamcore/trip_wrapped/latest.html?ts=123`

## Usage (CLI)

```bash
python3 export.py \
  --base-url "https://traccar.local" \
  --user-token "..." \
  --device-id 1 \
  --from "2026-03-01T00:00:00Z" \
  --to "2026-03-08T00:00:00Z" \
  --out-json /config/www/roamcore/trip_wrapped/latest.json \
  --out-html /config/www/roamcore/trip_wrapped/latest.html

# Alternative auth

- If you omit `--user-token`, the exporter will try `/config/secrets.yaml`:
  - `roamcore_traccar_user_token`
  - then fall back to the Home Assistant Supervisor proxy (if available)
  - then fall back to Basic Auth using `--username/--password` or:
    - `roamcore_traccar_admin_email`
    - `roamcore_traccar_admin_password`

To disable the Supervisor proxy fallback (useful for local dev):

```bash
python3 export.py --no-ha-proxy ...
```

To preview the UI without Traccar configured:

```bash
python3 export.py --demo \
  --base-url "" --device-id 1 \
  --from "2026-03-01T00:00:00Z" --to "2026-03-08T00:00:00Z" \
  --out-json /tmp/tw.json --out-html /tmp/tw.html
```

## Notes

- MVP uses stdlib-only HTTP (urllib) and supports Traccar **user token** auth to avoid storing credentials in HA.
- The generated `latest.html` is intended to be served by Home Assistant at `/local/...`. It includes no-cache hints and cache-busting for the static map image, but some clients can still cache aggressively—if you see stale content, hard-refresh.
- Static map images are generated by downloading from `https://staticmap.openstreetmap.de/` at export time and saving as `latest_map.png` next to the HTML. If the exporter host is offline (or that service is blocked), the report will still render and will fall back to an offline preview (if route points are available).
- If you open/share the HTML outside of Home Assistant, copy the accompanying `latest_map.png` too (or expect the map to fall back to the offline preview).
- HTTPS/TLS: `urllib` performs certificate validation. If your Traccar uses a self-signed cert, fix the certificate chain (recommended) or run via the HA supervisor proxy.
- Later iterations can add:
  - route polyline rendering
  - server-side PNG export (Pillow) for offline/airgapped installs
  - nicer HTML templates / branding assets
