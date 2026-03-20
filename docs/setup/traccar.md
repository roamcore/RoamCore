# Traccar (RoamCore) — Setup & Credentials

RoamCore embeds the Traccar web UI inside Home Assistant via a same-origin proxy.

## ⚠️ Security note (read this)

Do **not** commit real credentials to git.

RoamCore expects Traccar credentials to live in Home Assistant's `/config/secrets.yaml` (on the HAOS host) or a token to be provided.

## Required HA secrets

Add the following keys to **`/config/secrets.yaml`** on your Home Assistant instance:

```yaml
# Traccar admin creds (used by the HA proxy to establish a session cookie)
roamcore_traccar_admin_email: "admin@roamcore.local"
roamcore_traccar_admin_password: "CHANGE_ME"

# Optional (preferred): Traccar user token. If set, the proxy uses
# GET /api/session?token=... instead of email/password.
roamcore_traccar_user_token: "OPTIONAL_TOKEN"
```

## Where the embedded UI lives

The embedded Traccar UI is served via a frontend-friendly route:

- `http://<home-assistant>:8123/roamcore/traccar/`

The raw Traccar port (e.g. `:8082`) is not recommended for embedding due to mobile/webview local-network restrictions.

## Troubleshooting

If the UI is blank:

1. Open Traccar directly once: `http://<home-assistant>:8082/`
2. Verify the proxy status endpoint (requires HA bearer token):
   - `GET /api/roamcore/traccar/_proxy_status`
3. Ensure the secrets above exist and restart Home Assistant.

