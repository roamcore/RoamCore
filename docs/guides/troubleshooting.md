# Troubleshooting & Support

This guide is for **field debugging** and for gathering the information needed to open a support ticket.

## 1) Use the RoamCore Diagnostics page

Open the RoamCore dashboard and navigate to:

- **Settings → Diagnostics**
- Or directly: `/roamcore/diagnostics`

The Diagnostics page is designed to answer three questions quickly:

1. **Was RoamCore installed/provisioned correctly?**
2. **Are the core backends ready (Victron / Trip Wrapped / Map / Owner)?**
3. **Which `rc_*` entities exist and what are their current states?**

### Copy a JSON support bundle

On the Diagnostics page, click:

- **Copy JSON support bundle**

This copies a single JSON blob to your clipboard that includes:

- RoamCore component version
- Provisioning / install markers (from `/config/.roamcore/*`)
- A curated list of key entity presence + state
- A full `rc_*` state dump (for bring-up)

Paste that JSON into your support ticket (GitHub issue) along with:

- What you expected to happen
- What actually happened
- Screenshots (optional)

If clipboard copy fails (some in-app WebViews block clipboard), open Home Assistant in a regular browser and try again.

## 2) Optional: export a support bundle ZIP (on-device)

If you have access to Home Assistant’s **Developer Tools → Services**, you can export a support bundle to disk:

- Service: `roamcore.export_support_bundle`
- Data:
  - `zip: true` (default)

This writes a bundle under:

- `/config/.roamcore/support/<timestamp>/`

and (optionally) creates:

- `/config/.roamcore/support/<timestamp>.zip`

Attach the ZIP to your support ticket **only if requested**.

## 3) Common failure modes

### Provision marker is missing

- `provisioned.marker` missing usually means the auto-provision step did not run or failed.
- Ensure Home Assistant has internet/DNS access during install.

### Key entities missing

- Missing entities usually means the relevant RoamCore packages were not loaded.
- Confirm the RoamCore dashboard + packages were provisioned under `/config/`.
- Restart Home Assistant after provisioning.

### Victron backend not connected

- Check `binary_sensor.rc_system_power_backend_connected`
- Verify the Victron add-on is installed/running and MQTT topics are present.

---

If you’re filing an issue, include the JSON bundle + a brief timeline of what changed (updates, reboots, new hardware, etc.).
