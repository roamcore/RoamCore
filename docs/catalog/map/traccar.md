# Traccar (GPS tracking) integration

**Support tier:** B (recipe + manual add-on install)

> **Tier B note:** this connection is a recipe install, not a one-tap.
> The user installs the upstream Traccar server add-on plus the RoamCore
> Traccar Init + Proxy add-ons, then restarts Home Assistant. There is
> no config_flow yet in the `roamcore_traccar_proxy` integration (it
> uses `async_setup` only), so the audit correctly classifies this as
> tier-b. Promotion to tier-a requires a config_flow + integration
> tests; see `connections/traccar/connection.yml` for the
> `promotion_blocker` notes.

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

## Links
- Traccar: https://www.traccar.org/
