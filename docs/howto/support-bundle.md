# Exporting a RoamCore support bundle (Home Assistant)

When something isn’t working (install/provisioning issues, missing `rc_*` entities, map/power data not showing, etc.), RoamCore can export a **support bundle** you can share in an issue or with a support person.

The bundle is written under:

- `/config/.roamcore/support/<timestamp>/`

…and (optionally) also as a zip:

- `/config/.roamcore/support/<timestamp>.zip`

## Export via Home Assistant UI

1. In Home Assistant, open **Settings → Developer Tools → Services**
2. Select service: **`roamcore.export_support_bundle`**
3. (Optional) Service data:

```yaml
zip: true
```

4. Click **Call service**

You should see a persistent notification with the output directory (and zip path if created).

## What’s included

The bundle is best-effort and may vary by installation, but it is intended to include:

- Installer/provisioning state:
  - `install-info.txt`
  - `manifest.txt`
  - `provisioned.marker`
- OpenClaw snapshots (no HTTP/token required):
  - `openclaw-summary.json`
  - `openclaw-timeseries-catalog.json`
- Setup wizard progress states:
  - `setup-wizard-states.json`

## Notes / privacy

- The bundle is designed to avoid exporting obvious secrets (like `secrets.yaml`).
- Always review the contents before posting publicly.
