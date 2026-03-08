# RoamCore Victron Auto (DEV)

**Goal:** a Home Assistant add-on that auto-discovers a Victron GX/Venus OS device on LAN, connects to its MQTT broker, and publishes vendor-layer `vt_*` entities via MQTT Discovery.

## Status
- Discovery: mDNS `_mqtt._tcp` + `venus.local` probe (MVP)
- HA MQTT: connects to local broker (Mosquitto add-on) (MVP)
- Victron MQTT ingest: connects, learns `portal id` from topics, sends keepalive (MVP)
- Entity mapping: small initial set of `system/*` → `vt_*` sensors (MVP)
- Device instance discovery: capture `N/<portal id>/+/+/ProductId` and publish a diagnostic devices sensor (MVP)

## Victron official MQTT/topic format (Venus OS >= 3.20)

Venus OS uses FlashMQ + `dbus-flashmq`.

Official repo/docs:
- https://github.com/victronenergy/dbus-flashmq
- https://github.com/victronenergy/venus/wiki/dbus

Key points we follow:
- Broker on LAN is reachable on **1883 (plaintext)** and/or **8883 (TLS)** depending on GX settings.
- Local broker authentication/TLS are configured on the GX itself (Settings → Services → MQTT). This add-on
  supports optional `victron_username/password` and TLS CA pinning/insecure TLS based on your LAN posture.
- Notifications publish on topics:
  - `N/<portal id>/<service_type>/<device instance>/<dbus path>`
- To fetch an initial snapshot (since values are not retained), send a keepalive read request:
  - `R/<portal id>/keepalive`
  - and wait for `N/<portal id>/full_publish_completed`

### Portal ID discovery caveat

The portal id is embedded in the topic namespace (`N/<portal id>/...`). If the GX is idle and nothing is changing,
you may not see any initial notifications to auto-learn it — and you can't send keepalives without it.

Workaround: set `victron_portal_id` in add-on options (find it on the GX: **Settings → VRM online portal → VRM Portal ID**).

If discovery does not work in your network, you can also set `victron_host` to the GX IP/hostname.

We also follow the official keep-alive guidance:
- keep-alive timeout is 60s
- after the initial full snapshot, send keepalives with `{"keepalive-options":["suppress-republish"]}` periodically to keep the stream alive without a full republish.

Additional (optional) behaviors implemented for robustness:
- `full_snapshot_interval_sec`: if set >0, request an *empty* keepalive on that interval to force a periodic full refresh.
- `startup_read_requests`: list of read-request suffixes (after the portal id) to fetch rarely-changing values (notably settings). Example: `settings/0/Settings`.

Optionally (Venus OS >= 3.50), we can include a `full-publish-completed-echo` correlation token on the initial keepalive.
This is controlled by the add-on option `keepalive_use_echo` (default: true).

Compatibility fallback (edge cases / older Venus):
- if we don't observe `N/<portal id>/full_publish_completed` shortly after a keepalive with options, retry the keepalive with an empty payload (`-m ''`) which is the canonical example in the dbus-flashmq docs.

### Device discovery (ProductId)

Victron's official docs recommend subscribing to `N/<portal ID>/+/+/ProductId` and then sending a keepalive to
get a full list of connected devices and their *device instances*.

This add-on captures those `ProductId` notifications and (optionally) publishes a Home Assistant MQTT sensor:

- **Victron Devices (discovered)**
  - state: number of discovered devices
  - attributes: `portal_id` + `devices[]` list of `{service_type, device_instance, product_id, last_seen}`
  - guardrail: the list is truncated to `devices_sensor_max` (default 50), with `truncated=true` when applicable.

## Notes
This add-on is *DEV* and is designed to run on RoamCore HAOS testbeds.

See:
- `docs/guides/roamcore-dev-mocks.md`
- `docs/reference/rc-entity-naming.md`
