# GeoLocator (Timezone + Location) — Recommended for RoamCore

RoamCore is designed for mobile Home Assistant installs (vans/RVs/boats) where timezone changes matter.

Home Assistant **does not reliably update its system timezone automatically** as you travel. That breaks:
- time-based automations
- sun events
- templates like `now()` / `today_at()`

The best “reuse-first” solution is **GeoLocator** by SmartyVan:

- Repo: https://github.com/SmartyVan/hass-geolocator
- Purpose: set HA timezone from GPS, with an offline fallback.

RoamCore recommends using GeoLocator rather than maintaining a custom timezone engine.

---

## Install (HACS)

1) Home Assistant → **HACS** → Integrations
2) ⋮ → **Custom repositories**
3) Add:
   - URL: `https://github.com/SmartyVan/hass-geolocator`
   - Category: **Integration**
4) Install **GeoLocator**
5) Restart Home Assistant

---

## Configure (minimal)

GeoLocator reads GPS coordinates from `zone.home`.

### Step 1 — Keep `zone.home` coordinates updated

If you already have a GPS tracker in Home Assistant (e.g. Traccar, HA Companion App), you can update HA’s location by calling:

```yaml
service: homeassistant.set_location
data:
  latitude: 34.0549
  longitude: -118.2426
```

For vans, you can trigger this when your chosen tracker updates (and optionally only when moving).

### Step 2 — Update GeoLocator

Call:

```yaml
service: geolocator.update_location
data: {}
```

This will:
- compute the correct timezone ID, and
- update Home Assistant’s system timezone if it changed.

---

## Suggested automation (RoamCore-friendly)

This is intentionally conservative (avoids thrashing):

```yaml
alias: "RoamCore: Update timezone (GeoLocator)"
mode: single
trigger:
  - platform: time_pattern
    minutes: "/15"
condition: []
action:
  - service: geolocator.update_location
    data: {}
```

If you prefer event-driven updates, trigger on `zone.home` changes instead.

---

## What RoamCore uses

Once GeoLocator is installed and running, RoamCore can treat timezone as reliable for:
- Weather/Time automations
- “local time” displays
- future Setup Wizard checks

RoamCore does not fork GeoLocator. Updates should be applied via HACS.

