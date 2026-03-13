# Traccar first-boot provisioning (Golden Image)

## Goal
Ship a RoamCore “golden image” where **each install gets unique Traccar credentials** without any external support infrastructure.

Constraints:
- No shared default admin password baked into the image.
- Credentials must be stored **locally on the device**.
- Single source of truth for secrets: **Home Assistant** `/config/secrets.yaml`.

## How Traccar behaves
Modern Traccar versions **do not ship a default admin**. When the database contains no users, the **first created/registered user becomes the admin**.

## Implementation (RoamCore)
We provide a local Home Assistant add-on:
- **Slug:** `roamcore-traccar-init`
- **Name:** “RoamCore Traccar Init”

What it does:
1. Checks `/config/secrets.yaml` for keys:
   - `roamcore_traccar_admin_email`
   - `roamcore_traccar_admin_password`
2. If present → exits (idempotent).
3. If missing → generates a strong random password and writes both keys.
4. Waits for Traccar health endpoint: `GET <base_url>/api/health`
5. Attempts best-effort admin creation via `POST <base_url>/api/users`.
   - If the API call fails (version/config differences), the secrets are still written.
   - The user can complete the signup manually using the stored credentials.

### Why this pattern
This is the standard OSS “init container / first boot provisioning” approach:
- unique per install
- no external infra
- secrets never leave the device

## Install / Run (Home Assistant UI)
Because Supervisor APIs are permissioned, installation is intentionally a manual UI step.

1. Home Assistant → **Settings → Add-ons → Add-on store**
2. Menu (⋮) → **Reload**
3. Under **Local add-ons**, find **RoamCore Traccar Init**
4. Install → Start

## Where the credentials are stored
`/config/secrets.yaml`

Keys:
```yaml
roamcore_traccar_admin_email: "admin@roamcore.local"
roamcore_traccar_admin_password: "<generated>"
```

## Using the credentials
- Open Traccar UI (RoamCore Map page iframe, or directly).
- Login with `admin@roamcore.local` and the password in `secrets.yaml`.
- After login, you can change the email/password in Traccar.

## Security notes
- Do **not** print the password in logs by default.
- Keep `/config/secrets.yaml` protected with filesystem permissions.
- In future, the RoamCore Settings page can provide a “Reveal / Copy” flow that reads these keys from HA (not from the browser).
