# Troubleshooting

This page collects the most common HA-only beta issues.

## Install issues

### The installer ran, but I don’t see RoamCore files

On the HA host, verify:

```sh
ls -la /config/packages | grep roamcore
ls -la /config/www/roamcore
ls -la /config/lovelace | grep roamcore
```

If those don’t exist, re-run the installer from:
- `docs/howto/homeassistant-installer.md`

### How do I uninstall cleanly?

Use the one-line uninstaller:

```sh
curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/uninstall.sh | sh
```

The installer keeps state (manifest + backups) at `/config/.roamcore/`.

## Map issues

### Map is blank / grey

This should not happen in current beta builds; the map code forces a raster fallback.
If it does:

1) Reload the page.
2) Confirm `/local/roamcore/…` assets are loading (browser DevTools → Network).
3) Temporarily set the map style URL to an invalid path and confirm the raster-only fallback appears.

## OpenClaw JSON API

### `/api/roamcore/openclaw/summary` returns missing/null fields

That typically means the upstream `rc_*` entities are missing or `unavailable`.
Check the `debug.entities` block in the response to see which entity ids are present.


Common issues and fixes.
