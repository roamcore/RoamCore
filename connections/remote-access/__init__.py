"""Remote access (vendor-neutral remote-access umbrella for HA —
Tailscale + Cloudflare Tunnel + Nabu Casa HA Cloud + Wireguard, the
operator picks ONE path) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship
native HA integration code; they publish a recipe
(docs/recipe.md) that walks the operator through installing ONE OR
MORE of the FOUR operator-pickable remote-access paths:

  - Path A — Tailscale (mesh VPN, default for most operators).
    The operator installs the HA core `tailscale` integration
    (since 2022.x — exposes tailnet device status via the
    `binary_sensor.tailscale_*` entities + the
    `device_tracker.tailscale_*` entities from the operator's
    tailnet) OR the HACS Tailscale add-on + logs in to Tailscale
    + enables MagicDNS + adds the operator's devices to the
    tailnet. Path A is the default for any van operator who wants
    a secure mesh VPN without opening inbound ports + with
    MagicDNS hostname resolution (the HA server is reachable as
    `https://<host>.ts.net`). Path A was the Wave 2 #29 focus
    (`feat/wave2-remote-access-tailscale` @ `0caa9c2`) — that
    branch already shipped the Tailscale-specific contract at
    `homeassistant/packages/roamcore_remote_access.yaml`. This
    slice lifts the Wave 2 contract into the `connections/`
    pipeline + ADDS the broader vendor-neutral contract layer.

  - Path B — Cloudflare Tunnel (no inbound ports, default for
    operators with a Cloudflare-managed domain). The operator
    creates a Cloudflare account + adds the operator's domain to
    Cloudflare + creates a Cloudflare Tunnel pointing at the HA
    server's local URL + installs the `cloudflared` daemon on
    the HA server via the HACS `cloudflared` add-on (HACS —
    installs the `cloudflared` daemon that tunnels traffic
    through Cloudflare's edge to the HA server's local URL
    without opening inbound ports) OR the official Cloudflare
    Tunnel integration. Path B is the default for any van
    operator who already has a Cloudflare-managed domain + who
    wants to expose the HA server without opening inbound ports
    on the HA server's firewall + who wants Cloudflare's edge
    caching + DDoS protection for the remote-access path.

  - Path C — Nabu Casa HA Cloud (Home Assistant's official cloud
    relay). The operator subscribes to Nabu Casa HA Cloud via
    the HA Cloud panel + enables remote access + the HA Core
    `cloud` integration (since 2022.x — exposes the Nabu Casa
    HA Cloud remote URL via `sensor.home_assistant_cloud_remote`
    + the `cloud.remote_connect` / `cloud.remote_disconnect`
    services) exposes the remote URL. Path C is the default for
    any van operator who wants the HA Core official cloud relay
    + who does NOT want to manage a self-hosted VPN server + who
    is willing to pay for the subscription. Nabu Casa is paid;
    the operator subscribes directly via the HA Cloud panel.

  - Path D — Wireguard (manual VPN, default for operators who
    prefer self-hosted VPN over managed services). The operator
    installs the HACS `wireguard` add-on (HACS — installs the
    Wireguard server in the HA server + generates server keys +
    generates per-client keys + exposes the VPN interface for
    manual peer management) OR a manual Wireguard install +
    configures the Wireguard server interface + adds the
    operator's devices as Wireguard peers + configures firewall
    rules + verifies the VPN tunnel. Path D is the default for
    any van operator who prefers a self-hosted VPN (no third-
    party relay + no subscription) + who is comfortable with
    per-client key management + who wants full control over the
    VPN configuration.

The umbrella publishes the resulting data via the upstream
Tailscale integration + the HACS `cloudflared` add-on + the HA
Core `cloud` integration + the HACS `wireguard` add-on + the HA
Companion app's `external_url` setting (since 2022.x — points the
operator's phone at the chosen remote-access URL when the
operator is OFF-LAN), then publishes the RoamCore remote-access
contract tiles on top (the 9 contract entities documented in
connection.yml — 1 binary_sensor operator-kill-switch + 1 sensor
remote-access URL + 1 binary_sensor active gate + 1 sensor
active-path indicator + 1 sensor peer count + 1 sensor last-
verified minutes ago + 1 binary_sensor hostname-resolvable gate
+ 1 button verify-now + 1 select operator-chosen path).

The audit + boundary CI can detect a `remote-access/` folder that
claims to be a connection via the `DOMAIN` constant exported
here. The wizard reads the manifest + recipe at runtime.

The real per-operator remote-access affordance path is:

    Operator-side choice of ONE path (Path A — Tailscale mesh
        VPN via the HA core `tailscale` integration OR the HACS
        Tailscale add-on; Path B — Cloudflare Tunnel via the
        HACS `cloudflared` add-on; Path C — Nabu Casa HA Cloud
        via the HA Core `cloud` integration; Path D — Wireguard
        self-hosted VPN via the HACS `wireguard` add-on)
        -> upstream entity (HA core `tailscale` integration's
           `binary_sensor.tailscale_*` entities + the
           `device_tracker.tailscale_*` entities for Path A;
           the HACS `cloudflared` add-on's daemon status + the
           Cloudflare Tunnel hostname for Path B; the HA Core
           `cloud` integration's
           `sensor.home_assistant_cloud_remote` + the
           `cloud.remote_connect` / `cloud.remote_disconnect`
           services for Path C; the HACS `wireguard` add-on's
           peer list + the Wireguard server interface status
           for Path D)
        -> RoamCore contract layer (HA core `template:` sensor
           + binary_sensor + the operator's `input_boolean` /
           `input_text` / `input_select` for the kill-switch +
           the URL + the path selector + the `button`
           integration for the verify-now button + the
           `command_line` integration for the upstream
           reachability probe)
        -> dashboard tiles + OpenClaw queries
            ("is remote access enabled?",
             "what is the URL to access Home Assistant
              remotely?",
             "is remote access currently active?",
             "which remote-access path is currently active?",
             "how many remote-access clients are currently
              connected?",
             "when was remote access last verified?",
             "does the remote-access hostname resolve?",
             "trigger a remote-access verification now",
             "which remote-access path should I use?")

    Safety interlocks (the recipe is the contract layer; the
    automation wrappers are documented in §8):
        -> The RoamCore kill-switch-ON automation is the §8.1
           automation that fires when the
           `binary_sensor.rc_remote_access_enabled` tile flips
           to ON AND the `select.rc_remote_access_path` tile is
           set to a valid path. The automation calls the
           upstream integration's enable service so the chosen
           remote-access path is fully active.
        -> The RoamCore kill-switch-OFF automation is the §8.2
           automation that fires when the
           `binary_sensor.rc_remote_access_enabled` tile flips
           to OFF. The automation calls the upstream
           integration's disable service so the chosen remote-
           access path is fully torn down when the operator
           chooses to disable remote access.
        -> The RoamCore auto-verify automation is the §8.3
           automation that fires every 15 minutes + calls the
           `button.rc_remote_access_verify_now` button (which
           fires an upstream reachability probe) + updates the
           `sensor.rc_remote_access_last_verified_minutes_ago`
           freshness gate.
        -> The RoamCore notify-on-path-switch automation is the
           §8.4 automation that fires when the
           `select.rc_remote_access_path` tile changes from one
           path to another. The automation sends a notification
           to the operator's phone (via the HA Companion app)
           saying "Remote access path switched from <old_path>
           to <new_path> — verify reachability at
           <sensor.rc_remote_access_url>".
        -> The RoamCore Stealth-mode suppression automation is
           the §8.5 automation that SUPPRESSES the §8.1 kill-
           switch-ON automation when the `select.rc_mode` is in
           `stealth` mode (campgrounds with quiet hours +
           overnight stays where exposing the HA server
           remotely would be a privacy concern). The recipe §12
           cross-references the mode/automation-builder recipe
           (Wave 2 #23) for the `select.rc_mode` tile.

    Cross-references:
        -> The HA core `tailscale` integration is the canonical
           Path A mesh VPN (since 2022.x).
        -> The HACS `cloudflared` add-on is the canonical Path B
           Cloudflare Tunnel daemon (HACS).
        -> The HA Core `cloud` integration is the canonical
           Path C Nabu Casa HA Cloud relay (since 2022.x).
        -> The HACS `wireguard` add-on is the canonical Path D
           Wireguard self-hosted VPN (HACS).
        -> The HA Companion app's `external_url` setting is the
           canonical OFF-LAN affordance for the operator's
           phone (since 2022.x).
        -> The mode/automation-builder recipe Wave 2 #23
           cross-references the `select.rc_mode` tile (the
           Stealth-mode suppression source of truth).
        -> The Wave 2 #29 `feat/wave2-remote-access-tailscale`
           branch cross-references the existing Tailscale
           contract layer at
           `homeassistant/packages/roamcore_remote_access.yaml`
           (the Wave 2 contract layer for Path A only; this
           slice LIFTS that into the `connections/` pipeline +
           ADDS the broader vendor-neutral contract layer +
           ADDS Cloudflare Tunnel + Nabu Casa + Wireguard as
           alternative paths so the operator is not locked to
           Tailscale).
        -> The approach-lights Wave 3 #52 connection
           cross-references the canonical ON-LAN-only lighting
           scene that Stealth-mode suppresses.

See docs/recipe.md for the full howto (HA core `tailscale`
integration install + HACS `cloudflared` add-on install + HA Core
`cloud` integration install + HACS `wireguard` add-on install +
Path A Tailscale mesh VPN wiring + Path B Cloudflare Tunnel
wiring + Path C Nabu Casa HA Cloud wiring + Path D Wireguard
self-hosted VPN wiring + the kill-switch + the path selector +
the FIVE §8 automations + the 9 `rc_remote_access_*` contract
tiles + the 6 §9 troubleshooting entries + privacy + tier-a
promotion outline).
"""

DOMAIN = "remote_access"