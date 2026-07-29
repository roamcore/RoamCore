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

## Implementation outline

- **Backend**: `roamcore-victron-auto` add-on owns discovery + connect and publishes `vt_*` entities via MQTT discovery.
- **UI**: RoamCore custom card / wizard step inside Lovelace calls into the backend.
- **Mapping**: `rc_*` entities are derived from `vt_*` via mapping templates so the UI consumes a stable contract.

## Auto-discovery on LAN (Wave 2 #12)

If the system is not paired yet, RoamCore now probes the LAN for the GX
on its own — the user does not have to click **Connect Victron** to learn
that a GX is on the network.

### Behaviour

1. **Auto-launch on first paint.** When the card mounts on the Power page
   and `binary_sensor.rc_system_power_backend_connected` is `off` (or
   unknown), the wizard probes the LAN once. If it finds a GX, the card
   shows a banner:

   > **We see a Victron GX at `192.168.1.50`**
   > Let's connect it — RoamCore can do the rest.

2. **Periodic re-scan.** While the user is parked on the discover view,
   RoamCore re-probes every 6 seconds (constant
   `_AUTO_RESCAN_INTERVAL_MS`) so a GX that just powered on shows up
   without a manual refresh.

3. **"Enable MQTT over LAN" prompt.** When discovery finds a GX but the
   add-on reports no data is flowing (e.g. `connected=false`, no full
   snapshot yet), the wizard surfaces a plain-English prompt:

   > **One thing to check on your GX**
   > RoamCore found your GX at `<ip>` but no data is flowing. On the GX,
   > open **Settings → Services → MQTT** and turn on
   > **"Enable MQTT over LAN (Broker mode)"**.
   >
   > This setting is off by default on Venus OS. After you flip it, click
   > **Re-scan** here.

   The menu path is rendered as a small ASCII hint so the user can locate
   it on a phone-sized GX touchscreen:

   ```
   [ Settings ] → [ Services ] → [ MQTT ]
          └─ ☑ Enable MQTT over LAN (Broker mode)
   ```

### Recovery flow

1. User opens RoamCore dashboard → Power page.
2. Auto-launch banner says "We see a Victron GX at `<ip>`".
3. User taps the GX candidate in the candidate list → wizard runs.
4. If data starts flowing (status shows `connected=true` and
   `did_full_publish=true`), the wizard drops the user on the success
   step.
5. If data is still not flowing after the add-on reports the connect
   succeeded, the **"Enable MQTT over LAN"** prompt appears with the menu
   path. The user flips the setting on the GX, taps **Re-scan** here, and
   the wizard re-runs from step 2.

### Files touched by this slice

- `homeassistant/www/roamcore/roamcore-victron-connect.js` — added the
  `_AUTO_RESCAN_INTERVAL_MS` constant, the `_MQTT_LAN_PROMPT` copy
  block, and the `_maybeAutoLaunchDiscovery` / `_armRescanTimer` /
  `_shouldShowMqttLanPrompt` / `_buildMqttLanPrompt` helpers.
- `homeassistant/custom_components/roamcore_openclaw_api/view.py` —
  added `pairing.gx_detected` (derived honestly from the paired state;
  `null` when unknown so OpenClaw is not told a lie).
- `scripts/checks/victron-auto-discovery-smoke.sh` — new smoke check.

## Future direction

- Dynamically adjust the Power dashboard based on which entities are discovered/exposed.

