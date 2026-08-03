"""MQTT — vendor-neutral lightweight pub/sub messaging layer that the
upstream HA core `mqtt` integration uses for Victron GX + Teltonika +
Wican Pro + Shelly + Tasmota + ESPHome + Traccar + 90%+ of IoT
devices — tier-b recipe connection.

Note on upstream wiring: tier-b connections don't ship a
RoamCore-owned operator-wired setup flow (a RoamCore
operator-wired wizard); instead, each path uses the
upstream integration's GUI flow (the HA core `mqtt`
integration exposes an operator-wired setup flow + GUI flow
for adding the upstream `mqtt` broker connection to the
HA core; the HA core `input_boolean` + `input_text` +
`input_number` + `input_select` + `input_datetime` +
`input_button` + `script` helpers + the HA core `template:`
sensor wrapper + the HA core `logbook` integration + the
HACS mosquitto add-on + the upstream `script:` integration
all expose their own operator-wired setup flow + GUI flow).

This module is a marker-only stub. Tier-b connections don't
ship native HA integration code; they publish a recipe
(docs/recipe.md) that walks the operator through installing
the HACS mosquitto add-on + the upstream HA core `mqtt`
integration + wiring the FIVE-step operator-pickable broker
flow:

  - Pick the broker path — the operator chooses ONE of the
    THREE upstream broker paths documented in the recipe:
    Path A — HACS mosquitto add-on (recommended for most
    operators; local-only + auto-starts on HA boot +
    auto-configures the HA core `mqtt` integration to point
    at the local broker; no vendor-specific credentials
    required); Path B — external / cloud broker (for
    operators who already run a broker off-box; the recipe
    documents how to wire the upstream HA core `mqtt`
    integration to point at the external broker + how to
    secure the connection with username / password / TLS);
    Path C — local container / VM broker (for operators who
    want a Docker / Podman / LXC / VM broker on the same
    Proxmox box or on a separate mini-PC; the recipe
    documents the vendor-neutral generic broker wire-up).

  - Mount the broker credentials — the operator configures
    `input_text.rc_mqtt_broker_url` (default
    `tcp://core-mosquitto:1883`) + the optional
    `input_text.rc_mqtt_broker_username` +
    `input_text.rc_mqtt_broker_password` +
    `input_boolean.rc_mqtt_broker_tls_enabled` (default
    FALSE for the recommended local-only mode). The §4
    operator flow walks the operator through populating the
    broker credentials + confirming the broker URL is
    reachable.

  - Confirm the broker is online — the operator confirms
    `binary_sensor.rc_mqtt_broker_online` reads TRUE (the
    §8.1 broker-offline guard's canonical safety chip).
    The §5 operator flow walks the operator through
    confirming the broker is online before the first
    publish.

  - Enable + start publishing — the operator flips
    `input_boolean.rc_mqtt_enabled` ON (the upstream HA
    core `mqtt` integration's master enable; the upstream
    `mqtt.publish` service exposes a GUI flow for the
    operator to publish from the HA UI under Developer
    Tools → Services). The `sensor.rc_mqtt_broker_status`
    surfaces "online" / "offline" / "tls_error" /
    "auth_error" / "unknown".

  - Audit + revert — every broker connection state change
    + every `mqtt.publish` service call + every
    `mqtt.publish` event received writes an entry to
    `sensor.rc_mqtt_discovery_count` (the resolved count
    of upstream `mqtt` discovery messages received in the
    last 24 hours) + the HA core `logbook` (the canonical
    audit-log destination for Home Assistant automations).
    The operator can revert at any time via
    `button.rc_mqtt_reconnect_now` (the operator-triggered
    one-tap reconnect — flips the upstream `mqtt`
    integration's connection state + re-publishes the
    `homeassistant/status` topic + clears the offline
    guard).

The umbrella publishes the resulting data via the upstream
HA core `mqtt` integration (since 2022.x — exposes the
canonical pub/sub messaging layer for Home Assistant
automations) + the HA core `input_boolean` + `input_text` +
`input_number` + `input_select` + `input_datetime` +
`input_button` + `script` helper entities (since 2022.x —
have exposed the standard `input_boolean.toggle` +
`input_text.set_value` + `input_number.set_value` +
`input_select.select_option` + `input_datetime.set_datetime`
+ `input_button.press` + `script.*` services + the
`input_boolean` / `input_text` / `input_number` / `select` /
`input_datetime` / `sensor` / `binary_sensor` / `button`
domain entities) + the HA core `template:` sensor wrapper
(since 2022.x — wraps any upstream sensor state into a
derived `sensor.*` entity) + the HA core `logbook`
integration (since 2022.x — the canonical audit-log
destination for Home Assistant automations) + the HACS
mosquitto add-on (the canonical upstream vendor-neutral
local broker), then publishes the RoamCore broker contract
tiles on top (the 8 contract entities documented in
connection.yml — 1 binary_sensor mqtt_broker_online + 1
sensor mqtt_broker_status + 1 input_text mqtt_broker_url +
1 sensor mqtt_discovery_count + 1 button mqtt_reconnect_now
+ 1 input_boolean mqtt_enabled + 1 input_text
mqtt_broker_username + 1 input_boolean mqtt_broker_tls_enabled
= 8 contract entities).

The audit + boundary CI can detect an `mqtt/` folder that
claims to be a connection via the `DOMAIN` constant
exported here. The wizard reads the manifest + recipe at
runtime.

The real per-operator broker affordance path is:

    Operator-side choice of the FIVE-step flow (Pick the
        broker path -> Mount the broker credentials ->
        Confirm the broker is online -> Enable + start
        publishing -> Audit + revert)
        -> upstream entities (the HA core
           `binary_sensor.rc_mqtt_broker_online` for the
           upstream `mqtt` integration's connection state —
           derived via the HA core `template:`
           binary_sensor wrapper since 2022.x; the HA core
           `sensor.rc_mqtt_broker_status` for the resolved
           connection status — derived via the HA core
           `template:` sensor wrapper since 2022.x; the HA
           core `input_text.rc_mqtt_broker_url` for the
           broker URL — the operator edits via the HA UI
           under Settings → Helpers; the HA core
           `sensor.rc_mqtt_discovery_count` for the
           resolved count of upstream `mqtt` discovery
           messages received in the last 24 hours —
           derived via the HA core `template:` sensor
           wrapper; the HA core
           `button.rc_mqtt_reconnect_now` for the
           operator-triggered one-tap reconnect — the
           `input_button:` domain entity fires an
           automation reconnecting the upstream `mqtt`
           integration; the HA core
           `input_boolean.rc_mqtt_enabled` for the master
           enable — operator flips via the HA UI under
           Settings → Helpers; the HA core
           `input_text.rc_mqtt_broker_username` for the
           broker username — operator edits via the HA UI
           under Settings → Helpers; the HA core
           `input_boolean.rc_mqtt_broker_tls_enabled`
           for the TLS toggle — operator flips via the HA
           UI under Settings → Helpers)
        -> upstream signals (the operator's chosen broker
           path — Path A HACS mosquitto add-on, Path B
           external / cloud broker, or Path C local
           container / VM broker; the operator's chosen
           broker credentials — username + password + TLS
           toggle; the upstream `mqtt` integration's
           auto-discovery of upstream sensors + binary
           sensors + switches + lights + covers via the
           canonical upstream `mqtt` discovery protocol
           since 2022.x)
        -> RoamCore contract layer (HA core `template:`
           sensor + binary_sensor + the operator's
           `input_boolean` / `input_text` / `input_number`
           / `input_select` / `input_datetime` /
           `input_button` for the contract tiles + the
           upstream `mqtt` integration for the
           auto-discovery signal + the `script:`
           integration for the upstream `mqtt.publish`
           wrapper + the `logbook` integration for the
           §8.3 audit-log entry)
        -> dashboard tiles + OpenClaw queries
            ("is the broker online?",
             "what is the broker status?",
             "what is the broker url?",
             "how many upstream mqtt devices are
              discovered?",
             "reconnect the broker now",
             "is the broker enabled?",
             "what is the broker username?",
             "is the broker tls enabled?")

    Safety interlocks (the recipe is the contract layer;
    the automation wrappers are documented in §8):
        -> The RoamCore broker-offline guard is the §8.1
           automation that fires when
           `binary_sensor.rc_mqtt_broker_online` flips
           FALSE; the automation flips
           `binary_sensor.rc_mqtt_broker_online` to FALSE
           + flips `sensor.rc_mqtt_broker_status` to
           "offline" + clears the discovery_count to 0 +
           fires a critical notification warning the
           operator that the broker has gone offline.
        -> The RoamCore broker-online guard is the §8.2
           automation that fires when
           `binary_sensor.rc_mqtt_broker_online` flips
           TRUE; the automation clears the offline flag +
           flips `sensor.rc_mqtt_broker_status` to
           "online" + updates the discovery_count +
           fires a notification warning the operator that
           the broker has come back online.
        -> The RoamCore broker-tls-error guard is the
           §8.3 automation that fires when
           `binary_boolean.rc_mqtt_broker_tls_enabled` is
           ON AND the upstream `mqtt` integration reports
           a TLS handshake failure; the automation flips
           `sensor.rc_mqtt_broker_status` to "tls_error"
           + fires a critical notification warning the
           operator that the TLS handshake failed.
        -> The RoamCore broker-auth-error guard is the
           §8.4 automation that fires when the upstream
           `mqtt` integration reports an authentication
           failure (wrong username / password); the
           automation flips
           `sensor.rc_mqtt_broker_status` to "auth_error"
           + fires a critical notification warning the
           operator that the broker credentials are
           wrong.
        -> The RoamCore publish-from-HA guard is the
           §8.5 automation that fires when ANY
           `script.*` / `automation.*` action tries to
           call the `mqtt.publish` service while
           `input_boolean.rc_mqtt_enabled` is OFF; the
           automation BLOCKS the publish + flips
           `sensor.rc_mqtt_broker_status` to "disabled"
           + fires a critical notification warning the
           operator that publishing is disabled.

The audit + boundary CI can detect this module via the
`DOMAIN = "mqtt"` constant; the wizard reads the manifest +
recipe at runtime.

The umbrella ships no RoamCore-owned pub/sub engine; the
recipe is the contract layer + the §8 MANDATORY automations
+ the operator-facing affordance surfaces.

The legacy catalog page (now superseded by this slice) lives
at `docs/catalog/homelab/mqtt.md` — a 12-line tier-b claim
stub, originally listed "MQTT (the broker everything
depends on): A lightweight pub/sub messaging layer that
the upstream HA core `mqtt` integration uses for Victron
GX + Teltonika + Wican Pro + Shelly + Tasmota + ESPHome +
Traccar + 90%+ of IoT devices. (Add recipe + contract +
automations + install path)" with no recipe + no contract
+ no automations + no install path — just a placeholder
with an aspirational tier-b claim. The picker is honest
and ships the contract layer + the recipe + the §8
automations + the operator-side broker wire-up as tier-b.
The legacy doc now carries a SUPERSEDED banner pointing at
this connection.
"""

from __future__ import annotations

DOMAIN = "mqtt"