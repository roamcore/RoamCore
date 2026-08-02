# Remote access — full howto (RoamCore vendor-neutral remote-access umbrella for HA — Tailscale + Cloudflare Tunnel + Nabu Casa HA Cloud + Wireguard)

This recipe is the canonical howto for the
`connections/remote-access/` tier-b recipe connection (Wave 3
#58). It walks the operator through setting up ONE of the FOUR
operator-pickable remote-access paths (Path A Tailscale mesh VPN
+ Path B Cloudflare Tunnel no-inbound-ports + Path C Nabu Casa
HA Cloud official cloud relay + Path D Wireguard self-hosted
VPN) + the 9 `rc_remote_access_*` contract tiles + the FIVE §8
automations.

The recipe assumes the operator has an always-on HA instance
reachable from the operator's home network. If the operator's
HA instance is not yet set up, see the broader RoamCore
documentation for the HA setup + the HA Companion app install
+ the operator's account on the chosen vendor's service.

## §1 What is remote access in RoamCore?

Remote access (vendor-neutral remote-access umbrella for HA,
covering Tailscale + Cloudflare Tunnel + Nabu Casa HA Cloud +
Wireguard — operator picks ONE path) — the umbrella for "check
the van from anywhere: see sensor status, view cameras, get
alerts, or (optionally) control systems" — is the networking-
category complement to the broader RoamCore scene + automation
affordances. The umbrella positions remote access as a
networking-category concern (not a scene + not an automation)
because remote access is the substrate that lets the operator
reach the HA server from OFF-LAN; once the operator is ON-LAN,
the scene + automation affordances take over.

The umbrella publishes the 9 `rc_remote_access_*` contract
tiles (vendor-neutral — no Tailscale / Cloudflare / Nabu Casa /
Wireguard / HACS / HA Companion / ESPHome / MQTT names leak
into the tile ids). The tiles are:

- `binary_sensor.rc_remote_access_enabled` — the operator
  kill-switch (the operator's single source of truth for
  whether remote access should be active). The kill-switch is
  an `input_boolean` (since 2022.x) exposed via the HA Core
  `input_boolean` integration; the operator sets it to TRUE
  to enable remote access + FALSE to disable remote access.
  The §8.1 + §8.2 automations fire on the kill-switch state
  change to enable or disable the chosen remote-access path.
- `sensor.rc_remote_access_url` — the URL to access HA
  remotely (the mesh-VPN hostname for Path A + the Cloudflare
  Tunnel hostname for Path B + the Nabu Casa remote URL for
  Path C + the Wireguard server endpoint for Path D). The URL
  derives from the operator's chosen path (the
  `select.rc_remote_access_path` tile) + the upstream
  integration's configuration (the Tailscale MagicDNS hostname
  for Path A + the Cloudflare DNS hostname for Path B + the
  Nabu Casa remote URL for Path C + the Wireguard server
  endpoint for Path D).
- `binary_sensor.rc_remote_access_active` — the AND gate
  (TRUE iff the kill-switch is ON AND at least one
  remote-access path is verified reachable). The tile is a
  `template:` binary_sensor (since 2022.x) that ANDs the
  kill-switch state + the upstream reachability state. The
  tile is the operator-facing "is remote access actually
  working?" indicator.
- `sensor.rc_remote_access_active_path` — which path is
  currently active (one of `tailscale` /
  `cloudflare_tunnel` / `nabu_casa` / `wireguard` /
  `companion_external_url` / `none`). The tile is a
  `template:` sensor (since 2022.x) that derives from the
  `select.rc_remote_access_path` tile + the upstream
  integration's state.
- `sensor.rc_remote_access_peer_count` — count of remote-
  access clients currently connected (Tailscale-only — the
  HA core `tailscale` integration exposes tailnet peer count
  via `device_tracker.tailscale_*` entities). For Path B +
  Path C + Path D, the tile surfaces 0 (the peer count is
  not directly exposed by those upstream integrations; the
  operator can verify reachability via the
  `binary_sensor.rc_remote_access_active` tile instead).
- `sensor.rc_remote_access_last_verified_minutes_ago` —
  freshness gate (the minutes since the last successful
  upstream reachability probe). The §8.3 auto-verify
  automation updates this tile every 15 minutes; the operator
  can trigger a manual probe via the
  `button.rc_remote_access_verify_now` button. The tile is a
  `template:` sensor (since 2022.x) that derives from the
  last verification timestamp (an `input_datetime` since
  2022.x).
- `binary_sensor.rc_remote_access_hostname_resolvable` —
  TRUE if the chosen path's hostname resolves (TRUE for
  Path A with MagicDNS enabled + Path B with Cloudflare DNS
  enabled + Path C with the Nabu Casa remote URL resolving
  + Path D with the Wireguard server endpoint resolving).
  The tile is a `template:` binary_sensor (since 2022.x)
  that derives from a DNS lookup of the chosen path's
  hostname.
- `button.rc_remote_access_verify_now` — manual verification
  trigger (the operator can force an immediate reachability
  probe without waiting for the §8.3 15-minute auto-verify).
  The button is an `input_button` (since 2022.x) exposed via
  the HA Core `input_button` integration; pressing the
  button fires the upstream reachability probe + updates the
  `sensor.rc_remote_access_last_verified_minutes_ago` tile.
- `select.rc_remote_access_path` — operator-chosen path
  (one of `tailscale` / `cloudflare_tunnel` / `nabu_casa` /
  `wireguard` / `none`). The tile is an `input_select`
  (since 2022.x) exposed via the HA Core `input_select`
  integration; the operator picks one of the four paths. The
  §8.4 notify-on-path-switch automation fires on the path
  change + sends a notification to the operator's phone.

The umbrella positions remote access as a vendor-neutral
contract layer (no Tailscale / Cloudflare / Nabu Casa /
Wireguard / HACS / HA Companion / ESPHome / MQTT names leak
into the tile ids). The tile ids are the operator-facing
surface the dashboard + OpenClaw queries use; the upstream
integration entities are the substrate the contract layer
reads from. The operator picks ONE of the four paths above;
the recipe §3 + §4 + §5 + §6 walks through each path's setup.

## §2 Prerequisites

Before installing the remote-access connection, the operator
must have:

1. **An always-on HA instance reachable from the operator's
   home network.** The HA server must be on the operator's
   home LAN + must be reachable from at least one device on
   the LAN (e.g. the operator's phone when at home). This is
   a baseline RoamCore requirement; the broader RoamCore
   documentation walks through the HA setup.

2. **At least one remote-access path chosen.** The operator
   picks ONE of the four paths (Path A Tailscale + Path B
   Cloudflare Tunnel + Path C Nabu Casa HA Cloud + Path D
   Wireguard). The choice depends on the operator's account
   on the chosen vendor's service + the operator's preference
   for managed vs self-hosted services + the operator's
   willingness to pay for a subscription.

3. **The operator's account on the chosen vendor's service.**
   - **Path A — Tailscale:** a Tailscale account (free for
     personal use; sign up at https://login.tailscale.com/).
   - **Path B — Cloudflare Tunnel:** a Cloudflare account
     (free for personal use; sign up at
     https://dash.cloudflare.com/sign-up) + a Cloudflare-
     managed domain (the operator's domain must be on
     Cloudflare's nameservers).
   - **Path C — Nabu Casa HA Cloud:** a Nabu Casa
     subscription (paid; subscribe via the HA Cloud panel
     in the HA UI; the operator's HA account must be
     linked to a Nabu Casa subscription).
   - **Path D — Wireguard:** no vendor account (the operator
     owns the Wireguard server keys + the per-client keys).
     The operator must be comfortable with per-client key
     management + Wireguard server configuration.

4. **The HA server's firewall permitting the chosen path's
   port range.** The HA server's firewall (typically the
   OpenWrt firewall on the home LAN + any host-based firewall
   on the HA server itself) must permit the chosen path's
   port range:
   - **Path A — Tailscale:** outbound UDP 41641 (Tailscale's
     default port for the `tailscaled` daemon; the operator
     does NOT need to open inbound ports on the HA server's
     firewall — Tailscale is outbound-only by design).
   - **Path B — Cloudflare Tunnel:** outbound HTTPS 7844
     (Cloudflare's default port for the `cloudflared` daemon;
     the operator does NOT need to open inbound ports on the
     HA server's firewall — Cloudflare Tunnel is outbound-
     only by design).
   - **Path C — Nabu Casa HA Cloud:** outbound HTTPS 443
     (Nabu Casa's remote relay uses HTTPS; the operator does
     NOT need to open inbound ports on the HA server's
     firewall — Nabu Casa is outbound-only by design).
   - **Path D — Wireguard:** inbound UDP 51820 (Wireguard's
     default port for the Wireguard server interface; the
     operator MUST open inbound ports on the HA server's
     firewall + on the home router's port-forwarding rules
     for the Wireguard server interface).

5. **The HA Companion app for the per-path external URL
   check.** The HA Companion app (Android / iOS) is the
   canonical OFF-LAN affordance; the Companion app's
   `external_url` setting (since 2022.x) points the phone at
   the chosen remote-access URL when the operator is OFF-LAN.
   The operator installs the HA Companion app + connects it
   to the HA instance + sets the `external_url` setting to
   the chosen path's URL.

6. **The operator's DNS provider account if Path B Cloudflare
   Tunnel is chosen.** The operator's domain must be on
   Cloudflare's nameservers + the Cloudflare DNS must be
   configured for the tunnel hostname. This is a Cloudflare-
   specific prerequisite; Paths A + C + D do NOT require a
   Cloudflare-managed domain.

7. **The mode/automation-builder recipe (Wave 2 #23) for the
   Stealth-mode suppression.** The §8.5 Stealth-mode
   suppression automation uses the mode/automation-builder
   recipe's `select.rc_mode` tile (with options `home` /
   `away` / `stealth` / `sleep`). The operator must have the
   mode/automation-builder recipe installed before the §8.5
   automation can do anything useful.

8. **A `tag_id → scene` mapping table (optional, only if the
   operator wants to use NFC tags to toggle the kill-switch).
   ** The operator can use NFC tags (via the NFC tags Wave 3
   #57 connection) to toggle the `binary_sensor.rc_remote_
   access_enabled` kill-switch — e.g. tap an NFC tag at the
   entry door to enable remote access when leaving the van.
   This is an optional affordance; the operator can ignore it.

## §3 Path A — Tailscale (mesh VPN, default for most operators)

Path A is the default for any van operator who wants a secure
mesh VPN without opening inbound ports + with MagicDNS
hostname resolution (the HA server is reachable as
`https://<host>.ts.net`). Path A was the Wave 2 #29 focus
(`feat/wave2-remote-access-tailscale` @ `0caa9c2`) — that
branch already shipped the Tailscale-specific contract at
`homeassistant/packages/roamcore_remote_access.yaml`. This
slice LIFTS that contract into the `connections/` pipeline +
ADDS the broader vendor-neutral contract layer.

The 7-step setup:

1. **Install Tailscale on the HA server via the HA core
   `tailscale` integration OR the HACS Tailscale add-on.**
   The operator picks ONE:
   - **HA core `tailscale` integration** (since 2022.x):
     Settings → Devices & Services → Add Integration → search
     for "Tailscale" → click the integration → follow the
     operator-wired setup flow (the integration prompts for
     the Tailscale account login + the tailnet name + the
     API key). The integration exposes tailnet device status
     via the `binary_sensor.tailscale_*` entities + the
     `device_tracker.tailscale_*` entities.
   - **HACS Tailscale add-on** (HACS — the HACS Tailscale
     add-on installs the `tailscaled` daemon on the HA server
     itself; useful if the operator wants the HA server to
     be a Tailscale node directly rather than just monitoring
     the tailnet). The HACS add-on is installed via HACS →
     Add-on Store → search for "Tailscale" → install → start
     the add-on → configure the auth key.

2. **Login to Tailscale.** The operator logs in to Tailscale
   via the HA core `tailscale` integration's setup flow OR
   via the HACS Tailscale add-on's configuration. The login
   authorizes the HA server to join the operator's tailnet.

3. **Enable MagicDNS.** In the Tailscale admin console
   (https://login.tailscale.com/admin/dns), the operator
   enables MagicDNS. MagicDNS assigns each tailnet device a
   stable hostname (`<host>.ts.net`) + resolves the hostname
   to the device's Tailscale IP. The HA server is reachable
   as `https://<host>.ts.net` once MagicDNS is enabled.

4. **Verify HA is reachable via `https://<host>.ts.net`.**
   From any device on the operator's tailnet (e.g. the
   operator's phone with Tailscale installed), the operator
   opens `https://<host>.ts.net` in a browser + verifies the
   HA UI loads. If the UI does NOT load, check that MagicDNS
   is enabled in the Tailscale admin console + check that
   the HA server's firewall permits outbound UDP 41641.

5. **Add the operator's devices to the tailnet.** The
   operator installs Tailscale on each device that should
   reach the HA server remotely (e.g. the operator's phone
   + the operator's laptop + the operator's tablet). Each
   device logs in to the same Tailscale account + joins the
   same tailnet. Once added, the device can reach the HA
   server via `https://<host>.ts.net`.

6. **Configure the `binary_sensor.rc_remote_access_enabled`
   kill-switch.** The operator creates an `input_boolean`
   (Settings → Devices & Services → Helpers → Create Helper
   → Toggle → name it "Remote access enabled"). The tile
   starts as TRUE; the operator can toggle it via the
   dashboard + the HA Companion app.

7. **Configure `select.rc_remote_access_path = tailscale`.**
   The operator creates an `input_select` (Settings →
   Devices & Services → Helpers → Create Helper → Dropdown →
   name it "Remote access path" + add options
   `tailscale` / `cloudflare_tunnel` / `nabu_casa` /
   `wireguard` / `none`). The operator selects
   `tailscale`.

Cross-reference: the Wave 2 #29 branch
(`feat/wave2-remote-access-tailscale` @ `0caa9c2`) already
shipped the Tailscale-specific contract layer at
`homeassistant/packages/roamcore_remote_access.yaml`. This
slice lifts that contract into the `connections/` pipeline +
ADDS the broader vendor-neutral contract layer. The Wave 2
contract is a SUPERSET of Path A only; this slice's
`connections/remote-access/` is the vendor-neutral umbrella
that includes Path A as one of four operator-pickable paths.

## §4 Path B — Cloudflare Tunnel (no inbound ports, default for operators with a Cloudflare-managed domain)

Path B is the default for any van operator who already has a
Cloudflare-managed domain + who wants to expose the HA server
without opening inbound ports on the HA server's firewall +
who wants Cloudflare's edge caching + DDoS protection for
the remote-access path. Path B is NOT recommended for
operators who do NOT have a Cloudflare-managed domain (Path A
+ Path C + Path D are better alternatives in that case).

The 7-step setup:

1. **Create a Cloudflare account.** The operator signs up at
   https://dash.cloudflare.com/sign-up (free for personal
   use). The Cloudflare account is the operator's
   authentication for the Cloudflare dashboard + the
   Cloudflare API.

2. **Add the operator's domain to Cloudflare.** In the
   Cloudflare dashboard (https://dash.cloudflare.com/), the
   operator clicks "Add a Site" + enters the operator's
   domain (e.g. `example.com`) + selects the Free plan +
   follows the onboarding flow. Cloudflare scans the
   operator's existing DNS records + instructs the operator
   to update the domain's nameservers to Cloudflare's
   nameservers. Once the nameservers are updated (DNS
   propagation takes up to 24 hours), the operator's domain
   is on Cloudflare's nameservers.

3. **Create a Cloudflare Tunnel pointing at the HA server's
   local URL.** In the Cloudflare dashboard, the operator
   navigates to Zero Trust → Networks → Tunnels → Create a
   tunnel → selects "Cloudflared" → names the tunnel
   (e.g. "roamcore-ha") + copies the tunnel token (a long
   string that the `cloudflared` daemon uses to authenticate
   against Cloudflare). The operator adds a public hostname
   (e.g. `ha.example.com`) + points it at the HA server's
   local URL (e.g. `http://homeassistant.local:8123`).

4. **Install the `cloudflared` daemon on the HA server via
   the HACS `cloudflared` add-on OR the official Cloudflare
   Tunnel integration.** The operator picks ONE:
   - **HACS `cloudflared` add-on** (HACS — installs the
     `cloudflared` daemon on the HA server itself). The
     operator installs the add-on via HACS → Add-on Store →
     search for "Cloudflared" → install → start the add-on
     → paste the tunnel token from step 3 into the add-on's
     configuration. The add-on starts the `cloudflared`
     daemon + connects to Cloudflare's edge.
   - **Official Cloudflare Tunnel integration** (since
     2022.x — exposes a GUI flow for the operator to
     authenticate against Cloudflare + configure the tunnel
     token). The integration is installed via Settings →
     Devices & Services → Add Integration → search for
     "Cloudflare" → click the integration → follow the
     operator-wired setup flow.

5. **Verify the tunnel is reachable.** From any device with
   internet access (e.g. the operator's phone on cellular),
   the operator opens `https://ha.example.com` (the public
   hostname from step 3) in a browser + verifies the HA UI
   loads. If the UI does NOT load, check that the tunnel
   token is correct + check that the `cloudflared` daemon
   is running + check that Cloudflare DNS is resolving the
   public hostname.

6. **Configure the `binary_sensor.rc_remote_access_enabled`
   kill-switch.** Same as Path A step 6 (create an
   `input_boolean` named "Remote access enabled" + start as
   TRUE).

7. **Configure `select.rc_remote_access_path =
   cloudflare_tunnel`.** Same as Path A step 7 (create an
   `input_select` named "Remote access path" + select
   `cloudflare_tunnel`).

Cross-reference: the HACS `cloudflared` add-on
(https://github.com/hassio-addons/addon-cloudflared) +
the HA community guide for Cloudflare Tunnel + the
Cloudflare Tunnel documentation
(https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/).

## §5 Path C — Nabu Casa HA Cloud (Home Assistant's official cloud relay)

Path C is the default for any van operator who wants the HA
Core official cloud relay + who does NOT want to manage a
self-hosted VPN server + who is willing to pay for the
subscription. Nabu Casa is paid; the operator subscribes
directly via the HA Cloud panel.

The 5-step setup:

1. **Subscribe to Nabu Casa HA Cloud via the HA Cloud panel.**
   In the HA UI, the operator navigates to Settings → Home
   Assistant Cloud → Start your free trial (or subscribe
   directly if the operator has already used the trial).
   The operator creates a Nabu Casa account (or logs in to
   an existing account) + enters the payment information +
   completes the subscription.

2. **Enable remote access.** In the HA Cloud panel, the
   operator toggles "Remote access" to ON. The HA Core
   `cloud` integration (since 2022.x) exposes the remote
   URL via `sensor.home_assistant_cloud_remote` + the
   `cloud.remote_connect` / `cloud.remote_disconnect`
   services.

3. **Verify the Nabu Casa remote URL.** The operator opens
   the `sensor.home_assistant_cloud_remote` URL in a
   browser + verifies the HA UI loads. If the UI does NOT
   load, check that the Nabu Casa subscription is active +
   check that remote access is enabled in the HA Cloud
   panel + check that the HA Core `cloud` integration is
   connected to Nabu Casa.

4. **Configure the `binary_sensor.rc_remote_access_enabled`
   kill-switch.** Same as Path A step 6 (create an
   `input_boolean` named "Remote access enabled" + start as
   TRUE).

5. **Configure `select.rc_remote_access_path = nabu_casa`.**
   Same as Path A step 7 (create an `input_select` named
   "Remote access path" + select `nabu_casa`).

Note: Nabu Casa is the HA Core official cloud relay but is
paid. The operator subscribes directly via the HA Cloud
panel; the subscription covers the Nabu Casa remote relay +
the Nabu Casa remote URL + the Nabu Casa remote access
service. The HA Core `cloud` integration is the upstream
source for the remote URL + the `cloud.remote_connect` /
`cloud.remote_disconnect` services.

Cross-reference: the HA Core `cloud` integration
(https://www.home-assistant.io/integrations/cloud/) +
the Nabu Casa website (https://www.nabucasa.com/) + the HA
Cloud panel documentation.

## §6 Path D — Wireguard (manual VPN, default for operators who prefer self-hosted VPN over managed services)

Path D is the default for any van operator who prefers a
self-hosted VPN (no third-party relay + no subscription) +
who is comfortable with per-client key management + who
wants full control over the VPN configuration. Path D
requires the most operator expertise (the operator must
generate + manage keys + configure the Wireguard server
interface + configure firewall rules).

The 8-step setup:

1. **Install Wireguard on the HA server via the HACS
   `wireguard` add-on OR a manual install.** The operator
   picks ONE:
   - **HACS `wireguard` add-on** (HACS — installs the
     Wireguard server in the HA server + generates server
     keys + exposes the VPN interface for manual peer
     management). The operator installs the add-on via
     HACS → Add-on Store → search for "Wireguard" →
     install → start the add-on → configure the server
     interface (IP range + port + DNS).
   - **Manual install** (the operator installs Wireguard
     directly on the HA server's host OS via apt / dnf /
     apk). This requires SSH access to the HA server's
     host OS + comfort with the Wireguard CLI.

2. **Generate server keys.** The operator generates a
   Wireguard server private key + public key pair. The
   HACS `wireguard` add-on generates the keys
   automatically; for a manual install, the operator runs
   `wg genkey | tee /etc/wireguard/server_private.key |
   wg pubkey > /etc/wireguard/server_public.key`. The
   server private key is stored on the HA server only; the
   server public key is shared with each client.

3. **Generate per-client keys.** For each device that
   should connect to the VPN (e.g. the operator's phone
   + the operator's laptop), the operator generates a
   Wireguard client private key + public key pair. The
   HACS `wireguard` add-on generates the keys
   automatically per peer; for a manual install, the
   operator runs `wg genkey | tee client_private.key |
   wg pubkey > client_public.key` for each client. The
   client private key is stored on the client only; the
   client public key is added to the Wireguard server's
   peer list.

4. **Configure the Wireguard server interface.** The
   operator configures the Wireguard server's interface
   in `/etc/wireguard/wg0.conf` (for a manual install) OR
   via the HACS `wireguard` add-on's configuration. The
   configuration includes:
   - The interface's private key (server_private.key).
   - The interface's address (e.g. `10.0.0.1/24`).
   - The interface's listen port (default 51820).
   - The `PostUp` + `PostDown` rules (for IP forwarding +
     NAT).
   - The peer list (one peer per client, with the
     client's public key + the client's allowed IP range).

5. **Add the operator's devices as Wireguard peers.** For
   each client, the operator adds a `[Peer]` section to
   the Wireguard server's configuration with the
   client's public key + the client's allowed IP range
   (e.g. `10.0.0.2/32` for the first client +
   `10.0.0.3/32` for the second client). The operator
   then distributes the Wireguard client configuration
   (the server's public key + the server's endpoint +
   the client's private key + the client's allowed IP
   range) to each client device.

6. **Configure firewall rules.** The operator opens
   inbound UDP 51820 (Wireguard's default port) on the
   HA server's firewall + on the home router's port-
   forwarding rules. The operator also enables IP
   forwarding on the HA server's host OS (via
   `sysctl -w net.ipv4.ip_forward=1`).

7. **Verify the VPN tunnel.** From each client device, the
   operator connects to the VPN + verifies that the
   client can reach the HA server via the VPN's IP
   range (e.g. `https://10.0.0.1:8123`). If the client
   cannot connect, check that the server's public key is
   correct in the client's configuration + check that
   the client's public key is correct in the server's
   peer list + check that the firewall permits inbound
   UDP 51820 + check that IP forwarding is enabled.

8. **Configure the `binary_sensor.rc_remote_access_enabled`
   kill-switch + `select.rc_remote_access_path =
   wireguard`.** Same as Path A step 6 + step 7 (create an
   `input_boolean` named "Remote access enabled" + start as
   TRUE + create an `input_select` named "Remote access
   path" + select `wireguard`).

Cross-reference: the HACS `wireguard` add-on +
the Wireguard documentation (https://www.wireguard.com/) +
the Wireguard quickstart
(https://www.wireguard.com/quickstart/).

## §7 RoamCore contract entities

The umbrella publishes the 9 `rc_remote_access_*` contract
tiles. The tiles are vendor-neutral (no Tailscale /
Cloudflare / Nabu Casa / Wireguard / HACS / HA Companion /
ESPHome / MQTT names leak into the tile ids). The tile ids
follow the `^[a-z_]+\.rc_remote_access_[a-z0-9_]+$` pattern
(per `docs/reference/rc-entity-naming.md`).

The 9 tiles:

- `binary_sensor.rc_remote_access_enabled` — the operator
  kill-switch (`input_boolean.rc_remote_access_enabled`).
  The tile is a `template:` binary_sensor (since 2022.x)
  that mirrors the `input_boolean` state.
- `sensor.rc_remote_access_url` — the URL to access HA
  remotely (`text.rc_remote_access_url`). The tile is a
  `template:` sensor (since 2022.x) that derives from the
  operator's chosen path + the upstream integration's
  configuration.
- `binary_sensor.rc_remote_access_active` — the AND gate
  (`template:` binary_sensor). The tile is TRUE iff the
  kill-switch is ON AND at least one remote-access path
  is verified reachable.
- `sensor.rc_remote_access_active_path` — which path is
  currently active (`template:` sensor). The tile derives
  from the `select.rc_remote_access_path` tile + the
  upstream integration's state.
- `sensor.rc_remote_access_peer_count` — count of remote-
  access clients currently connected (`template:` sensor).
  The tile surfaces the count of `device_tracker.*`
  entities (for Path A Tailscale) OR 0 (for Path B +
  Path C + Path D — the peer count is not directly
  exposed by those upstream integrations).
- `sensor.rc_remote_access_last_verified_minutes_ago` —
  freshness gate (`template:` sensor). The tile derives
  from the last verification timestamp (an
  `input_datetime` since 2022.x).
- `binary_sensor.rc_remote_access_hostname_resolvable` —
  TRUE if the chosen path's hostname resolves (`template:`
  binary_sensor). The tile derives from a DNS lookup of
  the chosen path's hostname.
- `button.rc_remote_access_verify_now` — manual
  verification trigger (`input_button.rc_remote_access_
  verify_now`). The button is an `input_button` (since
  2022.x) exposed via the HA Core `input_button`
  integration; pressing the button fires the upstream
  reachability probe + updates the
  `sensor.rc_remote_access_last_verified_minutes_ago`
  tile.
- `select.rc_remote_access_path` — operator-chosen path
  (`input_select.rc_remote_access_path`). The tile is an
  `input_select` (since 2022.x) exposed via the HA Core
  `input_select` integration; the operator picks one of
  the four paths.

The upstream integration entities expose the underlying
data:

- **Path A — Tailscale:** the HA core `tailscale`
  integration (since 2022.x) exposes
  `binary_sensor.tailscale_*` entities + the
  `device_tracker.tailscale_*` entities from the
  operator's tailnet. The contract layer reads from
  these entities.
- **Path B — Cloudflare Tunnel:** the HACS `cloudflared`
  add-on exposes the `cloudflared` daemon status + the
  Cloudflare Tunnel hostname. The contract layer reads
  from the add-on's status entity.
- **Path C — Nabu Casa HA Cloud:** the HA Core `cloud`
  integration (since 2022.x) exposes
  `sensor.home_assistant_cloud_remote` + the
  `cloud.remote_connect` / `cloud.remote_disconnect`
  services. The contract layer reads from
  `sensor.home_assistant_cloud_remote`.
- **Path D — Wireguard:** the HACS `wireguard` add-on
  exposes the Wireguard server interface status + the
  peer list. The contract layer reads from the add-on's
  status entity.

Translation helpers (per docs/reference/rc-entity-naming.md):

- **Path-specific verification states:** the contract layer
  translates the upstream integration's verification state
  into the `binary_sensor.rc_remote_access_active` tile.
  The translation is a `template:` binary_sensor that
  reads from the upstream integration's status entity
  + the kill-switch state.
- **Path-specific URL:** the contract layer translates the
  upstream integration's URL into the
  `sensor.rc_remote_access_url` tile. The translation is a
  `template:` sensor that reads from the upstream
  integration's URL entity + the
  `select.rc_remote_access_path` tile.
- **Hostname resolvable:** the contract layer translates a
  DNS lookup of the chosen path's hostname into the
  `binary_sensor.rc_remote_access_hostname_resolvable`
  tile. The translation is a `template:` binary_sensor
  that reads from a `command_line` sensor (since 2022.x)
  that runs `dig +short <hostname>`.
- **Peer count:** the contract layer translates the
  upstream integration's peer count into the
  `sensor.rc_remote_access_peer_count` tile. The
  translation is a `template:` sensor that reads from the
  upstream integration's peer count entity (Path A
  Tailscale only — for Path B + Path C + Path D, the tile
  surfaces 0).

The kill-switch (`binary_sensor.rc_remote_access_enabled`)
is the operator-facing affordance; the §8.1 + §8.2
automations fire on the kill-switch state change. The
freshness gate (`sensor.rc_remote_access_last_verified_
minutes_ago`) is the §8.3 auto-verify automation's
timestamp; the §8.3 automation fires every 15 minutes +
updates the tile. The per-path hostname contract is the
`sensor.rc_remote_access_url` tile's derivation; the URL
is the operator-facing affordance for "what URL do I use
to reach the HA server remotely?".

## §8 Automations

The §8 walks through the FIVE MANDATORY automations. The
FIVE automations are MANDATORY before first use; without
them, the contract tiles are dormant (the kill-switch
state does not propagate to the upstream integration + the
auto-verify does not run + the path switch does not
notify + the Stealth-mode suppression does not suppress).

### §8.1 Kill-switch ON → enable remote access

The automation fires when the
`binary_sensor.rc_remote_access_enabled` tile flips to ON
AND the `select.rc_remote_access_path` tile is set to a
valid path (one of `tailscale` / `cloudflare_tunnel` /
`nabu_casa` / `wireguard`). The automation calls the
upstream integration's enable service so the chosen
remote-access path is fully active.

```yaml
alias: "Remote access: kill-switch ON enables remote access"
description: "Enable the chosen remote-access path when the kill-switch flips ON"
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.rc_remote_access_enabled
    to: "on"
condition:
  - condition: not
    conditions:
      - condition: state
        entity_id: select.rc_remote_access_path
        state: "none"
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: select.rc_remote_access_path
            state: "tailscale"
        sequence:
          - service: tailscale.start
            data: {}
      - conditions:
          - condition: state
            entity_id: select.rc_remote_access_path
            state: "cloudflare_tunnel"
        sequence:
          - service: hassio.addon_start
            data:
              addon: "core_cloudflared"
      - conditions:
          - condition: state
            entity_id: select.rc_remote_access_path
            state: "nabu_casa"
        sequence:
          - service: cloud.remote_connect
            data: {}
      - conditions:
          - condition: state
            entity_id: select.rc_remote_access_path
            state: "wireguard"
        sequence:
          - service: hassio.addon_start
            data:
              addon: "core_wireguard"
    default: []
```

### §8.2 Kill-switch OFF → disable remote access

The automation fires when the
`binary_sensor.rc_remote_access_enabled` tile flips to
OFF. The automation calls the upstream integration's
disable service so the chosen remote-access path is fully
torn down when the operator chooses to disable remote
access.

```yaml
alias: "Remote access: kill-switch OFF disables remote access"
description: "Disable the chosen remote-access path when the kill-switch flips OFF"
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.rc_remote_access_enabled
    to: "off"
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: select.rc_remote_access_path
            state: "tailscale"
        sequence:
          - service: tailscale.stop
            data: {}
      - conditions:
          - condition: state
            entity_id: select.rc_remote_access_path
            state: "cloudflare_tunnel"
        sequence:
          - service: hassio.addon_stop
            data:
              addon: "core_cloudflared"
      - conditions:
          - condition: state
            entity_id: select.rc_remote_access_path
            state: "nabu_casa"
        sequence:
          - service: cloud.remote_disconnect
            data: {}
      - conditions:
          - condition: state
            entity_id: select.rc_remote_access_path
            state: "wireguard"
        sequence:
          - service: hassio.addon_stop
            data:
              addon: "core_wireguard"
    default: []
```

### §8.3 Auto-verify every 15 minutes

The automation fires every 15 minutes + calls the
`button.rc_remote_access_verify_now` button (which fires
an upstream reachability probe) + updates the
`sensor.rc_remote_access_last_verified_minutes_ago`
freshness gate.

```yaml
alias: "Remote access: auto-verify every 15 minutes"
description: "Periodically verify the remote-access path is reachable"
mode: single
trigger:
  - platform: time_pattern
    minutes: "/15"
condition:
  - condition: state
    entity_id: binary_sensor.rc_remote_access_enabled
    state: "on"
action:
  - service: button.press
    target:
      entity_id: button.rc_remote_access_verify_now
    data: {}
  - service: input_datetime.set_datetime
    target:
      entity_id: input_datetime.rc_remote_access_last_verified
    data:
      datetime: "{{ now().isoformat() }}"
```

### §8.4 Notify on path switch

The automation fires when the
`select.rc_remote_access_path` tile changes from one path
to another. The automation sends a notification to the
operator's phone (via the HA Companion app) saying
"Remote access path switched from <old_path> to
<new_path> — verify reachability at
<sensor.rc_remote_access_url>".

```yaml
alias: "Remote access: notify on path switch"
description: "Notify the operator when the remote-access path changes"
mode: single
trigger:
  - platform: state
    entity_id: select.rc_remote_access_path
action:
  - service: notify.mobile_app
    data:
      title: "Remote access path switched"
      message: >-
        Remote access path switched from
        {{ trigger.from_state.state }} to
        {{ trigger.to_state.state }}.
        Verify reachability at
        {{ states('sensor.rc_remote_access_url') }}.
      data:
        tag: "roamcore-remote-access-path-switch"
```

### §8.5 Stealth-mode suppression via `select.rc_mode`

The automation SUPPRESSES the §8.1 kill-switch-ON
automation when the `select.rc_mode` is in `stealth` mode
(campgrounds with quiet hours + overnight stays where
exposing the HA server remotely would be a privacy
concern). The automation is a guard: the §8.1
automation's trigger is guarded by the `select.rc_mode`
NOT being in `stealth` mode.

```yaml
alias: "Remote access: Stealth-mode suppression"
description: "Suppress remote access when in Stealth mode (campground quiet hours)"
mode: single
trigger:
  - platform: state
    entity_id: select.rc_mode
    to: "stealth"
action:
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.rc_remote_access_enabled
    data: {}
  - service: notify.mobile_app
    data:
      title: "Remote access suppressed (Stealth mode)"
      message: >-
        Stealth mode is ON. Remote access has been
        disabled to protect privacy at the campground.
```

The recipe §11 cross-references the mode/automation-
builder recipe (Wave 2 #23) for the `select.rc_mode` tile.

## §9 Troubleshooting

### §9.1 Remote access not reachable

The most common cause is one of:
- **Kill-switch OFF.** The `binary_sensor.rc_remote_access_
  enabled` tile is FALSE. Action: set the kill-switch to
  TRUE (toggle the `input_boolean.rc_remote_access_enabled`
  helper via the dashboard + the HA Companion app).
- **Upstream integration not configured.** The chosen path's
  upstream integration (HA core `tailscale` integration +
  HACS `cloudflared` add-on + HA Core `cloud` integration
  + HACS `wireguard` add-on) is NOT configured. Action:
  follow the §3 / §4 / §5 / §6 setup steps for the chosen
  path.
- **MagicDNS not enabled (Path A).** The Tailscale
  MagicDNS is NOT enabled in the Tailscale admin console.
  Action: enable MagicDNS in the Tailscale admin console
  (https://login.tailscale.com/admin/dns).
- **Cloudflare Tunnel not running (Path B).** The HACS
  `cloudflared` add-on is NOT running. Action: start the
  add-on (Settings → Add-ons → Cloudflared → Start).
- **Nabu Casa subscription lapsed (Path C).** The Nabu
  Casa subscription has lapsed. Action: renew the
  subscription via the HA Cloud panel.
- **Wireguard tunnel down (Path D).** The Wireguard
  server interface is NOT running. Action: start the
  HACS `wireguard` add-on (Settings → Add-ons →
  Wireguard → Start) + verify the server interface is
  up.

### §9.2 Hostname not resolving

The most common cause is one of:
- **MagicDNS not enabled (Path A).** See §9.1.
- **Cloudflare DNS not resolving (Path B).** The
  Cloudflare DNS is NOT resolving the public hostname
  (e.g. `ha.example.com`). Action: check the Cloudflare
  dashboard (https://dash.cloudflare.com/) + verify the
  tunnel is up + the public hostname is configured.
- **Nabu Casa remote URL blank (Path C).** The
  `sensor.home_assistant_cloud_remote` is blank. Action:
  check the HA Cloud panel (Settings → Home Assistant
  Cloud) + verify remote access is enabled + the
  subscription is active.
- **Wireguard server endpoint not reachable (Path D).**
  The Wireguard server endpoint is NOT reachable from the
  client. Action: check the firewall permits inbound
  UDP 51820 + check the home router's port-forwarding
  rules + check the Wireguard server interface is up.

### §9.3 Cloudflare Tunnel 1033/1034 errors

The most common cause is one of:
- **Origin certificate missing.** The Cloudflare Tunnel
  requires an origin certificate on the HA server. Action:
  download the origin certificate from the Cloudflare
  dashboard + install it on the HA server.
- **`cloudflared` not running.** The HACS `cloudflared`
  add-on is NOT running. Action: start the add-on (see
  §9.1).
- **Cloudflare account suspended.** The Cloudflare account
  has been suspended. Action: contact Cloudflare support
  to resolve the suspension.

### §9.4 Nabu Casa remote URL blank

The most common cause is one of:
- **HA Cloud panel not subscribed.** The operator has NOT
  subscribed to Nabu Casa HA Cloud. Action: subscribe via
  the HA Cloud panel (see §5).
- **Nabu Casa account lapsed.** The Nabu Casa subscription
  has lapsed. Action: renew the subscription (see §9.1).
- **HA Core not connected to Nabu Casa.** The HA Core
  `cloud` integration is NOT connected to Nabu Casa.
  Action: check the integration (Settings → Devices &
  Services → Home Assistant Cloud) + re-authenticate if
  necessary.

### §9.5 Wireguard handshake failing

The most common cause is one of:
- **Server keys mismatch.** The server's private key in
  `/etc/wireguard/wg0.conf` does NOT match the server's
  public key in the client's configuration. Action:
  regenerate the server keys + update the server's
  configuration + update the client's configuration.
- **Client keys mismatch.** The client's private key in
  the client's configuration does NOT match the client's
  public key in the server's peer list. Action:
  regenerate the client keys + update the client's
  configuration + update the server's peer list.
- **Firewall blocking UDP port.** The HA server's firewall
  + the home router's port-forwarding rules do NOT permit
  inbound UDP 51820. Action: open inbound UDP 51820 on
  the firewall + the port-forwarding rules.
- **HA server clock skew.** The HA server's clock is
  skewed (Wireguard requires the clocks to be within a
  few minutes of each other for the handshake to succeed).
  Action: check the HA server's clock + enable NTP.

### §9.6 Path-switch leaves stale hostname in `sensor.rc_remote_access_url`

The most common cause is one of:
- **Template not re-rendering.** The
  `sensor.rc_remote_access_url` template does NOT
  re-render on the `select.rc_remote_access_path` change.
  Action: check the template's `trigger:` entities + add
  the `select.rc_remote_access_path` entity to the
  template's `trigger:` list.
- **Stale `input_text`.** The
  `input_text.rc_remote_access_url` is stale. Action:
  manually update the `input_text` via the dashboard.
- **Path-specific sensor not updated.** The path-specific
  sensor (e.g. `sensor.tailscale_hostname` for Path A) is
  NOT updated. Action: check the upstream integration's
  state + force a refresh via the integration's service.

## §10 Privacy

The remote-access paths produce no telemetry beyond the
chosen vendor's standard logs. The privacy posture:

- **No RoamCore-side telemetry.** The 9
  `rc_remote_access_*` contract tiles are computed locally
  on the HA instance; no RoamCore-side telemetry is sent.
- **Tailscale logs are operator-owned via the Tailscale
  admin console.** Path A — Tailscale — exposes the
  operator's tailnet device status + the per-device
  reachability state via the Tailscale admin console. The
  logs are operator-owned; RoamCore does NOT have access
  to the Tailscale admin console.
- **Cloudflare Tunnel logs are operator-owned via the
  Cloudflare dashboard.** Path B — Cloudflare Tunnel —
  exposes the tunnel status + the public hostname +
  the request logs via the Cloudflare dashboard. The logs
  are operator-owned; RoamCore does NOT have access to
  the Cloudflare dashboard.
- **Nabu Casa logs are operator-owned via the HA Cloud
  panel.** Path C — Nabu Casa HA Cloud — exposes the
  remote URL + the subscription status + the request logs
  via the HA Cloud panel. The logs are operator-owned;
  RoamCore does NOT have access to the HA Cloud panel.
- **Wireguard logs are operator-owned on the HA server.**
  Path D — Wireguard — exposes the server interface status
  + the peer list + the handshake logs on the HA server
  itself. The logs are operator-owned; RoamCore does NOT
  have access to the HA server.

The recipe does NOT collect any personally identifiable
information (PII) about the operator's remote-access paths.
The 9 `rc_remote_access_*` contract tiles are computed
locally on the HA instance; the chosen vendor's logs are
operator-owned via the chosen vendor's console; no
RoamCore-side telemetry is sent.

## §11 Promoting to tier-a

To promote the remote-access connection from tier-b to
tier-a, the following would need to happen:

1. **Real remote-access bench on CI.** RoamCore would need
   a CI bench with all FOUR upstream integrations installed
   + the operator's account on the chosen vendor's service
   + canned fixture responses for reachability probes. The
   bench is the canonical "integration test" target for
   remote access.
2. **RoamCore-owned operator-wired setup flow.** RoamCore
   would need a `config_flow.py` for the remote-access
   integration that walks the operator through path
   selection + the chosen path's upstream integration +
   the kill-switch + the path selector. The setup flow is
   the canonical "operator-wired" affordance that
   distinguishes tier-b from tier-a.
3. **Integration tests asserting:**
   - The kill-switch ON enables the chosen remote-access
     path (the upstream integration's enable service is
     called + the path is verified reachable).
   - The kill-switch OFF disables the chosen remote-access
     path (the upstream integration's disable service is
     called + the path is verified unreachable).
   - The auto-verify every 15 minutes updates the
     freshness gate.
   - The path switch notification fires + sends the
     notification to the operator's phone.
   - The Stealth-mode suppression suppresses the §8.1
     kill-switch-ON automation when the `select.rc_mode`
     is in `stealth` mode.
   - The contract tiles reflect the current state of the
     remote-access setup (kill-switch + URL + active gate +
     active-path indicator + peer count + freshness gate +
     hostname-resolvable gate + verify-now button + path
     selector).

The tier-a promotion is BLOCKED on the real remote-access
bench; until the bench fixture lands, the remote-access
connection is tier-b.

## §12 Files in this connection + cross-references

### Files

- `connections/remote-access/connection.yml` — the
  source-of-truth manifest.
- `connections/remote-access/__init__.py` — the
  `DOMAIN = "remote_access"` marker for the audit.
- `connections/remote-access/README.md` — the folder
  overview.
- `connections/remote-access/docs/recipe.md` — the full
  howto.
- `connections/remote-access/tests/test_connection_yml.py`
  — the manifest honesty checks.

### Cross-references

- **HA core `tailscale` integration** (the canonical Path A
  mesh VPN; since 2022.x) —
  https://www.home-assistant.io/integrations/tailscale/
- **HA Core `cloud` integration** (the canonical Path C
  Nabu Casa HA Cloud relay; since 2022.x) —
  https://www.home-assistant.io/integrations/cloud/
- **HACS `cloudflared` add-on** (the canonical Path B
  Cloudflare Tunnel daemon; HACS) —
  https://github.com/hassio-addons/addon-cloudflared
- **HACS `wireguard` add-on** (the canonical Path D
  Wireguard self-hosted VPN; HACS) —
  https://hacs.xyz/docs/integrations/active
- **HA Companion app `external_url` setting** (the canonical
  OFF-LAN affordance; since 2022.x) —
  https://companion.home-assistant.io/docs/core/sensors
- **Wave 2 #29 Tailscale contract**
  (`feat/wave2-remote-access-tailscale` @ `0caa9c2`) —
  `homeassistant/packages/roamcore_remote_access.yaml`
- **Mode/automation-builder recipe** (the `select.rc_mode`
  tile source of truth for the §8.5 Stealth-mode
  suppression; Wave 2 #23) —
  `connections/smart-automations/`
- **Approach lights** (the canonical ON-LAN-only lighting
  scene that Stealth-mode suppresses; Wave 3 #52) —
  `connections/approach-lights/`
- **NFC tags** (the optional `tag_id → scene` mapping table
  for toggling the kill-switch via NFC scan; Wave 3 #57) —
  `connections/nfc-tags/`
- **RoamCore entity naming** —
  `docs/reference/rc-entity-naming.md` (the
  `remote_access` subsystem was added by this slice)