# Traccar (RoamCore) — Setup, credentials, and reconnect

RoamCore uses Traccar for **GPS tracking**, **route history**, and **Trip Wrapped**.

RoamCore embeds the Traccar web UI inside Home Assistant via a **same-origin proxy** so it works reliably on mobile (no “local network” iframe blocks).

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
