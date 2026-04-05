# Victron Integration (RoamCore) — Runbook

This runbook documents the canonical upstream references + the RoamCore mapping layers.

## Upstream References (Victron)

**MQTT + topic semantics (Venus OS >= 3.20):**
- `dbus-flashmq` README (authoritative):
  - https://github.com/victronenergy/dbus-flashmq/blob/master/README.md

Related background:
- Venus OS wiki:
  - https://github.com/victronenergy/venus/wiki

## Canonical MQTT Topic Format (dbus-flashmq)

Notifications (value change events):
- `N/<portal_id>/<service_type>/<device_instance>/<dbus_path>`
- Payload is JSON: `{ "value": <scalar|null> }`

Edge cases:
- invalid value: `{ "value": null }`
- device disappears: payload may be empty (zero bytes, not valid JSON)

Read requests:
- `R/<portal_id>/<service_type>/<device_instance>/<dbus_path>`

Keepalive / snapshot:
- publish to `R/<portal_id>/keepalive`
- wait for `N/<portal_id>/full_publish_completed`

After initial snapshot, use keepalive-options to avoid full republish:
- `{ "keepalive-options": ["suppress-republish"] }`

## RoamCore Layers

### Vendor layer (`vt_*`)
Source:
- RoamCore Victron Auto add-on publishes `vt_*` entities into Home Assistant via MQTT Discovery.

Goal:
- Provide a small, stable set of vendor-specific entities (still “Victron-shaped”).

### Contract layer (`rc_*`)
Source:
- Home Assistant template sensors in `homeassistant/packages/*`.

Goal:
- Provide a stable RoamCore contract so the UI is insulated from upstream changes.

Hard rule:
- The RoamCore dashboard should reference **only `rc_*`** entities.

## Coverage / Completeness Strategy

To ensure we can ingest the full Victron dataset:
1) Enumerate all devices/instances by subscribing to:
   - `N/<portal_id>/+/+/ProductId`
2) Capture a topic inventory from `N/<portal_id>/#` and compare against the RoamCore “minimum telemetry set”.
3) Expand `vt_*` mappings incrementally and keep `rc_*` stable.

---

## Pairing / Setup Wizard (Beta)

RoamCore’s beta UX goal is that a user can:
- install the RoamCore Victron Auto add-on,
- open the RoamCore dashboard,
- and connect to their GX device via the embedded pairing card.

Implementation notes:
- The pairing UI lives in the Lovelace card `custom:roamcore-victron-connect`.
- That card calls the add-on ingress API:
  - `GET /api/v1/victron/discover`
  - `POST /api/v1/victron/connect`
  - `GET /api/v1/victron/status`
- Health for the wizard is derived from retained MQTT status topics published by the add-on:
  - `roamcore/victron/<device_id>/availability` (online/offline)
  - `roamcore/victron/<device_id>/status` (connected/searching)
  - `roamcore/victron/<device_id>/snapshot_state` (ready/pending)

The contract-level readiness bit used by the setup wizard is:
- `binary_sensor.rc_system_power_backend_connected`

Which then feeds:
- `binary_sensor.rc_setup_victron_ready`
