# Traccar (RoamCore) — Setup, credentials, and reconnect

RoamCore uses Traccar for **GPS tracking**, **route history**, and **Trip Wrapped**.

RoamCore embeds the Traccar web UI inside Home Assistant via a **same-origin proxy** so it works reliably on mobile (no “local network” iframe blocks).

## Step 1: Configure the Home Assistant Traccar integration

RoamCore reads your location from a `device_tracker` entity. The
`rc_location_*` contract sensors (`sensor.rc_location_lat`, etc.) auto-map
the tracker entity configured in
`input_text.rc_location_tracker_entity`. This step wires that input_text
to a real Traccar device.

### Which integration to use

There are two Traccar integrations Home Assistant supports:

| Integration | Domain | Source | Use it for |
| --- | --- | --- | --- |
| **Traccar Server** | `traccar_server` | Built into Home Assistant (core) | **This is the one RoamCore expects.** Connects to a running Traccar server and creates a `device_tracker.traccar_<device>` entity per device. |
| Traccar Client | `traccar` | Built into Home Assistant (core) | Sends the local device's location up to an external Traccar server via webhook. Not what you want for a van. |

RoamCore expects the **Traccar Server** integration (`traccar_server`).
It is built into Home Assistant, so you do **not** need HACS.

### Add the integration (one-time)

1. Confirm your Traccar server is reachable from Home Assistant.
   If you installed it as the official HA add-on (slug `a0d7b954_traccar`)
   it lives at `http://homeassistant.local:8082`. If you use the RoamCore
   proxy add-on (`roamcore-traccar-proxy`), use the ingress URL shown in
   **Settings → Add-ons → RoamCore Traccar Proxy → Open Web UI**.
2. Home Assistant → **Settings → Devices & services**.
3. Bottom-right: **Add Integration**.
4. Search for **Traccar Server** and select it.
5. Enter your Traccar server **Base URL**:
   - Official add-on: `http://homeassistant.local:8082`
   - RoamCore proxy add-on: use the ingress URL from step 1.
   - External Traccar server: `https://traccar.example.com`
6. Enter a Traccar **username** and **password** (the admin or a device
   user you created in Traccar). These are different from
   `/config/secrets.yaml` — RoamCore uses the integration's own auth.
7. Submit. Home Assistant will pull every device registered on that
   Traccar server.
8. After a few seconds you should see one or more
   `device_tracker.traccar_<device_name>` entities under **Settings →
   Devices & services → Traccar Server → Devices**.

### Point RoamCore at the entity

You have two paths; pick one:

**Path A — let RoamCore auto-fill (recommended on first install).**

The `homeassistant/packages/roamcore_location.yaml` package ships an
automation (`automation.rc_location_autofill_tracker_entity`) that runs on
`homeassistant_started` and on every new `device_tracker.traccar_*`
registration. It writes the **first** matching entity_id into
`input_text.rc_location_tracker_entity` automatically. Restart Home
Assistant after adding the integration, or just wait — the
`entity_registry_updated` trigger fires within a few seconds of the
integration registering a device.

**Path B — set it manually (when you have multiple devices or want
fine-grained control).**

1. Home Assistant → **Developer Tools → Actions**.
2. Action: `input_text.set_value`.
3. Target: `input_text.rc_location_tracker_entity`.
4. Data: `value: device_tracker.traccar_<your_device_name>` (paste the
   exact entity_id from Devices & services).
5. **Call action**.

Either way, after a few seconds the RoamCore contract sensors should
populate:

- `sensor.rc_location_lat`
- `sensor.rc_location_lon`
- `sensor.rc_location_speed`
- `sensor.rc_location_heading_deg`
- `sensor.rc_location_accuracy` (when the source exposes accuracy)
- `sensor.rc_location_source` (`traccar` once configured)

If they show `unknown`, double-check that
`input_text.rc_location_tracker_entity` matches a real entity id
(typos are common; the entity_id is **case-sensitive**).

### Optional: YAML pre-stage block

For users who prefer YAML, the `homeassistant/configuration_addon.yaml`
file ships a commented-out `device_tracker:` → `traccar:` snippet you can
paste into your own `configuration.yaml`. RoamCore keeps this disabled
by default (we follow the HACS-friendly / UI-first principle — see
GOLDEN.md §HACS-friendly layout) but the snippet is there for advanced
users.

## ⚠️ Security note (read this)

Do **not** commit real credentials to git.

RoamCore expects Traccar credentials to live in Home Assistant's `/config/secrets.yaml` (on the HAOS host) or a token to be provided.

## Required HA secrets (recommended)

Add the following keys to **`/config/secrets.yaml`** on your Home Assistant instance:

```yaml
# Traccar admin creds (used by the HA proxy to establish a session cookie)
roamcore_traccar_admin_email: "admin@roamcore.local"
roamcore_traccar_admin_password: "CHANGE_ME"

# Optional (preferred): Traccar user token. If set, RoamCore can authenticate
# without storing an email/password session.
roamcore_traccar_user_token: "OPTIONAL_TOKEN"
```

## Where the embedded UI lives

The embedded Traccar UI is served via a frontend-friendly route:

- `http://<home-assistant>:8123/api/roamcore/traccar`

The raw Traccar port (e.g. `:8082`) is not recommended for embedding due to mobile/webview local-network restrictions.

## Reconnect steps (when routes / Trip Wrapped stop updating)

Use **RoamCore → Settings → Traccar (Trip tracking)**:

1) Confirm **Base URL** and **Device ID**.
2) Refresh your **Traccar user token** and save it:
   - Paste into `input_text.rc_setup_traccar_user_token`
   - Run `script.rc_setup_save_traccar_user_token`
3) Run a test export:
   - `script.rc_trip_wrapped_run_today`

If you can’t generate a report after this, the most common causes are:
- wrong device id
- Traccar server not reachable from Home Assistant
- token expired / revoked

## Troubleshooting

If the UI is blank:

1. Open Traccar directly once: `http://<home-assistant>:8082/`
2. Verify the proxy status endpoint (requires HA bearer token):
   - `GET /api/roamcore/traccar/_proxy_status`
3. Ensure the secrets above exist and restart Home Assistant.
