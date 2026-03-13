# Trip Wrapped (MVP)

Generates a shareable “Trip Wrapped” report from Traccar trip data.

## What it produces

- `latest.json` — raw stats + trip list
- `latest.html` — self-contained HTML report viewable at `/local/...`

## Runtime assumptions (HAOS)

- This code lives under `/config/tools/trip_wrapped/` in Home Assistant.
- Output is written under `/config/www/roamcore/trip_wrapped/` and served at:
  - `/local/roamcore/trip_wrapped/latest.html`

## Usage (CLI)

```bash
python3 export.py \
  --base-url "https://traccar.local" \
  --username "..." \
  --password "..." \
  --device-id 1 \
  --from "2026-03-01T00:00:00Z" \
  --to "2026-03-08T00:00:00Z" \
  --out-json /config/www/roamcore/trip_wrapped/latest.json \
  --out-html /config/www/roamcore/trip_wrapped/latest.html
```

## Notes

- MVP uses stdlib-only HTTP (urllib) and **Basic Auth** to avoid Python deps in HA.
- Later iterations can add:
  - route polyline rendering
  - PNG export (Pillow)
  - nicer HTML templates / branding assets

