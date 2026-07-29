# Remote access (Tailscale) — RoamCore setup

**Support tier:** B (community-supported Home Assistant integration; RoamCore contract layer on top)

RoamCore lets you reach your Home Assistant instance from anywhere without
opening ports on your mobile router or paying for Nabu Casa. It does this
by sitting the HA instance on a **Tailscale** mesh VPN — the HA core
*Tailscale* integration is already shipped with Home Assistant, and RoamCore
adds a small contract layer + operator-friendly UI on top.

> RoamCore does **not** ship a separate Tailscale client. The HA core
> integration is the only Tailscale client in the system.

## What you get

- One boolean kill-switch (`input_boolean.rc_remote_access_enabled`) that
  gates the entire feature.
- One text field (`input_text.rc_remote_access_tailnet_host`) where you set
  the device name as it appears in your tailnet (e.g. `home-assistant`).
- A stable set of contract entities the dashboard and automations consume:
  - `binary_sensor.rc_remote_access_active` — ON iff the kill-switch is ON
    AND at least one tailnet device is reporting in.
  - `sensor.rc_remote_access_url` — `https://<host>.ts.net`.
  - `sensor.rc_remote_access_peer_count` — number of devices on your
    tailnet.
  - `sensor.rc_remote_access_last_seen` — last successful integration
    poll (timestamp).

## Step-by-step setup

### 1. Enable the Tailscale integration in Home Assistant

Open *Settings → Devices & Services → + Add Integration → Tailscale*.
You will need a Tailscale API key (see
<https://tailscale.com/kb/1101/api/>). After enabling, HA creates one set
of `sensor.*_last_seen` / `binary_sensor.*_update_available` entities per
tailnet device.

If the integration is missing from the picker, install it via HACS-frontend
or as a custom integration from
<https://github.com/home-assistant/core/tree/dev/homeassistant/components/tailscale>.

### 2. Set the tailnet host

In *Settings → Devices & Services → Helpers* (or on the setup wizard
"Remote access" card), set:

- `input_text.rc_remote_access_tailnet_host` = the device name exactly as
  it appears in your tailnet. For most vans this is `home-assistant`.

The contract layer uses this single value to derive the access URL
(`https://home-assistant.ts.net`).

### 3. Flip the kill-switch

Toggle `input_boolean.rc_remote_access_enabled` to **ON**.

### 4. Confirm `binary_sensor.rc_remote_access_active` turns ON

Open any dashboard or the setup wizard card. You should see the status
chip switch from *Off* to *Active* within a few seconds. If it stays
*Off* or *Not configured*, see **Troubleshooting** below.

## Privacy

**RoamCore does not phone home.** All Tailscale AP traffic goes directly
from your devices to Tailscale's coordination server. The HAOS instance
only makes **outbound API calls** to `api.tailscale.com` while the
integration is enabled — there is no inbound port, no relay, no RoamCore
backend.

## Troubleshooting

### The Tailscale integration does not appear in *Add Integration*

You can install the integration two ways:

1. **HACS-frontend**: *HACS → Integrations → ⋯ → Custom repositories →
   add* `https://github.com/home-assistant/core` (category: *Integration*).
2. **Manual**: drop the `tailscale` folder from the HA core repo into
   `/config/custom_components/tailscale/` and restart HA.

### `sensor.rc_remote_access_url` is `unavailable`

You have not set the operator override. Open *Helpers* and set
`input_text.rc_remote_access_tailnet_host` to your Tailscale device name
(e.g. `home-assistant`). The entity will become available as soon as the
value is non-empty AND the kill-switch is ON.

### `binary_sensor.rc_remote_access_active` is `unavailable`

Either:

1. The kill-switch is OFF (`input_boolean.rc_remote_access_enabled`).
   Flip it to ON.
2. The Tailscale integration is not installed yet, or has no devices. Open
   the integration and check it reports at least one device.

### URL does not resolve from outside

Check the host spelling in `input_text.rc_remote_access_tailnet_host`. It
must match exactly the device name in your Tailscale admin console. Also
make sure your mobile carrier does not block UDP — Tailscale's WireGuard
fallback usually handles this automatically, but a corporate VPN can
interfere.

### "Peer count" looks wrong

The peer count is derived from `sensor.*_last_seen` entities currently
known to HA. If your tailnet has more than ~30 devices, HA may not have
created entities for all of them yet (first poll after enabling can take
a minute). Wait, then refresh the dashboard.

## Files added by this slice

- `homeassistant/packages/roamcore_remote_access.yaml` — contract layer
  (entities above).
- `homeassistant/packages/roamcore_setup_wizard_remote_access.yaml` —
  setup wizard card snippet.
- `docs/setup/remote-access.md` — this document.
- `scripts/checks/remote-access-tailscale-smoke.sh` — static smoke check.
- `scripts/check.sh` — wires the smoke into the repo check (existing
  chain from slice #28; this slice appends the new smoke).

## See also

- `docs/catalog/remote-access/tailscale.md` — catalog entry (tier-b
  description, links to upstream).
- `docs/reference/rc-entity-naming.md` — RoamCore entity naming
  convention used by all `rc_*` contract entities.