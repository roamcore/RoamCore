# In‑cab dashboard (driving tablet)

**Support tier:** C

> **SUPERSEDED 2026-08-02 by `connections/in-cab-tablet-dashboard/connection.yml` + `connections/in-cab-tablet-dashboard/docs/recipe.md`. This legacy tier-c catalog page is kept as a thin folder-overview pointer for backward compatibility.**

Mount a small tablet in the cab that shows the handful of controls and readouts you care about while driving: exterior lighting, compressor, basic house status, and key vehicle stats.

## What you need
- An in-cab tablet (or head unit) running the Home Assistant app
- Vehicle stats source (OBD/CAN adapter, or a vehicle integration)
- Any controllable cab-relevant devices (lights, compressor, etc.)

## What RoamCore would do
- Provide a “Driving” friendly view:
  - Big buttons, minimal text
  - Only safe interactions while moving
- Optionally auto-switch the UI when ignition turns on

