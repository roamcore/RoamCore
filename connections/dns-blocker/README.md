# Pi-hole / AdGuard Home (network-wide DNS ad blocker)

**Tier:** B (recipe)
**Category:** Networking
**Status:** beta

## What this connection is

Pi-hole and AdGuard Home are self-hosted DNS-level ad/tracker
blockers. Both work as a **DNS sinkhole**: every DNS query from
every device on the LAN is answered by the blocker, queries against
known ad/tracker domains are answered with `0.0.0.0` (or `NXDOMAIN`)
instead of the real IP, and legitimate queries are forwarded to an
upstream DNS resolver (Cloudflare / Quad9 / Google / the operator's
choice).

RoamCore uses the DNS blocker as the network-wide ad-blocking slice
for the van's LAN:

- **Saves bandwidth on LTE / Starlink** — ad/tracker traffic is
  cut at DNS resolution, so the cellular uplink never has to fetch
  the bytes in the first place. On a metered LTE plan this is the
  single biggest bandwidth win you can ship.
- **Faster browsing on weak connections** — pages load faster when
  half the third-party requests never resolve.
- **Simple "is DNS healthy?" monitoring** — one glance at the
  RoamCore dashboard tells you whether the blocker is up, what %
  of queries are blocked, and whether the upstream DNS is
  reachable.
- **Mode-aware pause / re-enable** — the recipe ships an automation
  that respects Stealth silent-hours (some vanlifers want raw DNS
  during certain stealth scenarios) and re-enables the blocker
  when the upstream DNS comes back.

The recipe covers **both** Pi-hole and AdGuard Home because they're
functionally equivalent (DNS sinkhole + blocklist + per-client
query stats + upstream DNS forwarding), and either one covers the
RoamCore `rc_net_dns_*` contract. Pick whichever fits your setup:

- **Path A — Pi-hole** (lightest footprint, ~50 MB RAM, mature).
  Best when you're running it on a Raspberry Pi or a tiny VM and
  don't need the richer AdGuard UI.
- **Path B — AdGuard Home** (richer UI, built-in DoH/DoT upstream
  encryption, per-client parental controls). Best when you want
  encrypted DNS upstream + a nicer admin UI.

Both have first-class Home Assistant core integrations with
working config_flows (Pi-hole's since 2021.8, AdGuard Home's since
2022.11). RoamCore does **not** ship a DNS blocker of its own — you
bring whichever blocker you want on your LAN, and RoamCore layers
the `rc_net_dns_*` contract tiles on top.

## Setup recipe (one-paragraph)

1. Decide Path A (Pi-hole) or Path B (AdGuard Home). Run the
   blocker on a Raspberry Pi, a mini PC, a VM on your Proxmox
   host, or as a Docker container — anywhere reachable from the
   RoamCore LAN with a static IP.
2. Wire the blocker into the LAN: assign it a static IP, point
   OpenWrt's DHCP options at it (so every LAN client gets the
   blocker as its only DNS server and can't bypass by hardcoding
   `8.8.8.8`), and configure the upstream DNS resolvers in the
   blocker's admin UI.
3. In Home Assistant → **Settings → Devices & Services → Add
   Integration**, search for **Pi-hole v6** (Path A) or **AdGuard
   Home** (Path B) and walk the upstream config_flow — enter the
   blocker's LAN URL + API token (Pi-hole) or credentials
   (AdGuard).
4. Create the `rc_net_dns_*` contract tiles by importing the
   recipe §5 snippet block (template sensors over the upstream
   `sensor.pi_hole_*` / `sensor.adguard_*` entities).
5. Enable the recipe §6 automations (blocklists-stale alert,
   Stealth-mode pause, upstream-DNS-down auto-re-enable).
6. Reload the RoamCore dashboard; the `rc_net_dns_*` contract
   tiles appear on the Networking section.

Full howto with copy-pasteable YAML for the helper templates,
the OpenWrt DHCP-options cross-reference, 3 automations, 6
troubleshooting entries, and the tier-a promotion outline: see
[`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration
tests against a real DNS blocker on CI, and `wizard.one_tap: true`.
We have no DNS blocker on the CI bench to integration-test against,
and the upstream Pi-hole / AdGuard Home integrations are operator-
chosen (Path A vs Path B). So this connection is honestly beta-tier:
the recipe is sound (it leans on the upstream HA core integration's
existing config_flow + the operator's own DNS-blocker deployment),
but we cannot claim one-tap automation from the RoamCore side.

The `install.config_flow: true` field in the manifest is
**UPSTREAM truth** (both Pi-hole and AdGuard Home have working
config_flows in HA core) — NOT a RoamCore-owned config_flow. The
`__init__.py` is a DOMAIN stub; there is no `config_flow.py` in
this folder. If we ever ship a native RoamCore-owned wrapper around
the upstream config_flow (e.g. a wizard-side helper that auto-
creates the `rc_net_dns_*` contract tiles post-config_flow), we'd
add a `config_flow.py` here, flip the tier to tier-a, and update
the test to assert the new flow is real.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "dns-blocker"` marker for the audit.
- `docs/recipe.md` — the full howto (Path A Pi-hole install +
  config_flow, Path B AdGuard Home install + config_flow,
  `rc_net_dns_*` template-helper wiring, OpenWrt DHCP-options
  cross-reference, 3 automations, 6 troubleshooting entries,
  tier-a promotion outline).
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog pages (now superseded by the connection manifest):
  - [`docs/catalog/homelab/pi-hole.md`](../../docs/catalog/homelab/pi-hole.md)
  - [`docs/catalog/homelab/adguard-home.md`](../../docs/catalog/homelab/adguard-home.md)
- Catalog category index: `docs/catalog/homelab/index.md`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
  (§net subsystem, `rc_net_dns_*` prefix).
- OpenWrt router controls (the DNS blocker plugs into the LAN
  behind OpenWrt's DHCP options — the OpenWrt router pushes the
  blocker's IP as the LAN's only DNS server):
  `connections/openwrt-controls/`
  (see `docs/catalog/networking/openwrt-controls.md`)
- Starlink mobile-internet slice (peers with DNS blocker under
  the §net subsystem): `connections/starlink/`
- Frigate NVR slice (uses the LAN but not the DNS subsystem):
  `connections/frigate/`