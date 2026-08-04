# Traccar (GPS tracking) integration

**Support tier:** A (RoamCore native)

## What this is
RoamCore ships Traccar support via its own proxy/init components so you can use Traccar as a reliable location history source in Home Assistant.

## Why it’s useful in a van
- Stable location tracking across drives
- Trip history for maps and reports

## Extra hardware required
- A phone or GPS tracker running the Traccar client
- (Optional) your own Traccar server

## Install / best next step
- Setup: `docs/setup/traccar.md`
- If you are building a golden image: `docs/runbooks/traccar-first-boot-provisioning.md`

## Reliability notes

If route lines or Trip Wrapped stop updating, use:

- **RoamCore → Settings → Traccar (Trip tracking)**

This gives you a deterministic reconnect checklist (base URL, device id, token refresh, and a test export).

## Trip Wrapped + Trip Local + Location behavior

Trip Wrapped + Trip Local + Location always reflect the operator's real Traccar data when Traccar is configured; the `--demo` flag is an explicit opt-in for UI preview only. When Traccar is NOT configured and the operator runs a non-demo Trip Wrapped export, the exporter exits with an actionable error message instead of silently substituting demo data. The Trip Wrapped dashboard page reads `binary_sensor.rc_traccar_configured` to surface the "Traccar not configured — click to set up" empty-state CTA.

## Links
- Traccar: https://www.traccar.org/
