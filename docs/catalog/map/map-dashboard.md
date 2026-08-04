# RoamCore Map (dashboard + route)

**Support tier:** A (RoamCore native)

## What this is
A live map on the RoamCore dashboard. Shows where you are right now, plus your today's trip or recent trips as an optional overlay.

## Why it's useful in a van
- "Where are we / where did we park?" in one glance
- See today's trip without pulling out a separate app

## Extra hardware required
- None if you already have a `device_tracker` (Traccar, HA Companion app, USB GPS, etc.)

## 5-step install

1. **Confirm the three RoamCore map packages are loaded.** Add to `homeassistant/configuration.yaml`:
   ```yaml
   homeassistant:
     packages:
       packs:
         - homeassistant/packages/roamcore_map.yaml
         - homeassistant/packages/roamcore_map_route.yaml
         - homeassistant/packages/roamcore_location.yaml
   ```
   Restart Home Assistant.

2. **Point `input_text.rc_location_tracker_entity` at your `device_tracker.*`** (Settings → Helpers → "RC Location Tracker Entity"). Examples:
   - `device_tracker.traccar_van` (Traccar)
   - `device_tracker.<your_phone>` (HA Companion app)

3. **Basemap is OpenStreetMap by default — free, no API key.** The default URL in `homeassistant/packages/roamcore_map.yaml` is:
   ```
   https://tile.openstreetmap.org/{z}/{x}/{y}.png
   ```
   The Lovelace map card renders the required "© OpenStreetMap contributors" attribution automatically. To swap basemaps (Stadia, Carto, self-hosted, …) paste a new URL into Settings → Helpers → "RC Map Tile URL". Common one-line swaps:
   - **Stadia Maps** (free for non-commercial, API key required): `https://tiles.stadia.com/{z}/{x}/{y}@2x?api_key=YOUR_KEY` — sign up at https://docs.stadiamaps.com/
   - **Carto Positron** (no key, light theme): `https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png`

4. **Add a Lovelace map card.** Open the map view and add the upstream HA core `map:` card. The card shows your current location automatically.

5. **Verify and you're done.** Open the map view. You should see your current location marker on the OSM basemap with "© OpenStreetMap contributors" attribution. If the basemap is unreachable, the map shows a gray background with a banner: "Map tiles unavailable — you can still see your last-known location. Check your internet connection."

## What you don't need
- An API key for the default basemap (OSM is free)
- A HACS add-on
- A custom_components folder
- A separate offline-tile cache (the map falls back to a plain gray basemap with your last-known location when tiles are unreachable)

## Links
- OSM tile usage policy: https://operations.osmfoundation.org/policies/tiles/
- Stadia Maps (free tier): https://docs.stadiamaps.com/
- Recipe (advanced, FIVE §9 MANDATORY automations, troubleshooting): `connections/map-dashboard/docs/recipe.md`
- HA core `map:` card: https://www.home-assistant.io/integrations/map/