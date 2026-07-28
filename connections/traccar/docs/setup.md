# Traccar (GPS / trip tracking) — install recipe

> **Connection tier:** `b` (recipe + manual add-on install)
> **Restart required:** yes (after add-on install)
> **Estimated time:** ~5 minutes

This is the install recipe for the **Traccar** connection on RoamCore.
Traccar is a self-hosted GPS tracker — RoamCore uses it for location
history, route lines on the map page, and Trip Wrapped reports.

The connection is tier-b because the upstream Traccar server add-on
+ the RoamCore proxy/init add-ons are three separate installs the
user has to confirm. There is no one-tap yet. See the
`promotion_blocker` notes in `connection.yml` for what tier-a would
require.

---

## What you'll install

Three add-ons, in this order:

| # | Add-on slug                         | Purpose                                                                 |
|---|-------------------------------------|-------------------------------------------------------------------------|
| 1 | `a0d7b954_traccar`                  | The Traccar server itself (devices report positions here).              |
| 2 | `local/roamcore-traccar-init`       | Generates a per-install admin password on first boot. Idempotent.       |
| 3 | `local/roamcore-traccar-proxy`      | Same-origin nginx proxy so the Traccar UI embeds in HA without iframe blocks. |

Then the RoamCore custom integration (`roamcore_traccar_proxy`) makes
the proxied routes available under `/api/roamcore/traccar`.

---

## Step 1 — Install the Traccar server add-on

1. Home Assistant → **Settings → Add-ons → Add-on store**.
2. Search for **Traccar**.
3. Install the official Traccar add-on (`slug: a0d7b954_traccar`).
4. Start the add-on. It listens on port `8082` inside HA.
5. Confirm it is up: `http://<home-assistant>:8082/` returns the Traccar login page.

> **Why this matters:** the RoamCore proxy points at this URL. If this
> add-on is not running, the proxied route 502s.

---

## Step 2 — Install the RoamCore Traccar Init add-on

This is the **first-boot credential generator**. The first user
registered with Traccar becomes the admin — Init handles that so you
don't ship a shared default password.

1. Home Assistant → **Settings → Add-ons → Add-on store**.
2. Menu (⋮) → **Reload** (so the local add-on is discovered).
3. Under **Local add-ons**, find **RoamCore Traccar Init**.
4. Click **Install**. Leave defaults. **Start** the add-on.

What it does:

1. Checks `/config/secrets.yaml` for `roamcore_traccar_admin_email` and
   `roamcore_traccar_admin_password`.
2. If both are present → exits (idempotent — safe to re-run).
3. If missing → generates a 24-char random password, writes both keys
   to `secrets.yaml`, and attempts admin creation against Traccar.
   (If the API call fails, the secrets are still saved — see
   `docs/runbooks/traccar-first-boot-provisioning.md`.)

> **Where the credentials live:** `/config/secrets.yaml` on the HAOS
> host. They never leave the device.

---

## Step 3 — Install the RoamCore Traccar Proxy add-on

This is the same-origin nginx reverse proxy that the RoamCore map
page embeds in an iframe.

1. Home Assistant → **Settings → Add-ons → Add-on store** → menu → **Reload**.
2. Under **Local add-ons**, find **RoamCore Traccar Proxy**.
3. **Install** → **Start**.

The default `traccar_base_url` is `http://homeassistant.local:8082`
(see `homeassistant/addons/roamcore-traccar-proxy/config.yaml`). Do
not change this unless you have moved the upstream Traccar server
somewhere exotic.

The proxy exposes:

- Ingress path: `/` (matches the Supervisor ingress slot for the add-on).
- As long as the proxy is running, the RoamCore map page can embed
  Traccar inside an iframe without the mobile local-network block.

---

## Step 4 — Restart Home Assistant

Some of the add-on paths are only registered after HA picks up the
custom component. Restart:

- **Settings → System → Restart Home Assistant**

Or via SSH: `ha core restart`.

---

## Step 5 — Verify the link

After the restart:

1. Open the RoamCore map page (Sidebar → **RoamCore** → **Map**).
2. The Traccar UI should render inside the iframe on the map page.
   If it does, the **proxy → server** link is working.
3. If the iframe is blank, see the **Troubleshooting** section below.

---

## Step 6 — Link a device

Traccar needs a device to be registered and reporting. The two common
flows are:

### A. Use the Traccar client app on your phone

1. Install **Traccar Client** (Android / iOS) on your phone.
2. In the app, set:
   - **Server URL:** `http://<home-assistant>:8082/`
   - **Device ID:** a unique number (e.g. `12`).
3. Log in with the Traccar admin credentials from
   `/config/secrets.yaml` (the `roamcore_traccar_admin_email` /
   `roamcore_traccar_admin_password` keys).
4. The app starts reporting positions. Within seconds you should see
   them on the Traccar map page embedded in RoamCore.

### B. Use a dedicated GPS tracker

Any Traccar-protocol GPS tracker (TK103, GT06N, etc.) works. Configure
the tracker to report to `<home-assistant>:8082` with the device id
matching whatever you set in the Traccar web UI.

---

## Where the credentials live

Add the following to `/config/secrets.yaml` on the HAOS host (Init
adds them for you, but you can also rotate them manually):

```yaml
# Traccar admin creds (used by the HA proxy to establish a session)
roamcore_traccar_admin_email: "admin@roamcore.local"
roamcore_traccar_admin_password: "CHANGE_ME"

# Optional (preferred): Traccar user token. If set, RoamCore can
# authenticate without storing an email/password session.
roamcore_traccar_user_token: "OPTIONAL_TOKEN"
```

> **Do not commit `/config/secrets.yaml` to git.** It is on the
> device only. See `docs/setup/traccar.md` for the full credential
> reference.

---

## Troubleshooting

**Traccar UI is blank inside the RoamCore map page**

1. Confirm the upstream Traccar server is up: open
   `http://<home-assistant>:8082/` directly. If it is not, the proxy
   is 502ing by design.
2. Confirm the proxy add-on is **Started** (not just installed).
3. Confirm `homeassistant/custom_components/roamcore_traccar_proxy/__init__.py`
   is present at `/config/custom_components/roamcore_traccar_proxy/__init__.py`.
   If not, re-run `install.sh`.

**Trip Wrapped stops reporting**

Use **RoamCore → Settings → Traccar (Trip tracking)**. The reconnect
checklist covers base URL, device id, token refresh, and a test export.

**Password rotation**

Edit the two keys in `/config/secrets.yaml` directly, then restart HA
(not the add-on). The Init add-on is idempotent and will not overwrite
your edits.

---

## See also

- `docs/setup/traccar.md` — full credential + reconnect reference.
- `docs/runbooks/traccar-first-boot-provisioning.md` — golden image
  provisioning for fleet rollouts.
- `homeassistant/addons/roamcore-traccar-proxy/config.yaml` — proxy
  add-on options.
- `homeassistant/addons/roamcore-traccar-init/config.yaml` — init
  add-on options.
- `homeassistant/custom_components/roamcore_traccar_proxy/__init__.py` — the
  HA-side proxy integration.
