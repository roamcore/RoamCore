# MQTT — vendor-neutral lightweight pub/sub messaging layer for IoT devices

**Tier:** B (recipe)
**Category:** homelab
**Status:** beta

## What this connection is

MQTT — vendor-neutral lightweight pub/sub messaging layer that the upstream HA core `mqtt` integration uses for Victron GX + Teltonika + Wican Pro + Shelly + Tasmota + ESPHome + Traccar + 90%+ of IoT devices — is the homelab-category umbrella for "the broker everything depends on". The recipe walks the operator through THREE upstream broker paths (Path A HACS mosquitto add-on — recommended for most operators; Path B external / cloud broker; Path C local container / VM broker) + mounting the broker credentials (`input_text.rc_mqtt_broker_url` default `tcp://core-mosquitto:1883`; `input_text.rc_mqtt_broker_username`; `input_boolean.rc_mqtt_broker_tls_enabled`) + confirming the broker is online (`binary_sensor.rc_mqtt_broker_online` reads TRUE) + enabling + starting publishing (`input_boolean.rc_mqtt_enabled` flips ON; the upstream `mqtt.publish` service exposes a GUI flow under Developer Tools → Services) + auditing (the HA core `logbook` integration is the canonical audit-log destination; `sensor.rc_mqtt_discovery_count` mirrors the upstream `mqtt` integration's auto-discovery signal) + reverting at any time via `button.rc_mqtt_reconnect_now` (the operator-triggered one-tap reconnect — flips the upstream `mqtt` integration's connection state + re-publishes the `homeassistant/status` topic + clears the offline guard).

RoamCore ships **no** native pub/sub broker engine. We RECIPE the well-understood upstream HA core `mqtt` integration (since 2022.x — exposes the canonical pub/sub messaging layer for Home Assistant automations; auto-discovers upstream sensors + binary_sensors + switches + lights + covers via the canonical upstream `mqtt` discovery protocol since 2022.x) + the HACS mosquitto add-on (the canonical upstream vendor-neutral local broker add-on; auto-starts on HA boot; auto-configures the upstream HA core `mqtt` integration to point at the local broker) + the HA core `input_boolean` + `input_text` + `input_number` + `input_select` + `input_datetime` + `input_button` + `script` helper entities (since 2022.x — expose a GUI flow for the operator to add the helper entities from the HA UI under Settings → Helpers) + the HA core `template:` sensor + binary_sensor wrappers (since 2022.x — wraps any upstream sensor state into a derived `sensor.*` entity) + the HA core `logbook` integration (since 2022.x — the canonical audit-log destination for Home Assistant automations). The 8 `rc_mqtt_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual pub/sub logic is provided by the upstream HA core `mqtt` integration + the HACS mosquitto add-on (RoamCore does NOT fork any of these).

## The 5-step operator flow

- **Step 1 — Pick the broker path** — the operator chooses ONE of the THREE upstream broker paths documented in §3: Path A (HACS mosquitto add-on, recommended for most operators; local-only + auto-starts on HA boot + auto-configures the upstream HA core `mqtt` integration to point at the local broker; no vendor-specific credentials required); Path B (external / cloud broker, for operators who already run a broker off-box; the recipe documents how to wire the upstream HA core `mqtt` integration to point at the external broker + how to secure the connection with username / password / TLS); Path C (local container / VM broker, for operators who want a Docker / Podman / LXC / VM broker on the same Proxmox box or on a separate mini-PC; the recipe documents the vendor-neutral generic broker wire-up).

- **Step 2 — Mount the broker credentials** — the operator configures `input_text.rc_mqtt_broker_url` (default `tcp://core-mosquitto:1883`) + the optional `input_text.rc_mqtt_broker_username` + the optional `input_text.rc_mqtt_broker_password` (referenced indirectly via `secrets.yaml`) + `input_boolean.rc_mqtt_broker_tls_enabled` (default FALSE for the recommended local-only mode). The §4 operator flow walks the operator through populating the broker credentials + confirming the broker URL is reachable.

- **Step 3 — Confirm the broker is online** — the operator confirms `binary_sensor.rc_mqtt_broker_online` reads TRUE (the §8.1 broker-offline guard's canonical safety chip). The §5 operator flow walks the operator through confirming the broker is online before the first publish.

- **Step 4 — Enable + start publishing** — the operator flips `input_boolean.rc_mqtt_enabled` ON (the upstream HA core `mqtt` integration's master enable; the upstream `mqtt.publish` service exposes a GUI flow for the operator to publish from the HA UI under Developer Tools → Services). The `sensor.rc_mqtt_broker_status` surfaces "online" / "offline" / "tls_error" / "auth_error" / "disabled" / "unknown".

- **Step 5 — Audit + revert** — every broker connection state change + every `mqtt.publish` service call + every `mqtt.publish` event received writes an entry to `sensor.rc_mqtt_discovery_count` (the resolved count of upstream `mqtt` discovery messages received in the last 24 hours) + the HA core `logbook` (the canonical audit-log destination). The operator can revert at any time via `button.rc_mqtt_reconnect_now`.

## Setup recipe (one-paragraph)

1. Decide which broker path you want (most operators: Path A HACS mosquitto add-on; Path B external / cloud broker if you already run a broker off-box; Path C local container / VM broker if you want a Docker / Podman / LXC / VM broker on the same Proxmox box).
2. Install the HACS mosquitto add-on (Path A) or the external / cloud broker (Path B) or the local container / VM broker (Path C). The recipe documents all THREE paths in §3.
3. Install the upstream HA core `mqtt` integration (auto-installed in every HA install + exposed via the HA UI under Settings → Devices & services → Integrations → Add Integration → MQTT).
4. Configure the broker URL via `input_text.rc_mqtt_broker_url` (default `tcp://core-mosquitto:1883` for Path A; your broker's URL for Path B / C).
5. Configure the broker username + password + TLS toggle via `input_text.rc_mqtt_broker_username` + `input_boolean.rc_mqtt_broker_tls_enabled` (default empty username + FALSE TLS for Path A).
6. Wire the operator-facing `binary_sensor.rc_mqtt_broker_online` + `sensor.rc_mqtt_broker_status` + `sensor.rc_mqtt_discovery_count` + `button.rc_mqtt_reconnect_now` + `input_boolean.rc_mqtt_enabled` contract tiles to point at the upstream HA core `mqtt` integration's connection state + the `template:` wrappers + the `logbook` integration.
7. Wire the FIVE §8 MANDATORY automations (broker-offline guard + broker-online guard + broker-tls-error guard + broker-auth-error guard + publish-from-HA guard).
8. Verify: confirm the broker is online → mount the broker credentials → enable → publish a known test topic via `mqtt.publish` from Developer Tools → Services → confirm the publish fires + confirm `sensor.rc_mqtt_discovery_count` increments → press `button.rc_mqtt_reconnect_now` → confirm the broker reconnects.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## The 8 `rc_mqtt_*` contract tiles

| Domain | Tile id | Purpose |
|---|---|---|
| `binary_sensor` | `rc_mqtt_broker_online` | TRUE when the upstream `mqtt` integration reports a connected state. The §8.1 broker-offline guard's canonical safety chip + the §8.2 broker-online guard's target. |
| `sensor` | `rc_mqtt_broker_status` | Resolved broker connection status (`online` / `offline` / `tls_error` / `auth_error` / `disabled` / `unknown`). Mirrors the §8.1 + §8.2 + §8.3 + §8.4 + §8.5 guards' state. |
| `input_text` | `rc_mqtt_broker_url` | Operator-configurable broker URL (default `tcp://core-mosquitto:1883`). |
| `sensor` | `rc_mqtt_discovery_count` | Resolved count of upstream `mqtt` discovery messages received in the last 24 hours. Mirrors the upstream `mqtt` integration's auto-discovery signal. |
| `button` | `rc_mqtt_reconnect_now` | Operator-triggered one-tap reconnect. Flips the upstream `mqtt` integration's connection state + re-publishes the `homeassistant/status` topic + clears the offline guard. |
| `input_boolean` | `rc_mqtt_enabled` | Master enable for the upstream `mqtt` integration's `mqtt.publish` service (default OFF for the recommended safe-default mode). The §8.5 publish-from-HA guard fires whenever a `mqtt.publish` invocation arrives while this toggle is OFF. |
| `input_text` | `rc_mqtt_broker_username` | Operator-configurable broker username (default empty for the recommended local-only mode). The §8.4 broker-auth-error guard fires when this is populated AND the upstream `mqtt` integration reports an authentication failure. |
| `input_boolean` | `rc_mqtt_broker_tls_enabled` | TLS toggle (default FALSE for the recommended local-only mode). The §8.3 broker-tls-error guard fires when this is ON AND the upstream `mqtt` integration reports a TLS handshake failure. |

## The 5 §8 MANDATORY automations

- **§8.1 Broker-offline guard** — fires when `binary_sensor.rc_mqtt_broker_online` flips FALSE. Flips `sensor.rc_mqtt_broker_status` to "offline" + clears `sensor.rc_mqtt_discovery_count` to 0 + fires a critical notification warning the operator that the broker has gone offline.
- **§8.2 Broker-online guard** — fires when `binary_sensor.rc_mqtt_broker_online` flips TRUE. Clears the offline flag + flips `sensor.rc_mqtt_broker_status` to "online" + updates `sensor.rc_mqtt_discovery_count` + fires a notification warning the operator that the broker has come back online.
- **§8.3 Broker-tls-error guard** — fires when `input_boolean.rc_mqtt_broker_tls_enabled` is ON AND the upstream `mqtt` integration reports a TLS handshake failure. Flips `sensor.rc_mqtt_broker_status` to "tls_error" + fires a critical notification warning the operator that the TLS handshake failed.
- **§8.4 Broker-auth-error guard** — fires when the upstream `mqtt` integration reports an authentication failure (wrong username / password). Flips `sensor.rc_mqtt_broker_status` to "auth_error" + fires a critical notification warning the operator that the broker credentials are wrong.
- **§8.5 Publish-from-HA guard** — fires when ANY `script.*` / `automation.*` action tries to call the `mqtt.publish` service while `input_boolean.rc_mqtt_enabled` is OFF. BLOCKS the publish + flips `sensor.rc_mqtt_broker_status` to "disabled" + fires a critical notification warning the operator that publishing is disabled.

## Why tier-b, not tier-a

Tier-a would require a RoamCore-owned pub/sub broker engine + integration code + integration tests against a real pub/sub broker engine bench (a controlled environment with canned fixture responses for broker-offline events + canned fixture responses for broker-tls-error events + canned fixture responses for broker-auth-error events + canned fixture responses for publish-from-HA disabled events + canned fixture responses for broker-online recovery events — all wired together in a controlled environment). We have no operator-side pub/sub broker engine bench on the CI to integration-test against (the bench requires the operator's chosen broker path + canned fixture responses for the FIVE §8 automations). Tier-b is the honest tier: HA core `mqtt` integration + the HACS mosquitto add-on + HA core `input_boolean` + `input_text` + `input_number` + `input_select` + `input_datetime` + `input_button` + `script` helpers + HA core `template:` + HA core `logbook` are all upstream / vendor / HACS code (not RoamCore-owned); the RoamCore wrapper is a thin upstream-entity-aggregation layer + the contract layer + the FIVE §8 MANDATORY automations + the operator-side broker wire-up. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (`docs/catalog/homelab/mqtt.md` — 12-line tier-b claim stub, originally listed "MQTT (the broker everything depends on): A lightweight pub/sub messaging layer that the upstream HA core `mqtt` integration uses for Victron GX + Teltonika + Wican Pro + Shelly + Tasmota + ESPHome + Traccar + 90%+ of IoT devices. (Add recipe + contract + automations + install path)" with no recipe + no contract + no automations + no install path — just a placeholder with an aspirational tier-b claim) is now superseded by this tier-b recipe connection. The legacy tier-b claim was honest-upstream-truth: RoamCore ships no native pub/sub broker engine in the repo today; the picker is honest and ships the contract layer + the recipe + the §8 automations + the operator-side broker wire-up as tier-b.

## Files

- `connection.yml` — the source-of-truth tier-b manifest.
- `__init__.py` — `DOMAIN = "mqtt"` marker for the audit.
- `README.md` — this file.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [`docs/catalog/homelab/mqtt.md`](../../docs/catalog/homelab/mqtt.md)
- Design doc (philosophy + broker wire-up details + tier-a promotion outline): [`docs/design.md`](../../docs/design.md)
- HA core `mqtt` integration (the canonical broker integration umbrella): https://www.home-assistant.io/integrations/mqtt/
- HA core `mqtt` discovery documentation: https://www.home-assistant.io/docs/mqtt/discovery/
- HA core `mqtt` service documentation: https://www.home-assistant.io/docs/mqtt/service/
- HA core `input_boolean` integration (the canonical master-enable helper): https://www.home-assistant.io/integrations/input_boolean/
- HA core `input_text` integration (the canonical broker-URL + username helper): https://www.home-assistant.io/integrations/input_text/
- HA core `input_datetime` integration (the canonical session-expiry helper — not used here, but referenced for the pattern): https://www.home-assistant.io/integrations/input_datetime/
- HA core `input_button` integration (the canonical reconnect-now button helper): https://www.home-assistant.io/integrations/input_button/
- HA core `script:` integration (the canonical `mqtt.publish` wrapper): https://www.home-assistant.io/integrations/script/
- HA core `template:` integration (the canonical broker-online + broker-status + discovery-count derivation): https://www.home-assistant.io/integrations/template/
- HA core `logbook` integration (the canonical audit-log destination for the §8.1 + §8.2 + §8.3 + §8.4 + §8.5 guards): https://www.home-assistant.io/integrations/logbook/
- HACS prerequisites (the canonical install path for the HACS mosquitto add-on): https://hacs.xyz/docs/setup/prerequisites
- Time-atomic (the time-of-day primitives used by the §8.1 broker-offline guard's "broker offline for more than 1 hour" check): `connections/time-atomic/` (Wave 3 #55)
- Remote-access (the VPN primitive used by the §8.5 publish-from-HA guard's owner-identity check): `connections/remote-access/` (Wave 3 #58)
- Approach lights (the dashboard banner pattern used by the §8.2 broker-online guard's "broker back online" notification): `connections/approach-lights/` (Wave 3 #52)
- Fans (the §8.1 broker-offline guard's fan-protection cross-reference): `connections/fans/` (Wave 3 #59)
- Leveling (the §8.1 broker-offline guard's levelling-jack protection cross-reference): `connections/leveling/` (Wave 3 #60)
- Mode (the §8.3 broker-tls-error guard's mode-change cross-reference): `connections/mode/` (Wave 3 #61)
- Demo-mode (the §8.4 broker-auth-error guard's safety-chip pattern): `connections/demo-mode/` (Wave 3 #62)
- Advanced-mode (the §8.5 publish-from-HA guard's confirm-flag pattern): `connections/advanced-mode/` (Wave 3 #63)
- OpenClaw JSON API (the §8.1 broker-offline guard's JSON payload cross-reference): `connections/openclaw-api/` (Wave 3 #64)
- Agent actions allowlist (the §8.5 publish-from-HA guard's kill-switch cross-reference): `connections/agent-actions-allowlist/` (Wave 3 #65)
- RoamCore entity naming: [`docs/reference/rc-entity-naming.md`](../../docs/reference/rc-entity-naming.md) (the `mqtt` subsystem was added by this slice)