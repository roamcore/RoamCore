# RoamCore UI custom cards (Home Assistant)

RoamCore’s Lovelace UI uses a small set of custom JS resources served from Home Assistant:

- `homeassistant/www/roamcore/roamcore-tiles.js`
  - Overview tiles (Power/Network/Level/Map) as separate cards
  - Delegated click handler (no re-binding on every hass update)
  - Each tile navigates to its subpage

- `homeassistant/www/roamcore/roamcore-pages.js`
  - Power, Network, Level, Map subpages
  - Uses the `rc_*` contract entities for data
  - Level page tilts the van SVGs based on pitch/roll degrees

## Installation (high level)

1. Copy JS into Home Assistant:
   - `/config/www/roamcore/roamcore-tiles.js`
   - `/config/www/roamcore/roamcore-pages.js`

2. Register resources in Lovelace:
   - URL: `/local/roamcore/roamcore-tiles.js` (type: module)
   - URL: `/local/roamcore/roamcore-pages.js` (type: module)

3. Use cards in dashboards:
   - Overview tiles:
     - `custom:roamcore-power-tile`
     - `custom:roamcore-network-tile`
     - `custom:roamcore-level-tile`
     - `custom:roamcore-map-tile`

   - Subpages:
     - `custom:roamcore-power-page`
     - `custom:roamcore-network-page`
     - `custom:roamcore-level-page`
     - `custom:roamcore-map-page`

## Performance notes

These cards are written to avoid a common HA frontend perf issue: attaching new event listeners on every render (`set hass()` is called frequently). Navigation uses a single delegated handler bound once.
