# MQTT — full howto (RoamCore vendor-neutral lightweight pub/sub messaging layer for IoT devices — the broker everything depends on)

This recipe is the canonical howto for the
`connections/mqtt/` tier-b recipe connection (Wave 3
#34). It walks the operator through picking ONE of the
THREE upstream broker paths (Path A HACS mosquitto
add-on, Path B external / cloud broker, Path C local
container / VM broker) + mounting the broker credentials
(`input_text.rc_mqtt_broker_url` default
`tcp://core-mosquitto:1883`; `input_text.rc_mqtt_broker_username`;
`input_boolean.rc_mqtt_broker_tls_enabled`) + confirming
the broker is online (`binary_sensor.rc_mqtt_broker_online`
reads TRUE) + enabling + starting publishing
(`input_boolean.rc_mqtt_enabled` flips ON; the upstream
`mqtt.publish` service exposes a GUI flow under
Developer Tools → Services) + auditing (the HA core
`logbook` integration is the canonical audit-log
destination; `sensor.rc_mqtt_discovery_count` mirrors the
upstream `mqtt` integration's auto-discovery signal) +
reverting at any time via `button.rc_mqtt_reconnect_now`
(the operator-triggered one-tap reconnect — flips the
upstream `mqtt` integration's connection state +
re-publishes the `homeassistant/status` topic + clears
the offline guard).

The recipe assumes the operator has at least the upstream
HA core `mqtt` integration auto-installed (every HA
install has it since 2022.x) + the HACS mosquitto add-on
installed (Path A — recommended) or the external / cloud
broker reachable (Path B) or the local container / VM
broker running (Path C) + the broker URL configured via
`input_text.rc_mqtt_broker_url` (default
`tcp://core-mosquitto:1883`). If the operator has the
upstream HA core `mqtt` integration + a reachable broker
+ the broker URL configured, the recipe starts at §4
Mount the broker credentials + walks through the broker
online guard + the enable + the audit log before the §7
contract layer.

## §1 What is MQTT in RoamCore?

MQTT — vendor-neutral lightweight pub/sub messaging layer
that the upstream HA core `mqtt` integration uses for
Victron GX + Teltonika + Wican Pro + Shelly + Tasmota +
ESPHome + Traccar + 90%+ of IoT devices — is the
homelab-category umbrella for "the broker everything
depends on". The single `binary_sensor.rc_mqtt_broker_online`
tile is the operator's canonical safety chip (TRUE when
the upstream `mqtt` integration reports a connected
state; should ALWAYS be TRUE when the upstream `mqtt`
integration is healthy; should NEVER be TRUE
unexpectedly); the `sensor.rc_mqtt_broker_status` is the
resolved broker connection status (surfaces "online" /
"offline" / "tls_error" / "auth_error" / "disabled" /
"unknown" in the dashboard; mirrors the §8.1 + §8.2 +
§8.3 + §8.4 + §8.5 guards' state); the
`input_text.rc_mqtt_broker_url` is the
operator-configurable broker URL (default
`tcp://core-mosquitto:1883` for the recommended Path A
HACS mosquitto add-on); the `sensor.rc_mqtt_discovery_count`
is the resolved count of upstream `mqtt` discovery
messages received in the last 24 hours (mirrors the
upstream `mqtt` integration's auto-discovery signal); the
`button.rc_mqtt_reconnect_now` is the operator-triggered
one-tap reconnect (flips the upstream `mqtt`
integration's connection state + re-publishes the
`homeassistant/status` topic + clears the offline guard);
the `input_boolean.rc_mqtt_enabled` is the master enable
for the upstream `mqtt` integration's `mqtt.publish`
service (default OFF for the recommended safe-default
mode; the §8.5 publish-from-HA guard fires whenever a
`mqtt.publish` invocation arrives while this toggle is
OFF); the `input_text.rc_mqtt_broker_username` is the
operator-configurable broker username (default empty for
the recommended local-only mode; the §8.4 broker-auth-
error guard fires when this is populated AND the upstream
`mqtt` integration reports an authentication failure);
the `input_boolean.rc_mqtt_broker_tls_enabled` is the
TLS toggle (default FALSE for the recommended local-only
mode; the §8.3 broker-tls-error guard fires when this is
ON AND the upstream `mqtt` integration reports a TLS
handshake failure).

The broker-online tile
(`binary_sensor.rc_mqtt_broker_online`) is the operator's
canonical safety chip — the recipe surfaces a green
"broker online" chip when the upstream `mqtt` integration
reports a connected state + a red "broker offline" chip
when the upstream `mqtt` integration reports a
disconnected state. The §8.1 broker-offline guard fires
whenever the broker-online chip flips FALSE; the §8.2
broker-online guard fires whenever the broker-online chip
flips TRUE.

The broker-status tile
(`sensor.rc_mqtt_broker_status`) is the operator's
resolved broker connection status — the recipe surfaces
"online" / "offline" / "tls_error" / "auth_error" /
"disabled" / "unknown" in the dashboard. The §8.1
broker-offline guard sets this to "offline"; the §8.2
broker-online guard sets this to "online"; the §8.3
broker-tls-error guard sets this to "tls_error"; the §8.4
broker-auth-error guard sets this to "auth_error"; the
§8.5 publish-from-HA guard sets this to "disabled".

The broker-url tile
(`input_text.rc_mqtt_broker_url`) is the operator's
broker URL — the recipe defaults to
`tcp://core-mosquitto:1883` because that's the canonical
HACS mosquitto add-on URL (the HACS mosquitto add-on
auto-starts on HA boot + auto-configures the upstream HA
core `mqtt` integration to point at this URL); the
operator may override the URL if they choose Path B
(external / cloud broker) or Path C (local container /
VM broker).

The discovery-count tile
(`sensor.rc_mqtt_discovery_count`) is the operator's
resolved count of upstream `mqtt` discovery messages
received in the last 24 hours — the recipe surfaces the
count as "47 devices discovered in the last 24h" in the
dashboard; mirrors the upstream `mqtt` integration's
auto-discovery signal (the upstream `mqtt` integration
auto-discovers upstream sensors + binary_sensors +
switches + lights + covers via the canonical upstream
`mqtt` discovery protocol since 2022.x).

The reconnect-now tile (`button.rc_mqtt_reconnect_now`)
is the operator's emergency reconnect — fires an
automation flipping the upstream `mqtt` integration's
connection state + re-publishing the
`homeassistant/status` topic + clearing the offline
guard. Surfaces a "broker reconnecting..." toast.

The enabled tile (`input_boolean.rc_mqtt_enabled`) is
the operator's master enable for the upstream `mqtt`
integration's `mqtt.publish` service — the recipe
defaults to OFF because publishing should never be
permitted unless the operator explicitly enables it (the
§8.5 publish-from-HA guard fires whenever a
`mqtt.publish` invocation arrives while this toggle is
OFF).

The broker-username tile
(`input_text.rc_mqtt_broker_username`) is the operator's
broker username — the recipe defaults to empty because
the recommended Path A HACS mosquitto add-on does NOT
require authentication for local-only use; the operator
may populate this if they choose Path B (external / cloud
broker) or Path C (local container / VM broker) with
authentication enabled.

The tls-enabled tile
(`input_boolean.rc_mqtt_broker_tls_enabled`) is the
operator's TLS toggle — the recipe defaults to FALSE
because the recommended Path A HACS mosquitto add-on
does NOT require TLS for local-only use; the operator may
flip this ON if they choose Path B (external / cloud
broker) or Path C (local container / VM broker) with TLS
enabled.

The audit-log entry (the §8.1 broker-offline guard + the
§8.2 broker-online guard + the §8.3 broker-tls-error
guard + the §8.4 broker-auth-error guard + the §8.5
publish-from-HA guard) is the operator-facing "when did
the broker last change state?" affordance — the §8
automations write entries to the HA core `logbook`
integration (the canonical audit-log destination for Home
Assistant automations) + the
`binary_sensor.rc_mqtt_broker_online` + the
`sensor.rc_mqtt_broker_status` + the
`sensor.rc_mqtt_discovery_count` contract tiles
(mirrors the upstream `mqtt` integration's connection
state).

The recipe covers the FIVE-step operator flow (Pick the
broker path + Mount the broker credentials + Confirm the
broker is online + Enable + start publishing + Audit +
revert) + the FIVE §8 MANDATORY automations + the 8
`rc_mqtt_*` contract tiles + the §9 troubleshooting
entries + the §10 privacy section + the §11 tier-a
promotion outline + the §12 files + the §13 cross-
references.

## §2 Prerequisites

### §2.1 Universal prerequisites

The operator must have:

- A running Home Assistant installation (HA Core
  2022.6+; the upstream `mqtt` integration + the
  `input_boolean` + `input_text` + `input_datetime` +
  `input_button` + `select` helpers + `template:` +
  `logbook` + `script:` integration are all upstream
  since 2022.x).
- The upstream HA core `mqtt` integration auto-installed
  (every HA install has it since 2022.x).
- The HACS prerequisites installed (for Path A; the
  HACS mosquitto add-on is the canonical upstream
  vendor-neutral local broker add-on; install HACS
  first per https://hacs.xyz/docs/setup/prerequisites).
- A reachable broker (Path A HACS mosquitto add-on,
  Path B external / cloud broker, or Path C local
  container / VM broker).
- Read access to the operator's broker URL via
  `input_text.rc_mqtt_broker_url` (default
  `tcp://core-mosquitto:1883`).

### §2.2 Upstream signal prerequisites

The operator must wire:

- `binary_sensor.rc_mqtt_broker_online` (the §7
  canonical safety chip + the §8.1 broker-offline
  guard's target).
- `sensor.rc_mqtt_broker_status` (the §7 resolved
  broker connection status).
- `input_text.rc_mqtt_broker_url` (the operator-
  configurable broker URL; default
  `tcp://core-mosquitto:1883`).
- `sensor.rc_mqtt_discovery_count` (the §7 resolved
  count of upstream `mqtt` discovery messages received
  in the last 24 hours).
- `button.rc_mqtt_reconnect_now` (the §7 operator-
  triggered one-tap reconnect).
- `input_boolean.rc_mqtt_enabled` (the §7 master enable
  for the upstream `mqtt` integration's `mqtt.publish`
  service; default OFF for the recommended safe-default
  mode).
- `input_text.rc_mqtt_broker_username` (the §7
  operator-configurable broker username; default empty
  for the recommended local-only mode).
- `input_boolean.rc_mqtt_broker_tls_enabled` (the §7
  TLS toggle; default FALSE for the recommended
  local-only mode).

### §2.3 Optional cross-references (recommended)

The operator may also wire:

- The time-atomic Wave 3 #55 connection's time-of-day
  primitives for the §8.1 broker-offline guard's
  "broker offline for more than 1 hour" check.
- The remote-access Wave 3 #58 connection's VPN
  primitive for the §8.5 publish-from-HA guard's
  owner-identity check.
- The approach lights Wave 3 #52 connection's dashboard
  banner pattern for the §8.2 broker-online guard's
  "broker back online" notification.
- The fans Wave 3 #59 connection's fan-protection cross-
  reference for the §8.1 broker-offline guard's fan
  protection.
- The leveling Wave 3 #60 connection's levelling-jack
  protection cross-reference for the §8.1 broker-offline
  guard's levelling-jack protection.
- The mode Wave 3 #61 connection's mode-change cross-
  reference for the §8.3 broker-tls-error guard.
- The demo-mode Wave 3 #62 connection's safety-chip
  pattern for the §8.4 broker-auth-error guard.
- The advanced-mode Wave 3 #63 connection's confirm-flag
  pattern for the §8.5 publish-from-HA guard.
- The openclaw-api Wave 3 #64 connection's JSON payload
  cross-reference for the §8.1 broker-offline guard.
- The agent-actions-allowlist Wave 3 #65 connection's
  kill-switch cross-reference for the §8.5 publish-from-
  HA guard.

## §3 Pick the broker path

The recipe documents THREE upstream broker paths. The
operator picks ONE based on their setup.

### §3.1 Path A — HACS mosquitto add-on (recommended)

Path A is the recommended path for most operators. The
HACS mosquitto add-on is the canonical upstream
vendor-neutral local broker add-on; it auto-starts on HA
boot + auto-configures the upstream HA core `mqtt`
integration to point at the local broker; no
vendor-specific credentials required.

Steps:

1. Install HACS (https://hacs.xyz/docs/setup/prerequisites).
2. Open HACS → Add-ons → Search for "Mosquitto broker"
   → Install.
3. Configure the HACS mosquitto add-on with the default
   settings (port 1883 + no authentication + no TLS for
   the recommended local-only mode).
4. Start the HACS mosquitto add-on + check the add-on
   logs for the "mosquitto broker started" line.
5. The upstream HA core `mqtt` integration will
   auto-detect the HACS mosquitto add-on at
   `tcp://core-mosquitto:1883` + auto-configure the
   connection.

### §3.2 Path B — External / cloud broker

Path B is for operators who already run a broker
off-box (e.g. a cloud-hosted broker for multi-site
deployments; a separate mini-PC broker; a VPS broker).

Steps:

1. Provision the external / cloud broker per the
   upstream provider's docs.
2. Note the broker URL + the username + the password +
   the TLS settings.
3. Configure `input_text.rc_mqtt_broker_url` to the
   external / cloud broker's URL (e.g.
   `mqtts://broker.example.com:8883`).
4. Configure `input_text.rc_mqtt_broker_username` to
   the external / cloud broker's username.
5. Configure the password via `secrets.yaml` (the
   recipe does NOT store the password in
   `input_text.*` for security reasons).
6. Configure `input_boolean.rc_mqtt_broker_tls_enabled`
   to TRUE if the external / cloud broker requires TLS.
7. The upstream HA core `mqtt` integration will
   auto-configure the connection to the external / cloud
   broker on the next HA restart.

### §3.3 Path C — Local container / VM broker

Path C is for operators who want a Docker / Podman / LXC /
VM broker on the same Proxmox box or on a separate
mini-PC. The recipe documents the vendor-neutral generic
broker wire-up.

Steps:

1. Provision the Docker / Podman / LXC / VM broker per
   the upstream provider's docs.
2. Note the broker URL + the username + the password +
   the TLS settings.
3. Configure `input_text.rc_mqtt_broker_url` to the
   local container / VM broker's URL (e.g.
   `tcp://192.168.1.100:1883`).
4. Configure `input_text.rc_mqtt_broker_username` to
   the local container / VM broker's username (if any).
5. Configure the password via `secrets.yaml` (if any).
6. Configure `input_boolean.rc_mqtt_broker_tls_enabled`
   to TRUE if the local container / VM broker requires
   TLS.
7. The upstream HA core `mqtt` integration will
   auto-configure the connection to the local container
   / VM broker on the next HA restart.

## §4 Mount the broker credentials

The broker credentials are mounted via the operator-facing
contract tiles. The recipe defaults to the canonical HACS
mosquitto add-on URL + empty username + FALSE TLS for
the recommended local-only mode.

### §4.1 Configure the broker URL

The operator configures `input_text.rc_mqtt_broker_url`
to point at the broker:

```yaml
input_text:
  rc_mqtt_broker_url:
    name: RC MQTT Broker URL
    initial: "tcp://core-mosquitto:1883"
    icon: mdi:server-network
```

The operator may override the URL based on their chosen
path (Path A: `tcp://core-mosquitto:1883`; Path B:
`mqtts://broker.example.com:8883`; Path C:
`tcp://192.168.1.100:1883`).

### §4.2 Configure the broker username

The operator configures `input_text.rc_mqtt_broker_username`
to the broker's username (if any):

```yaml
input_text:
  rc_mqtt_broker_username:
    name: RC MQTT Broker Username
    initial: ""
    icon: mdi:account-outline
```

The operator may leave this empty for the recommended
local-only mode (Path A) or populate this for Path B /
Path C with authentication enabled.

### §4.3 Configure the TLS toggle

The operator configures `input_boolean.rc_mqtt_broker_tls_enabled`
based on whether the broker requires TLS:

```yaml
input_boolean:
  rc_mqtt_broker_tls_enabled:
    name: RC MQTT Broker TLS Enabled
    icon: mdi:lock-outline
    initial: false
```

The operator may flip this ON for Path B (external / cloud
broker with TLS) or Path C (local container / VM broker
with TLS).

## §5 Confirm the broker is online

The broker-online guard is the operator's canonical
safety chip. The operator MUST confirm the broker is
online before the first publish.

### §5.1 Confirm the broker-online chip

The `binary_sensor.rc_mqtt_broker_online` tile is a
`template:` binary_sensor (since 2022.x) that reads from
the upstream `mqtt` integration's connection state. The
operator MUST confirm the tile reads TRUE before the
first publish.

### §5.2 What the broker-online chip does

When the broker-online chip is TRUE:

- `sensor.rc_mqtt_broker_status` reads "online".
- `sensor.rc_mqtt_discovery_count` increments as
  upstream `mqtt` discovery messages arrive.
- The §8.1 broker-offline guard does NOT fire.
- The §8.5 publish-from-HA guard allows `mqtt.publish`
  invocations (when `input_boolean.rc_mqtt_enabled` is
  also ON).

When the broker-online chip is FALSE:

- `sensor.rc_mqtt_broker_status` reads "offline".
- `sensor.rc_mqtt_discovery_count` is 0.
- The §8.1 broker-offline guard fires + writes an
  audit-log entry + flips
  `binary_sensor.rc_mqtt_broker_online` to FALSE.
- The §8.5 publish-from-HA guard BLOCKS `mqtt.publish`
  invocations.

### §5.3 Wiring the broker-online chip

The broker-online chip is wired via the HA core
`template:` binary_sensor wrapper:

```yaml
template:
  - binary_sensor:
      - name: "RC MQTT Broker Online"
        unique_id: rc_mqtt_broker_online
        device_class: connectivity
        icon: mdi:server-network
        state: >
          {{ is_state('mqtt.broker', 'connected') }}
```

## §6 Enable + start publishing

The operator flips `input_boolean.rc_mqtt_enabled` ON
when ready to publish.

### §6.1 Configure the master enable

The operator configures `input_boolean.rc_mqtt_enabled`:

```yaml
input_boolean:
  rc_mqtt_enabled:
    name: RC MQTT Enabled
    icon: mdi:publish
    initial: false
```

The recipe defaults to OFF because publishing should never
be permitted unless the operator explicitly enables it.

### §6.2 Publish a test topic

The operator publishes a test topic via Developer Tools
→ Services → `mqtt.publish`:

```yaml
service: mqtt.publish
data:
  topic: "homeassistant/binary_sensor/roamcore_test/availability"
  payload: "online"
  qos: 1
  retain: true
```

The operator MUST confirm the publish fires + the
upstream `mqtt` integration reports the publish succeeded
+ `sensor.rc_mqtt_discovery_count` increments.

### §6.3 Configure the discovery-count tile

The `sensor.rc_mqtt_discovery_count` tile is a
`template:` sensor (since 2022.x) that reads from the
upstream `mqtt` integration's discovery event log:

```yaml
template:
  - sensor:
      - name: "RC MQTT Discovery Count"
        unique_id: rc_mqtt_discovery_count
        icon: mdi:counter
        state: >
          {{ states.mqtt | selectattr('attributes.discovery', 'defined') | list | length }}
```

The operator MAY wire the discovery-count tile to a more
sophisticated counter (e.g. rolling 24-hour count) — the
recipe ships the basic count for v1.

## §7 RoamCore contract entities

The 8 `rc_mqtt_*` contract tiles are the canonical
RoamCore surface for the broker umbrella. The tiles are
vendor-neutral — no Victron / SeeLevel / Garnet / Mopeka /
Renogy / Starlink / Peplink / Teltonika / Unifi / Ubiquiti
/ OpenAI / Anthropic / Claude / GPT / ChatGPT / LLM /
conversation / MQTT / webhook / REST / API / HTTP / HTTPS
/ Companion / ESPHome / phone / GPS / accelerometer /
iPhone / iOS / Android / Samsung / Pixel / OnePlus /
Xiaomi / Huawei / input_boolean / input_text /
input_number / input_select / input_datetime /
input_button / script / template / logbook / Z-Wave /
Zigbee / ZHA / Deconz / Tasmota / Shelly / Sonoff /
ESP32 / ESP8266 / Wi-Fi / BLE / Bluetooth names leak into
the tile ids.

### §7.1 The 8 `rc_mqtt_*` contract tiles

- `binary_sensor.rc_mqtt_broker_online` — TRUE when the
  upstream `mqtt` integration reports a connected state.
  The tile is a `template:` binary_sensor (since 2022.x)
  that reads from the upstream `mqtt` integration's
  connection state.
  ```yaml
  template:
    - binary_sensor:
        - name: "RC MQTT Broker Online"
          unique_id: rc_mqtt_broker_online
          device_class: connectivity
          icon: mdi:server-network
          state: >
            {{ is_state('mqtt.broker', 'connected') }}
  ```

- `sensor.rc_mqtt_broker_status` — resolved broker
  connection status (`online` / `offline` / `tls_error` /
  `auth_error` / `disabled` / `unknown`). The tile is a
  `template:` sensor (since 2022.x) that reads from the
  upstream `mqtt` integration's connection state + the
  §8.1 + §8.2 + §8.3 + §8.4 + §8.5 guards' state.
  ```yaml
  template:
    - sensor:
        - name: "RC MQTT Broker Status"
          unique_id: rc_mqtt_broker_status
          icon: mdi:server-network-outline
          state: >
            {% set broker_online = is_state('binary_sensor.rc_mqtt_broker_online', 'on') %}
            {% set tls_enabled = is_state('input_boolean.rc_mqtt_broker_tls_enabled', 'on') %}
            {% set enabled = is_state('input_boolean.rc_mqtt_enabled', 'on') %}
            {% if not enabled %}
              disabled
            {% elif not broker_online %}
              offline
            {% else %}
              online
            {% endif %}
  ```

- `input_text.rc_mqtt_broker_url` — operator-configurable
  broker URL (default `tcp://core-mosquitto:1883`). The
  tile is an `input_text:` domain entity (since 2022.x)
  that the operator's chosen broker-path UI sets.
  ```yaml
  input_text:
    rc_mqtt_broker_url:
      name: RC MQTT Broker URL
      initial: "tcp://core-mosquitto:1883"
      icon: mdi:server-network
  ```

- `sensor.rc_mqtt_discovery_count` — resolved count of
  upstream `mqtt` discovery messages received in the
  last 24 hours. The tile is a `template:` sensor (since
  2022.x) that reads from the upstream `mqtt`
  integration's discovery event log.
  ```yaml
  template:
    - sensor:
        - name: "RC MQTT Discovery Count"
          unique_id: rc_mqtt_discovery_count
          icon: mdi:counter
          state: >
            {{ states.mqtt | selectattr('attributes.discovery', 'defined') | list | length }}
          unit_of_measurement: "devices"
  ```

- `button.rc_mqtt_reconnect_now` — operator-triggered
  one-tap reconnect. The button is an `input_button:`
  domain entity (since 2022.x) that fires an automation
  reconnecting the upstream `mqtt` integration.
  ```yaml
  input_button:
    rc_mqtt_reconnect_now:
      name: RC MQTT Reconnect Now
      icon: mdi:restart
  ```

- `input_boolean.rc_mqtt_enabled` — master enable for
  the upstream `mqtt` integration's `mqtt.publish`
  service (default OFF for the recommended safe-default
  mode). The tile is an `input_boolean:` domain entity
  (since 2022.x) that the operator's chosen master-enable
  UI flips.
  ```yaml
  input_boolean:
    rc_mqtt_enabled:
      name: RC MQTT Enabled
      icon: mdi:publish
      initial: false
  ```

- `input_text.rc_mqtt_broker_username` — operator-
  configurable broker username (default empty for the
  recommended local-only mode). The tile is an
  `input_text:` domain entity (since 2022.x) that the
  operator's chosen username UI sets.
  ```yaml
  input_text:
    rc_mqtt_broker_username:
      name: RC MQTT Broker Username
      initial: ""
      icon: mdi:account-outline
  ```

- `input_boolean.rc_mqtt_broker_tls_enabled` — TLS
  toggle (default FALSE for the recommended local-only
  mode). The tile is an `input_boolean:` domain entity
  (since 2022.x) that the operator's chosen TLS UI
  flips.
  ```yaml
  input_boolean:
    rc_mqtt_broker_tls_enabled:
      name: RC MQTT Broker TLS Enabled
      icon: mdi:lock-outline
      initial: false
  ```

### §7.2 Script-runner wrappers

The `mqtt.publish` wrapper is an upstream `script:`
integration script-runner wrapper that the operator wires
in `homeassistant/scripts.yaml` (or in a dedicated
RoamCore-side
`homeassistant/packages/roamcore_mqtt_scripts.yaml`
file).

```yaml
script:
  roamcore_mqtt_publish:
    alias: "RoamCore: MQTT Publish"
    description: >-
      Publish a message via the upstream `mqtt.publish`
      service. Requires input_boolean.rc_mqtt_enabled to
      be ON AND binary_sensor.rc_mqtt_broker_online to
      be TRUE.
    sequence:
      - choose:
          - conditions:
              - condition: state
                entity_id: input_boolean.rc_mqtt_enabled
                state: "off"
            sequence:
              - service: logbook.log
                data:
                  name: "RoamCore MQTT"
                  message: >-
                    MQTT publish BLOCKED: master enable is
                    OFF.
                  entity_id: input_boolean.rc_mqtt_enabled
              - stop: "MQTT master enable is OFF"
      - service: mqtt.publish
        data:
          topic: "{{ topic | default('homeassistant/binary_sensor/roamcore_default/state') }}"
          payload: "{{ payload | default('online') }}"
          qos: "{{ qos | default(0) }}"
          retain: "{{ retain | default(false) }}"
```

## §8 Automations (MANDATORY before first use)

### §8.1 Broker-offline guard

The automation fires when
`binary_sensor.rc_mqtt_broker_online` flips FALSE. The
automation flips `sensor.rc_mqtt_broker_status` to
"offline" + clears `sensor.rc_mqtt_discovery_count` to
0 + fires a critical notification warning the operator
that the broker has gone offline.

```yaml
automation:
  - alias: "RoamCore: MQTT — broker-offline guard"
    description: >-
      Fires when the broker-online chip flips FALSE.
      Flips the broker-status to "offline" + clears the
      discovery count + fires a critical notification.
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_mqtt_broker_online
        to: "off"
    action:
      - service: logbook.log
        data:
          name: "RoamCore MQTT"
          message: >-
            Broker OFFLINE: connection to {{ states('input_text.rc_mqtt_broker_url') }}
            lost.
          entity_id: binary_sensor.rc_mqtt_broker_online
      - service: persistent_notification.create
        data:
          title: "RoamCore MQTT: broker offline"
          message: >-
            The broker at
            {{ states('input_text.rc_mqtt_broker_url') }}
            has gone offline. Check the broker service
            + the network. Press
            binary_sensor.rc_mqtt_reconnect_now to retry.
          notification_id: roamcore_mqtt_broker_offline
```

### §8.2 Broker-online guard

The automation fires when
`binary_sensor.rc_mqtt_broker_online` flips TRUE. The
automation clears the offline flag + flips
`sensor.rc_mqtt_broker_status` to "online" + updates
`sensor.rc_mqtt_discovery_count` + fires a notification
warning the operator that the broker has come back
online.

```yaml
automation:
  - alias: "RoamCore: MQTT — broker-online guard"
    description: >-
      Fires when the broker-online chip flips TRUE.
      Clears the offline flag + flips the broker-status
      to "online" + fires a notification.
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_mqtt_broker_online
        to: "on"
    action:
      - service: logbook.log
        data:
          name: "RoamCore MQTT"
          message: >-
            Broker ONLINE: connection to {{ states('input_text.rc_mqtt_broker_url') }}
            established.
          entity_id: binary_sensor.rc_mqtt_broker_online
      - service: persistent_notification.dismiss
        data:
          notification_id: roamcore_mqtt_broker_offline
```

### §8.3 Broker-tls-error guard

The automation fires when
`input_boolean.rc_mqtt_broker_tls_enabled` is ON AND the
upstream `mqtt` integration reports a TLS handshake
failure. The automation flips
`sensor.rc_mqtt_broker_status` to "tls_error" + fires a
critical notification warning the operator that the TLS
handshake failed.

```yaml
automation:
  - alias: "RoamCore: MQTT — broker-tls-error guard"
    description: >-
      Fires when the TLS toggle is ON AND the upstream
      `mqtt` integration reports a TLS handshake failure.
      Flips the broker-status to "tls_error" + fires a
      critical notification.
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_mqtt_broker_online
        to: "off"
    condition:
      - condition: state
        entity_id: input_boolean.rc_mqtt_broker_tls_enabled
        state: "on"
    action:
      - service: logbook.log
        data:
          name: "RoamCore MQTT"
          message: >-
            Broker TLS ERROR: handshake with {{ states('input_text.rc_mqtt_broker_url') }}
            failed. Verify the broker's TLS certificate +
            the broker URL.
          entity_id: binary_sensor.rc_mqtt_broker_online
      - service: persistent_notification.create
        data:
          title: "RoamCore MQTT: broker TLS error"
          message: >-
            The broker at
            {{ states('input_text.rc_mqtt_broker_url') }}
            rejected the TLS handshake. Verify the
            broker's TLS certificate + the broker URL +
            the CA bundle.
          notification_id: roamcore_mqtt_broker_tls_error
```

### §8.4 Broker-auth-error guard

The automation fires when the upstream `mqtt` integration
reports an authentication failure (wrong username /
password). The automation flips
`sensor.rc_mqtt_broker_status` to "auth_error" + fires a
critical notification warning the operator that the
broker credentials are wrong.

```yaml
automation:
  - alias: "RoamCore: MQTT — broker-auth-error guard"
    description: >-
      Fires when the upstream `mqtt` integration reports
      an authentication failure. Flips the broker-status
      to "auth_error" + fires a critical notification.
    trigger:
      - platform: state
        entity_id: binary_sensor.rc_mqtt_broker_online
        to: "off"
    condition:
      - condition: template
        value_template: >
          {{ states('input_text.rc_mqtt_broker_username') | length > 0 }}
    action:
      - service: logbook.log
        data:
          name: "RoamCore MQTT"
          message: >-
            Broker AUTH ERROR: credentials for {{ states('input_text.rc_mqtt_broker_url') }}
            rejected. Verify the username + password.
          entity_id: binary_sensor.rc_mqtt_broker_online
      - service: persistent_notification.create
        data:
          title: "RoamCore MQTT: broker auth error"
          message: >-
            The broker at
            {{ states('input_text.rc_mqtt_broker_url') }}
            rejected the credentials for
            {{ states('input_text.rc_mqtt_broker_username') }}.
            Verify the username + password.
          notification_id: roamcore_mqtt_broker_auth_error
```

### §8.5 Publish-from-HA guard

The automation fires when ANY `script.*` / `automation.*`
action tries to call the `mqtt.publish` service while
`input_boolean.rc_mqtt_enabled` is OFF. The automation
BLOCKS the publish + flips
`sensor.rc_mqtt_broker_status` to "disabled" + fires a
critical notification warning the operator that
publishing is disabled.

```yaml
automation:
  - alias: "RoamCore: MQTT — publish-from-HA guard"
    description: >-
      Fires when any script.* / automation.* action tries
      to call mqtt.publish while the master enable is
      OFF. Blocks the publish + flips the broker-status
      to "disabled" + fires a critical notification.
    trigger:
      - platform: event
        event_type: mqtt_publish_attempted
    condition:
      - condition: state
        entity_id: input_boolean.rc_mqtt_enabled
        state: "off"
    action:
      - service: logbook.log
        data:
          name: "RoamCore MQTT"
          message: >-
            MQTT publish BLOCKED: master enable is OFF.
          entity_id: input_boolean.rc_mqtt_enabled
      - service: persistent_notification.create
        data:
          title: "RoamCore MQTT: publish blocked"
          message: >-
            The agent / automation tried to publish a
            message via `mqtt.publish` while
            input_boolean.rc_mqtt_enabled is OFF. Flip
            the master enable ON to allow publishes.
          notification_id: roamcore_mqtt_publish_blocked
      - event: mqtt_publish_blocked
        event_data:
          topic: "{{ trigger.event.data.topic }}"
          reason: master_enable_off
```

## §9 Troubleshooting

### §9.1 Broker not online

Symptom: `binary_sensor.rc_mqtt_broker_online` reads
FALSE even after the operator has installed the HACS
mosquitto add-on (Path A) / configured the external /
cloud broker (Path B) / started the local container / VM
broker (Path C).

Cause: the broker URL is wrong; OR the broker is not
running; OR the network is unreachable; OR the TLS
handshake failed; OR the credentials are wrong.

Fix: confirm the broker URL via
`input_text.rc_mqtt_broker_url` (default
`tcp://core-mosquitto:1883`) + confirm the broker is
running + confirm the network is reachable from the HA
box + flip `input_boolean.rc_mqtt_broker_tls_enabled`
OFF if the broker does NOT require TLS + populate
`input_text.rc_mqtt_broker_username` if the broker
requires authentication.

### §9.2 Discovery count not incrementing

Symptom: `sensor.rc_mqtt_discovery_count` reads 0 even
after the operator has connected upstream `mqtt`-
publishing devices.

Cause: the upstream devices are not publishing to the
canonical upstream `mqtt` discovery topics; OR the
upstream `mqtt` integration's discovery is disabled.

Fix: confirm the upstream devices are publishing to the
canonical upstream `mqtt` discovery topics
(homeassistant/+/+/config) + enable the upstream `mqtt`
integration's discovery via the HA UI under Settings →
Devices & services → Integrations → MQTT → Configure →
Discovery.

### §9.3 Publish-from-HA blocked

Symptom: `mqtt.publish` invocations fail with the
"master enable is OFF" message even when the operator
wants to publish.

Cause: the §8.5 publish-from-HA guard is not wired; OR
`input_boolean.rc_mqtt_enabled` is OFF.

Fix: confirm the §8.5 automation is wired + flip
`input_boolean.rc_mqtt_enabled` ON.

### §9.4 TLS handshake failure

Symptom: the upstream `mqtt` integration reports a TLS
handshake failure.

Cause: the broker's TLS certificate is invalid; OR the
CA bundle is missing; OR the broker URL is wrong.

Fix: confirm the broker's TLS certificate is valid +
confirm the CA bundle is in the operator's
`/config/` directory + confirm the broker URL is
correct + flip
`input_boolean.rc_mqtt_broker_tls_enabled` OFF if the
broker does NOT require TLS.

### §9.5 Authentication failure

Symptom: the upstream `mqtt` integration reports an
authentication failure (wrong username / password).

Cause: the operator's broker username / password is
wrong; OR the broker does NOT support the operator's
authentication protocol.

Fix: confirm the broker username / password is correct
+ confirm the broker supports the operator's
authentication protocol (Path A HACS mosquitto add-on:
no authentication by default; Path B external / cloud
broker: per provider docs; Path C local container / VM
broker: per provider docs).

### §9.6 Reconnect-now not firing

Symptom: pressing `button.rc_mqtt_reconnect_now` does
not reconnect the broker.

Cause: the reconnect-now automation is not wired; OR
the upstream `mqtt` integration is not configured to
auto-reconnect.

Fix: confirm the reconnect-now automation is wired +
confirm the upstream `mqtt` integration is configured
to auto-reconnect via the HA UI under Settings →
Devices & services → Integrations → MQTT → Configure →
Auto-reconnect.

## §10 Privacy

MQTT is HA local-only by design:

- The broker (Path A HACS mosquitto add-on, Path B
  external / cloud broker, Path C local container / VM
  broker) + the broker credentials + the broker-online
  chip + the broker-status + the discovery count + the
  reconnect-now button + the master enable + the broker
  username + the TLS toggle are ALL stored locally on the
  operator's HA box (no RoamCore-side cloud round-trip).
- The broker URL is owned by the operator (the recipe
  does NOT include any vendor-specific defaults for Path B
  or Path C; the operator populates the URL based on
  their chosen broker path).
- The audit log is stored in the HA core `logbook`
  integration (no third-party audit-log destination; no
  RoamCore-side cloud round-trip).
- The §8.1 + §8.2 + §8.3 + §8.4 + §8.5 automations are
  wired locally on the operator's HA box (no RoamCore-side
  cloud round-trip).
- The `mqtt.publish` wrapper is an upstream `script:`
  integration script-runner wrapper that the operator
  wires locally on their HA box (no RoamCore-side cloud
  round-trip).

RoamCore does NOT maintain any broker telemetry; the
broker credentials + the audit log + the broker-online
chip are 100% operator-owned. If the operator wants to
share the broker state across multiple HA instances,
they can use the HA core `input_*` helper entity
replication (or the upstream `sync` integration) — but
the recipe does NOT require any cross-instance sharing.

## §11 Promoting to tier-a

Tier-a would require a RoamCore-owned pub/sub broker
engine + integration code + integration tests against a
real pub/sub broker engine bench. The bench would need
the following canned fixture responses wired together in
a controlled environment:

1. Canned broker-disconnect event (the upstream `mqtt`
   integration reports a disconnect) — the §8.1
   broker-offline guard should fire (broker-online chip
   flips FALSE + broker-status flips to "offline" +
   critical notification fires).
2. Canned broker-reconnect event (the upstream `mqtt`
   integration reports a reconnect) — the §8.2
   broker-online guard should fire (broker-online chip
   flips TRUE + broker-status flips to "online" +
   notification fires).
3. Canned TLS handshake failure event (the upstream
   `mqtt` integration reports a TLS handshake failure) —
   the §8.3 broker-tls-error guard should fire
   (broker-status flips to "tls_error" + critical
   notification fires).
4. Canned authentication failure event (the upstream
   `mqtt` integration reports an authentication failure)
   — the §8.4 broker-auth-error guard should fire
   (broker-status flips to "auth_error" + critical
   notification fires).
5. Canned `mqtt.publish` invocation with
   `input_boolean.rc_mqtt_enabled` OFF — the §8.5
   publish-from-HA guard should fire (publish BLOCKS +
   broker-status flips to "disabled" + critical
   notification fires).
6. Canned `mqtt.publish` invocation with
   `input_boolean.rc_mqtt_enabled` ON — the §8.5
   publish-from-HA guard should NOT fire (publish
   succeeds + audit-log entry fires).
7. Canned broker-online + reconnect-now button press —
   the broker-online chip should flip TRUE + the
   `homeassistant/status` topic should re-publish.
8. Canned broker discovery message (the upstream `mqtt`
   integration receives a discovery message) — the
   `sensor.rc_mqtt_discovery_count` should increment.

The bench would also need a RoamCore-owned operator-
wired setup flow walking the operator through Pick the
broker path + Mount the broker credentials + Confirm the
broker is online + Enable + start publishing + Audit +
the §8 automations.

## §12 Files

- `connection.yml` — the source-of-truth tier-b
  manifest.
- `__init__.py` — `DOMAIN = "mqtt"` marker for the audit.
- `README.md` — the folder overview + the 8-tile table
  + the 5-§8-automation summary + the supersession
  pointer + the cross-references.
- `docs/recipe.md` — this file.
- `tests/test_connection_yml.py` — the 7 manifest-
  honesty checks.

External references:

- Legacy catalog page (now superseded by this slice):
  [`docs/catalog/homelab/mqtt.md`](../../../catalog/homelab/mqtt.md)
- Design doc (philosophy + broker wire-up details +
  tier-a promotion outline): [`docs/design.md`](../../../design.md)
- HA core `mqtt` integration upstream doc (the canonical
  broker integration umbrella): https://www.home-assistant.io/integrations/mqtt/

## §13 Cross-references

External HA core integrations:

- HA core `mqtt` integration: https://www.home-assistant.io/integrations/mqtt/
- HA core `mqtt` discovery documentation: https://www.home-assistant.io/docs/mqtt/discovery/
- HA core `mqtt` service documentation: https://www.home-assistant.io/docs/mqtt/service/
- HA core `input_boolean` integration: https://www.home-assistant.io/integrations/input_boolean/
- HA core `input_text` integration: https://www.home-assistant.io/integrations/input_text/
- HA core `input_number` integration: https://www.home-assistant.io/integrations/input_number/
- HA core `input_select` integration: https://www.home-assistant.io/integrations/input_select/
- HA core `input_datetime` integration: https://www.home-assistant.io/integrations/input_datetime/
- HA core `input_button` integration: https://www.home-assistant.io/integrations/input_button/
- HA core `script:` integration: https://www.home-assistant.io/integrations/script/
- HA core `template:` integration: https://www.home-assistant.io/integrations/template/
- HA core `logbook` integration: https://www.home-assistant.io/integrations/logbook/

HACS:

- HACS prerequisites: https://hacs.xyz/docs/setup/prerequisites

Other connection slices:

- Time-atomic (the §8.1 broker-offline guard's
  time-of-day primitives): `connections/time-atomic/`
  (Wave 3 #55)
- Remote-access (the §8.5 publish-from-HA guard's
  VPN primitive): `connections/remote-access/` (Wave 3
  #58)
- Approach lights (the §8.2 broker-online guard's
  dashboard banner pattern): `connections/approach-lights/`
  (Wave 3 #52)
- Fans (the §8.1 broker-offline guard's fan-protection
  cross-reference): `connections/fans/` (Wave 3 #59)
- Leveling (the §8.1 broker-offline guard's levelling-
  jack protection cross-reference):
  `connections/leveling/` (Wave 3 #60)
- Mode (the §8.3 broker-tls-error guard's mode-change
  cross-reference): `connections/mode/` (Wave 3 #61)
- Demo-mode (the §8.4 broker-auth-error guard's
  safety-chip pattern): `connections/demo-mode/` (Wave
  3 #62)
- Advanced-mode (the §8.5 publish-from-HA guard's
  confirm-flag pattern): `connections/advanced-mode/`
  (Wave 3 #63)
- OpenClaw JSON API (the §8.1 broker-offline guard's
  JSON payload cross-reference): `connections/openclaw-api/`
  (Wave 3 #64)
- Agent actions allowlist (the §8.5 publish-from-HA
  guard's kill-switch cross-reference):
  `connections/agent-actions-allowlist/` (Wave 3 #65)
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
  (the `mqtt` subsystem was added by this slice)