"""Pi-hole / AdGuard Home (network-wide DNS ad blocker) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up either Pi-hole (Path A) or AdGuard Home
(Path B) as a separate LAN service (Docker container, bare-metal
Raspberry Pi / mini PC, VM on Proxmox, or the community HA add-on),
exposing it on the LAN with a static IP, and letting HA's upstream
UI walk pick it up.

Both upstream integrations have a working entry in HA core:
  - Pi-hole (ha_integration_domain: pi_hole) since 2021.8
  - AdGuard Home (ha_integration_domain: adguard) since 2022.11

RoamCore does NOT ship a RoamCore-owned wrapper around either
upstream; the upstream-truth flag in connection.yml reflects
UPSTREAM truth (the operator adds the integration via HA's own
setup), NOT a RoamCore-owned flow.

The audit + boundary CI can detect a `dns-blocker/` folder that claims
to be a connection via the `DOMAIN` constant exported here. The wizard
reads the manifest + recipe at runtime.

The real DNS-blocker path is:

    Pi-hole (Path A) or AdGuard Home (Path B)
        -> upstream HA setup (pi_hole entry or adguard entry)
        -> upstream sensor entities (sensor.pi_hole_blocked_today,
           sensor.adguard_blocked_today, etc.)
        -> RoamCore contract layer (rc_net_dns_blocked_today,
           rc_net_dns_blocked_pct, rc_net_dns_blocker_reachable,
           rc_net_dns_queries_total, rc_net_dns_blocker_enabled,
           rc_net_dns_resolver_status, rc_net_dns_gravity_updated)
        -> dashboard tiles + OpenClaw queries

    OpenWrt DHCP options (cross-reference)
        -> pushes the DNS blocker's IP as the LAN's only DNS server
        -> clients can't bypass by hardcoding 8.8.8.8

See docs/recipe.md for the full howto (Path A Pi-hole install +
setup, Path B AdGuard Home install + setup, the `rc_net_dns_*`
template-helper wiring, the OpenWrt DHCP-options cross-reference,
3 automations, 6 troubleshooting entries, and the tier-a promotion
outline).
"""

DOMAIN = "dns-blocker"