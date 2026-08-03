# Remote access (vendor-neutral remote-access umbrella for HA — Tailscale + Cloudflare Tunnel + Nabu Casa HA Cloud + Wireguard, operator picks ONE path)

**Tier:** B (recipe)
**Category:** networking
**Status:** beta

## What this connection is

Remote access (vendor-neutral remote-access umbrella for HA, covering Tailscale + Cloudflare Tunnel + Nabu Casa HA Cloud + Wireguard — operator picks ONE path) — the umbrella for "check the van from anywhere: see sensor status, view cameras, get alerts, or (optionally) control systems" — is the networking-category complement to the broader RoamCore scene + automation affordances. The single "is remote access enabled?" tile aggregates the operator kill-switch into one dashboard indicator; the "the URL to access HA remotely" tile surfaces the chosen-path URL (the mesh-VPN hostname for Path A + the Cloudflare Tunnel hostname for Path B + the Nabu Casa remote URL for Path C + the Wireguard server endpoint for Path D); the "is remote access active?" tile is the AND gate (TRUE iff the kill-switch is ON AND at least one remote-access path is verified reachable); the "which path is currently active?" tile surfaces the operator's chosen path (one of `tailscale` / `cloudflare_tunnel` / `nabu_casa` / `wireguard` / `companion_external_url` / `none`); the "remote-access peer count" tile surfaces the count of remote-access clients currently connected (Tailscale-only); the "last-verified minutes ago" tile is the freshness gate; the "hostname resolvable" tile surfaces whether the chosen path's hostname resolves; the "verify-now" button surfaces the manual verification trigger; the "operator-chosen path" selector is the operator-facing affordance.

RoamCore ships **no** native remote-access engine. We RECIPE the well-understood upstream Tailscale integration (HA core `tailscale` integration since 2022.x — exposes tailnet device status via the `binary_sensor.tailscale_*` entities + the `device_tracker.tailscale_*` entities from the operator's tailnet) + the HACS `cloudflared` add-on (HACS — installs the `cloudflared` daemon that tunnels traffic through Cloudflare's edge to the HA server's local URL without opening inbound ports) + the HA Core `cloud` integration (since 2022.x — exposes the Nabu Casa HA Cloud remote URL via `sensor.home_assistant_cloud_remote` + the `cloud.remote_connect` / `cloud.remote_disconnect` services) + the HACS `wireguard` add-on (HACS — installs the Wireguard server in the HA server + generates per-client keys + exposes the VPN interface for manual peer management) + the HA Companion app's `external_url` setting (since 2022.x — points the operator's phone at the chosen remote-access URL when the operator is OFF-LAN). The 9 `rc_remote_access_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual remote-access path is provided by the upstream Tailscale integration + the HACS `cloudflared` add-on + the HA Core `cloud` integration + the HACS `wireguard` add-on (RoamCore does NOT fork any of these).

## The 4 operator-pickable paths

- **Path A — Tailscale (mesh VPN).** Default for operators who want a secure mesh VPN without opening inbound ports + with MagicDNS hostname resolution (`https://<host>.ts.net`). Installed via the HA core `tailscale` integration OR the HACS Tailscale add-on. Cross-references the Wave 2 #29 branch (`feat/wave2-remote-access-tailscale` @ `0caa9c2`) which shipped the Tailscale-specific contract at `homeassistant/packages/roamcore_remote_access.yaml`.

- **Path B — Cloudflare Tunnel (no inbound ports).** Default for operators with a Cloudflare-managed domain who want to expose the HA server without opening inbound ports + with Cloudflare's edge caching + DDoS protection. Installed via the HACS `cloudflared` add-on OR the official Cloudflare Tunnel integration. The `cloudflared` daemon tunnels traffic through Cloudflare's edge to the HA server's local URL.

- **Path C — Nabu Casa HA Cloud (official cloud relay).** Default for operators who want the HA Core official cloud relay + who do NOT want to manage a self-hosted VPN server + who are willing to pay for the subscription. Activated via the HA Cloud panel + the HA Core `cloud` integration. Nabu Casa is paid; the operator subscribes directly via the HA Cloud panel.

- **Path D — Wireguard (manual VPN).** Default for operators who prefer self-hosted VPN (no third-party relay + no subscription) + who are comfortable with per-client key management. Installed via the HACS `wireguard` add-on OR a manual Wireguard install. The operator generates server keys + per-client keys + configures the Wireguard server interface + adds the operator's devices as Wireguard peers + configures firewall rules.

The HA Companion app's `external_url` setting (since 2022.x) is the canonical OFF-LAN affordance: it points the operator's phone at the chosen remote-access URL when the operator is OFF-LAN. The Companion external URL is NOT a separate remote-access path; it's the Companion app's affordance for using one of the four paths above.

## Setup recipe (one-paragraph)

1. Have an always-on HA instance reachable from the operator's home network.
2. Pick ONE of the four paths (Path A / Path B / Path C / Path D).
3. Set up the chosen path:
   - **Path A — Tailscale:** install the HA core `tailscale` integration OR the HACS Tailscale add-on + login to Tailscale + enable MagicDNS + add the operator's devices to the tailnet.
   - **Path B — Cloudflare Tunnel:** create a Cloudflare account + add the operator's domain to Cloudflare + create a Cloudflare Tunnel pointing at the HA server's local URL + install the `cloudflared` daemon via the HACS `cloudflared` add-on OR the official Cloudflare Tunnel integration.
   - **Path C — Nabu Casa HA Cloud:** subscribe to Nabu Casa HA Cloud via the HA Cloud panel + enable remote access + verify the Nabu Casa remote URL.
   - **Path D — Wireguard:** install the HACS `wireguard` add-on OR a manual Wireguard install + generate server keys + generate per-client keys + configure the Wireguard server interface + add the operator's devices as Wireguard peers + configure firewall rules.
4. Configure the HA server's firewall to permit the chosen path's port range (UDP 41641 for Path A + outbound HTTPS 7844 for Path B + outbound HTTPS for Path C + UDP 51820 for Path D).
5. Install the HA Companion app + configure the `external_url` setting to point at the chosen remote-access URL.
6. Configure the operator's DNS provider account if Path B is chosen (Cloudflare-managed domain + Cloudflare DNS).
7. Configure the `binary_sensor.rc_remote_access_enabled` kill-switch tile (set to TRUE).
8. Configure the `select.rc_remote_access_path` tile to the chosen path (one of `tailscale` / `cloudflare_tunnel` / `nabu_casa` / `wireguard`).
9. Wire the FIVE §8 automations (kill-switch ON enables remote access + kill-switch OFF disables remote access + auto-verify every 15 minutes + notify on path switch + Stealth-mode suppression via `select.rc_mode`).
10. Verify: check `sensor.rc_remote_access_url` reflects the chosen path's URL + check `binary_sensor.rc_remote_access_active` is TRUE + trigger the `button.rc_remote_access_verify_now` button + verify reachability.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a would require a RoamCore-owned remote-access engine + integration code + integration tests against a real remote-access bench (a controlled environment with Tailscale coordination server + Cloudflare Tunnel token + Nabu Casa test subscription + Wireguard server + canned fixture responses for reachability probes). We have no operator-side remote-access bench on the CI to integration-test against (the bench requires the four upstream integrations + the operator's account on the chosen vendor's service + canned fixture responses for reachability probes — all wired together in a controlled environment). Tier-b is the honest tier: Tailscale + Cloudflare Tunnel + Nabu Casa + Wireguard are all upstream / vendor / HACS code (not RoamCore-owned); the RoamCore wrapper is a thin path-routing layer + the contract layer. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (`docs/catalog/remote-access/index.md` — 16-line stub, originally listed ONLY Tailscale at "Support tier: B" with no recipe + no contract + no broader vendor-neutral coverage — just a placeholder about "check sensor status, view cameras, get alerts, or (optionally) control systems" + "safe ways to reach Home Assistant remotely, with clear notes on security and support level") is now superseded by this tier-b recipe connection. The Wave 2 #29 branch (`feat/wave2-remote-access-tailscale` @ `0caa9c2`) already shipped the Tailscale-specific contract layer at `homeassistant/packages/roamcore_remote_access.yaml` — this slice lifts that contract into the `connections/` pipeline + adds the broader vendor-neutral contract layer + adds Cloudflare Tunnel + Nabu Casa + Wireguard as alternative paths.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "remote_access"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [`docs/catalog/remote-access/index.md`](../../docs/catalog/remote-access/index.md)
- Legacy Tailscale catalog page (now superseded by this slice): [`docs/catalog/remote-access/tailscale.md`](../../docs/catalog/remote-access/tailscale.md)
- HA core `tailscale` integration (Path A): https://www.home-assistant.io/integrations/tailscale/
- HA Core `cloud` integration (Path C): https://www.home-assistant.io/integrations/cloud/
- HA Companion app external URL docs: https://companion.home-assistant.io/docs/core/sensors
- HACS `cloudflared` add-on (Path B): https://hacs.xyz/docs/integrations/active
- HACS `wireguard` add-on (Path D): https://hacs.xyz/docs/integrations/active
- Wave 2 #29 Tailscale contract (`feat/wave2-remote-access-tailscale` @ `0caa9c2`): `homeassistant/packages/roamcore_remote_access.yaml`
- Mode/automation-builder (the `select.rc_mode` tile source of truth for the §8.5 Stealth-mode suppression): `connections/smart-automations/` (Wave 2 #23)
- Approach lights (the canonical ON-LAN-only lighting scene that Stealth-mode suppresses): `connections/approach-lights/` (Wave 3 #52)
- RoamCore entity naming: `docs/reference/rc-entity-naming.md` (the `remote_access` subsystem was added by this slice)