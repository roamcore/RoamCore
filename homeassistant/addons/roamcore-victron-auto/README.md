# RoamCore Victron Auto (DEV)

**Goal:** a Home Assistant add-on that auto-discovers a Victron GX/Venus OS device on LAN, connects to its MQTT broker, and publishes vendor-layer `vt_*` entities via MQTT Discovery.

## Status
- Discovery: mDNS `_mqtt._tcp` + `venus.local` probe (MVP)
- HA MQTT: connects to local broker (Mosquitto add-on) (MVP)
- Victron MQTT ingest: skeleton (TODO)
- Entity mapping: TODO (dbus-mqtt topics → `vt_*`)

## Notes
This add-on is *DEV* and is designed to run on RoamCore HAOS testbeds.

See:
- `docs/guides/roamcore-dev-mocks.md`
- `docs/reference/rc-entity-naming.md`
