# RoamCore Power detail page (capability-driven)

The Power detail page is a custom Lovelace card that renders only the
tiles whose required `rc_*` contract entities are present in your live
Home Assistant state. Tiles for unavailable subsystems (e.g. alternator,
cell-level BMS) are **hidden**, not greyed out, and the layout reflows
cleanly to fit whatever tiles you do have.

## Files

| File | Purpose |
| --- | --- |
| `homeassistant/www/roamcore/roamcore-power-page.js` | Custom element (`<roamcore-power-page>`). |
| `homeassistant/www/roamcore/power-capabilities.json` | Manifest describing each tile's required / optional entities. |
| `homeassistant/www/roamcore/roamcore-pages.js` | Companion bundle that defines `RoamcoreBasePage`. |
| `scripts/check_power_capabilities.py` | Schema + backend-match smoke check. |

## Lovelace usage

Embed the new element on any view that uses the RoamCore custom cards:

```yaml
type: custom:roamcore-power-page
```

Or, in a vertical stack with the Victron Connect card:

```yaml
type: vertical-stack
cards:
  - type: custom:roamcore-victron-connect
    title: Victron (Connect)
  - type: custom:roamcore-power-page
```

## Adding or changing a tile

1. Edit `homeassistant/www/roamcore/power-capabilities.json`.
2. Add the matching entity to `homeassistant/packages/roamcore_power.yaml`
   so the prefix actually resolves at runtime.
3. Run `bash scripts/check.sh --core-only` — the new
   `Power: capability-driven page smoke` step validates the manifest
   schema and warns if any required prefix has zero backend matches.

## Empty state

If no tile has all of its required entities (e.g. before Victron is
paired), the page renders a "Victron not connected" card with a button
that opens the RoamCore setup wizard at the same nav path the dashboard
uses (`${basePath}/setup`).