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

## Future direction

- Dynamically adjust the Power dashboard based on which entities are discovered/exposed.

