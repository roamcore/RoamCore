# Victron onboarding: "Connect Victron" flow (MVP)

This doc captures the product direction for Victron onboarding in RoamCore.

## End goal

- Ship a **fully configured RoamCore image** for the target hardware (VP2430).
- Provide a **simple onboarding wizard** embedded in the RoamCore Lovelace dashboard.
- Provide a single, obvious entry point on the **Power** page: **Connect Victron**.

## MVP user experience

1. User opens RoamCore dashboard → Power page.
2. If Victron is not connected, the UI shows a prominent button: **Connect Victron**.
3. User clicks the button.
4. RoamCore scans the LAN for Victron GX/Venus devices.
5. UI lists the discovered devices.
6. User selects the device they want to connect.
7. RoamCore applies the configuration automatically (no manual MQTT config).
8. Victron data begins flowing via MQTT and the dashboard starts showing values.

### Pairing wizard (Wave 2, 2026-07)

The "Connect Victron" button is now a guided multi-step wizard instead of a
single form. The wizard lives in `homeassistant/www/roamcore/roamcore-victron-connect.js`
and is registered as the Lovelace card `custom:roamcore-victron-connect`. It
keeps the existing card slot, so installs don't need to update their dashboard
YAML to get the new behavior.

#### Steps

| # | Step         | What the user sees                                                                                  |
|---|--------------|------------------------------------------------------------------------------------------------------|
| 1 | Intro        | "Let's connect your Victron system" + a short "what you'll need" list + **Get started**             |
| 2 | Discover     | LAN scan for GX devices, plus a manual IP fallback. Recovery if nothing is found.                    |
| 3 | Connecting   | Live progress: saving the selection, restarting the add-on, verifying data is flowing.              |
| 4 | Success      | "You're connected", summary of what changed, **Go to Power** one-click jump.                        |

Each step has a working **Back** affordance that preserves what the user has
already typed/selected. There is no dead-end screen — if discovery or
connection fails, the user is shown a plain-English cause and the next action.

#### Recovery affordances

- **Discovery found nothing** — three paths, all in plain English:
  1. **Scan again** (sometimes the second scan picks it up).
  2. **Type the IP address** (with a one-line hint: "look under Settings → General on the GX Remote Console").
  3. **Check the basics** (expandable: "is the GX on the same Wi-Fi as RoamCore?").
- **Connection failed** — the wizard shows a categorized error (timeout,
  unreachable, invalid host, persist failed) with a single next action.

#### Visibility

- The wizard exposes the same state OpenClaw reads: the add-on's status
  endpoint powers the progress check, and the existing
  `binary_sensor.rc_system_power_backend_connected` /
  `sensor.rc_system_power_backend_status` contract entities surface
  "is Victron paired?" in `/api/roamcore/openclaw/summary` under the new
  `pairing` block.

#### Files

- `homeassistant/www/roamcore/roamcore-victron-connect.js` — wizard UI
  (replaces the single-form connect card; backwards compatible card name).
- `homeassistant/addons/roamcore-victron-auto/` — discovery + connect
  backend (unchanged contract; still exposes
  `roamcore/victron/<device_id>/status`, `snapshot_state`, and the
  HTTP API on the ingress port).
- `homeassistant/custom_components/roamcore_openclaw_api/view.py` —
  adds the `pairing` block to the OpenClaw summary.
- `homeassistant/packages/roamcore_victron_health.yaml` — owns the
  `rc_system_power_backend_*` contract entities (no changes; the wizard
  reads them as the source of truth).

## Implementation outline

- **Backend**: `roamcore-victron-auto` add-on owns discovery + connect and publishes `vt_*` entities via MQTT discovery.
- **UI**: RoamCore custom card / wizard step inside Lovelace calls into the backend.
- **Mapping**: `rc_*` entities are derived from `vt_*` via mapping templates so the UI consumes a stable contract.

## Future direction

- Dynamically adjust the Power dashboard based on which entities are discovered/exposed.