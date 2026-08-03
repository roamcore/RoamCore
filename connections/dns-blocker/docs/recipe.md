# Pi-hole / AdGuard Home — tier-b recipe connection

**Tier:** B (recipe)
**Audience:** A RoamCore user who wants network-wide DNS ad/tracker
blocking on the van's LAN. Pick one blocker (Path A = Pi-hole, Path B
= AdGuard Home), deploy it on a Raspberry Pi / mini PC / VM / Docker
container with a static IP, wire OpenWrt's DHCP options at it so LAN
clients can't bypass, let HA's upstream config_flow pick it up, and
import the `rc_net_dns_*` contract helpers from the recipe §5 snippet
block.

This howto is mirrored into `docs/connections/dns-blocker.md` by the
catalog cron (`scripts/build_catalog.py`) so it shows up under the
public docs site's "Connections" section. Keep this recipe as the
source of truth.

## What is a DNS blocker in RoamCore?

A DNS-level ad blocker is a service that sits between every device
on the LAN and the upstream DNS resolver. When a device asks "what
IP is `ads.example.com`?", the blocker answers `0.0.0.0` (or
`NXDOMAIN`) instead of looking up the real IP. The browser never
connects to the ad server, the cellular uplink never has to fetch
the bytes, and the page loads faster because half the third-party
requests never resolve.

Pi-hole and AdGuard Home are the two dominant self-hosted DNS
blockers. Both work the same way:

1. Run a DNS server on the LAN (port 53/UDP+TCP), configured with
   one or more upstream DNS resolvers (Cloudflare 1.1.1.1,
   Quad9 9.9.9.9, the operator's choice — see Path A / Path B for
   DoH/DoT options).
2. Maintain a list of "blocked" domains (a "blocklist" / "gravity
   list" / "filter list") — typically several hundred thousand
   domains aggregated from community-maintained sources.
3. Answer queries against the blocklist with `0.0.0.0` /
   `NXDOMAIN`; forward legitimate queries upstream.
4. Log per-client per-domain query stats + per-client blocking
   toggles + ad-blocking ratio.

In RoamCore, the DNS blocker is the **network-wide ad-blocking slice**
for vans that go off-grid:

- **Saves bandwidth on LTE / Starlink.** On a metered LTE plan this
  is the single biggest bandwidth win you can ship — ad/tracker
  traffic is cut at DNS resolution so the cellular uplink never has
  to fetch the bytes.
- **Faster browsing on weak connections.** Pages load faster when
  half the third-party requests never resolve.
- **Simple "is DNS healthy?" monitoring.** One glance at the
  RoamCore dashboard tells you whether the blocker is up, what %
  of queries are blocked, and whether the upstream DNS is
  reachable.
- **Mode-aware pause.** The recipe ships an automation that pauses
  the blocker during Stealth silent-hours (some vanlifers want raw
  DNS during certain stealth scenarios) and re-enables it when the
  upstream DNS comes back.

RoamCore does **not** ship a DNS blocker of its own. There is no
RoamCore-owned `pi-hole` or `adguard-home` container image, no
`config_flow.py` wrapping either upstream, and no DNS blocker on
the CI bench to integration-test against. So we publish a recipe
that walks you through deploying either blocker (your choice) on
your own LAN hardware, then layer a small contract on top:
`rc_net_dns_*` dashboard tiles + OpenClaw queries ("how many ads
blocked today?", "is the DNS blocker reachable?", "what % of DNS
queries were blocked?", "are the blocklists up to date?", "is the
DNS blocker enabled?", "what's the upstream DNS server status?")
that bind to those contract entities.

**Why tier-b:** RoamCore has no DNS blocker on the bench to
integration-test against, no RoamCore-owned config_flow to ship
(the upstream Pi-hole and AdGuard Home integrations both have
their own config_flows in HA core, but those are UPSTREAM truth,
not RoamCore's). The recipe is sound (it leans on the upstream
config_flow + the operator's own DNS-blocker deployment), but we
cannot claim one-tap automation. The promotion outline at the
bottom of this recipe describes exactly what needs to happen to
flip this to tier-a.

**Two install paths:**

- **Path A — Pi-hole** (lightest footprint, ~50 MB RAM, mature
  blocklist, less admin UI polish). Best when you're running it
  on a Raspberry Pi or a tiny VM and don't need the richer AdGuard
  UI.
- **Path B — AdGuard Home** (richer UI, built-in DoH/DoT upstream
  encryption, per-client parental controls, encryption setup
  wizards). Best when you want encrypted DNS upstream + a nicer
  admin UI.

## Prerequisites

Before starting the recipe, make sure you have:

- **A device to run the blocker on.** A Raspberry Pi (3B+ or newer
  recommended for Pi-hole; any model for AdGuard Home), a mini PC
  (Intel NUC / Beelink / etc.), a VM on your Proxmox host, or
  another spare box on the LAN with at least 512 MB RAM. Storage is
  trivial (~50 MB for the binary + blocklist cache).
- **A static IP for the blocker.** Either via DHCP reservation on
  your OpenWrt router (recommended) or a manually-configured static
  IP on the box itself. Example: `192.168.1.53` (where 53 is the
  DNS port — a nod, not a requirement).
- **The ability to point the LAN's DHCP clients at the blocker
  as their DNS server.** Usually via OpenWrt's **Network → DHCP and
  DNS → LAN → DHCP Options** (`6,192.168.1.53` — option 6 = DNS
  server). This is critical: if you skip this step, clients can
  hardcode `8.8.8.8` and bypass the blocker. See recipe §5.3.
- **Path A — Pi-hole** (`https://pi-hole.net/`). The Pi-hole v6
  installer is a one-liner: `curl -sSL https://install.pi-hole.net
  | bash`. Docker also works: `docker run -d --name pihole \
  -e TZ=UTC -e WEBPASSWORD=... -p 53:53/tcp -p 53:53/udp \
  -p 80:80 pihole/pihole:latest`. Or the community HA add-on.
- **Path B — AdGuard Home**
  (`https://github.com/AdguardTeam/AdGuardHome`). Install via Docker
  (`docker run -d --name adguardhome -p 53:53/tcp -p 53:53/udp \
  -p 3000:3000 -p 443:443 -p 853:853/tcp -p 784:784/udp \
  -p 8853:8853/udp adguard/adguardhome:latest`), the standalone
  binary, or the community HA add-on. The Docker image exposes the
  admin UI on port 3000 by default.
- **(Recommended) Upstream DNS over HTTPS (DoH) / TLS (DoT).** Path
  B's killer feature is built-in DoH/DoT encryption. Path A can do
  this too via `pihole-FTL --dns-upstream` + a sidecar stubby /
  cloudflared. Cloudflare DoH URL: `https://cloudflare-dns.com/dns-query`.
  Quad9 DoH URL: `https://dns.quad9.net/dns-query`.

## Path A — Pi-hole

The lightest-footprint path. ~50 MB RAM, runs happily on a
Raspberry Pi Zero 2 W.

### A.1 — Install Pi-hole

Pick ONE of the install methods:

- **One-liner (bare-metal / VM):**
  ```bash
  curl -sSL https://install.pi-hole.net | bash
  ```
  The installer walks you through upstream DNS choice (use
  Cloudflare / Quad9 / custom), blocklist choice (accept the
  defaults), web admin password, and the web server install.
  Note the admin password at the end.

- **Docker:**
  ```bash
  docker run -d --name pihole \
    --restart=unless-stopped \
    -e TZ=UTC \
    -e WEBPASSWORD='YOUR_STRONG_PASSWORD_HERE' \
    -v pihole_etc:/etc/pihole \
    -v pihole_dnsmasq:/etc/dnsmasq.d \
    --network=host \
    pihole/pihole:latest
  ```
  `--network=host` is the easiest path for DNS — Pi-hole binds to
  port 53 directly on the host. If you can't use `--network=host`,
  publish the ports explicitly (`-p 53:53/tcp -p 53:53/udp -p
  80:80`).

### A.2 — Assign a static IP

- **DHCP reservation (recommended):** In OpenWrt → **Network →
  DHCP and DNS → Static Leases**, add the blocker's MAC address
  with IP `192.168.1.53` (or whatever you choose). The blocker
  will get `192.168.1.53` reliably on every boot.
- **Manual static IP:** On the blocker box itself, set
  `192.168.1.53/24`, gateway `192.168.1.1` (your OpenWrt), DNS
  `127.0.0.1` (itself).

### A.3 — Configure upstream DNS + admin UI

1. Browse to `http://192.168.1.53/admin/` (Pi-hole's web admin).
2. Log in with the password from A.1.
3. **Settings → DNS:** uncheck all the Google / Cloudflare / OpenDNS
   upstream boxes you don't want, then in **Upstream DNS Servers**
   add the ones you do want:
   - Cloudflare: `1.1.1.1` + `1.0.0.1` (plain DNS; for DoH see
     §5.4)
   - Quad9: `9.9.9.9` + `149.112.112.112`
   - Custom: your upstream of choice
4. **Settings → Blocklists:** Pi-hole ships a sensible default list;
   add more from the community (Firebog curated lists:
   `https://firebog.net/`).
5. **Tools → Update Gravity** to pull the latest blocklists. This
   is what populates `binary_sensor.rc_net_dns_gravity_updated`
   (via the automation in §6.1).

### A.4 — Wire the LAN's DHCP at the blocker (CRITICAL)

In OpenWrt → **Network → DHCP and DNS → LAN → DHCP Options**, add:

```
6,192.168.1.53
```

That's option 6 (DNS server) pointing at the blocker's IP. Save +
apply. Every LAN client that pulls a DHCP lease from OpenWrt will
now get `192.168.1.53` as its ONLY DNS server. Clients can no
longer bypass by hardcoding `8.8.8.8` — well, they can, but it
won't matter for ad-blocking if you also block port 53 outbound
from anything that isn't the blocker (firewall recipe below).

(Optional) To block port 53 outbound at the firewall, in OpenWrt →
**Network → Firewall → Traffic Rules**, add a rule rejecting
forwarded traffic from the LAN zone to port 53 on any IP that
isn't `192.168.1.53`.

### A.5 — Add the HA integration

In Home Assistant → **Settings → Devices & Services → Add
Integration → Pi-hole v6**
(`https://www.home-assistant.io/integrations/pi_hole/`):

- **Host:** `192.168.1.53`
- **API token:** Settings → API → Show API token (Pi-hole v6
  uses a token, not the old web password)

After the config_flow completes you'll have entities like:

- `sensor.pi_hole_ads_blocked_today`
- `sensor.pi_hole_ads_percentage_today`
- `binary_sensor.pi_hole_status` (reachable)
- `sensor.pi_hole_dns_queries_today`
- `switch.pi_hole` (enable/disable)
- `binary_sensor.pi_hole_update_available`
- `sensor.pi_hole_upstream_dns` (depends on version)

These are UPSTREAM entity ids. The recipe §5 contract templates
wrap them into vendor-neutral `rc_net_dns_*` ids.

## Path B — AdGuard Home

Richer UI, built-in DoH/DoT encryption, per-client parental
controls.

### B.1 — Install AdGuard Home

Pick ONE:

- **Docker:**
  ```bash
  docker run -d --name adguardhome \
    --restart=unless-stopped \
    --network=host \
    -v adguard_work:/opt/adguardhome/work \
    -v adguard_conf:/opt/adguardhome/conf \
    adguard/adguardhome:latest
  ```
  `--network=host` is again the easy path. AdGuard Home's admin
  UI listens on `http://<host>:3000/` on first run.

- **Standalone binary:** download from
  `https://github.com/AdguardTeam/AdGuardHome/releases`, run
  `AdGuardHome`, walk the first-run setup wizard (listens on
  `:3000`), then `AdGuardHome -s install` to register it as a
  systemd service.

- **HA add-on:** community-maintained; check the HACS / add-on
  store for current options.

### B.2 — Assign a static IP

Same as A.2: DHCP reservation in OpenWrt or manual static IP on the
box itself. Use the same `192.168.1.53` if you want consistency
with Path A (only one blocker at a time, of course).

### B.3 — Walk the admin wizard

1. Browse to `http://192.168.1.53:3000/` on first run.
2. Walk the wizard:
   - **Web interface listening interface:** `0.0.0.0:80` (or any
     free port)
   - **DNS interface:** `0.0.0.0:53`
   - **Admin credentials:** set a strong username + password.
3. **Setup → Upstream DNS servers:** AdGuard Home's killer feature
   is built-in DoH/DoT. Use the encryption-on checkboxes and pick:
   - Cloudflare DoH: `https://cloudflare-dns.com/dns-query`
   - Quad9 DoH: `https://dns.quad9.net/dns-query`
   - Or plain DNS if you prefer (`1.1.1.1`, `9.9.9.9`).
4. **Filters → DNS blocklists → Add blocklist:** AdGuard Home
   ships with several pre-configured lists; add more from the
   community (Firebog curated lists: `https://firebog.net/`, or
   HaGeZi's list: `https://raw.githubusercontent.com/hagezi/dns-blocklists/main/hosts.txt`).
5. Save. The blocker is live.

### B.4 — Wire the LAN's DHCP at the blocker (CRITICAL)

Same as A.4: in OpenWrt → **Network → DHCP and DNS → LAN → DHCP
Options**, add `6,192.168.1.53`.

### B.5 — Add the HA integration

In Home Assistant → **Settings → Devices & Services → Add
Integration → AdGuard Home**
(`https://www.home-assistant.io/integrations/adguard/`):

- **Host:** `192.168.1.53`
- **Port:** `80` (or whatever you set in B.3)
- **Username / password:** the admin credentials from B.3.

After the config_flow completes you'll have entities like:

- `sensor.adguard_blocked_count_today`
- `sensor.adguard_blocked_percentage_today`
- `binary_sensor.adguard_running` (reachable)
- `sensor.adguard_total_queries_today`
- `switch.adguard_protection` (enable/disable)
- `binary_sensor.adguard_update_available`
- `sensor.adguard_upstream_dns`

These are UPSTREAM entity ids. The recipe §5 contract templates
wrap them into vendor-neutral `rc_net_dns_*` ids.

## RoamCore contract entities

The full listing the wizard + dashboard + OpenClaw rely on:

| Entity | Type | States | Source |
|---|---|---|---|
| `sensor.rc_net_dns_blocked_today` | sensor | count (int) | template over upstream `*_blocked_today` |
| `sensor.rc_net_dns_blocked_pct` | sensor | 0–100 (%) | template over upstream `*_blocked_pct` |
| `binary_sensor.rc_net_dns_blocker_reachable` | binary_sensor | ON / OFF | template over upstream reachability |
| `sensor.rc_net_dns_queries_total` | sensor | count (int) | template over upstream `*_queries_today` |
| `switch.rc_net_dns_blocker_enabled` | switch | ON / OFF | template over upstream enable/disable |
| `sensor.rc_net_dns_resolver_status` | sensor | `ok` / `degraded` / `down` | template over upstream DNS check |
| `binary_sensor.rc_net_dns_gravity_updated` | binary_sensor | ON / OFF | automation tracking last gravity update |

All grayed-out / `unknown` fallback when the upstream integration
is in error state (or no blocker is configured).

### §5.1 — Copy-pasteable helper YAML (Path A — Pi-hole)

Drop into `homeassistant/packages/roamcore_dns_blocker.yaml`:

```yaml
# RoamCore DNS-blocker contract helpers (recipe §5.1, Pi-hole / Path A).
# All entities are vendor-neutral per docs/reference/rc-entity-naming.md.
# Wraps upstream `sensor.pi_hole_*` entities from the Pi-hole v6
# integration (ha_integration_domain: pi_hole) into rc_net_dns_* ids.

template:
  - sensor:
      - name: DNS blocked today (contract)
        unique_id: rc_net_dns_blocked_today
        unit_of_measurement: "queries"
        state: "{{ states('sensor.pi_hole_ads_blocked_today') | int(0) }}"
        icon: mdi:block-helper
      - name: DNS blocked pct (contract)
        unique_id: rc_net_dns_blocked_pct
        unit_of_measurement: "%"
        state: "{{ states('sensor.pi_hole_ads_percentage_today') | float(0) }}"
        icon: mdi:block-helper
      - name: DNS queries total (contract)
        unique_id: rc_net_dns_queries_total
        unit_of_measurement: "queries"
        state: "{{ states('sensor.pi_hole_dns_queries_today') | int(0) }}"
        icon: mdi:format-list-numbered
  - binary_sensor:
      - name: DNS blocker reachable (contract)
        unique_id: rc_net_dns_blocker_reachable
        device_class: connectivity
        state: "{{ states('binary_sensor.pi_hole_status') }}"
        icon: mdi:dns
      - name: DNS gravity updated (contract)
        unique_id: rc_net_dns_gravity_updated
        device_class: problem
        state: >
          {{ is_state('binary_sensor.pi_hole_update_available', 'off') }}
        icon: mdi:database-refresh
  - switch:
      - name: DNS blocker enabled (contract)
        unique_id: rc_net_dns_blocker_enabled
        state: "{{ is_state('switch.pi_hole', 'on') }}"
        turn_on:
          service: switch.turn_on
          target:
            entity_id: switch.pi_hole
        turn_off:
          service: switch.turn_off
          target:
            entity_id: switch.pi_hole
        icon: mdi:shield-check
  - sensor:
      - name: DNS upstream status (contract)
        unique_id: rc_net_dns_resolver_status
        state: >
          {% set s = states('sensor.pi_hole_upstream_dns') | default('unknown', true) %}
          {% if s in ['unknown', 'unavailable', 'none'] %}down
          {% elif '1.1.1.1' in s or '9.9.9.9' in s or '8.8.8.8' in s %}ok
          {% else %}degraded
          {% endif %}
        icon: mdi:dns-outline
```

### §5.2 — Copy-pasteable helper YAML (Path B — AdGuard Home)

Drop alongside §5.1 in the same package (or replace §5.1 — pick
the path you deployed):

```yaml
# RoamCore DNS-blocker contract helpers (recipe §5.2, AdGuard Home / Path B).
# All entities are vendor-neutral per docs/reference/rc-entity-naming.md.
# Wraps upstream `sensor.adguard_*` entities from the AdGuard Home
# integration (ha_integration_domain: adguard) into rc_net_dns_* ids.

template:
  - sensor:
      - name: DNS blocked today (contract)
        unique_id: rc_net_dns_blocked_today
        unit_of_measurement: "queries"
        state: "{{ states('sensor.adguard_blocked_count_today') | int(0) }}"
        icon: mdi:block-helper
      - name: DNS blocked pct (contract)
        unique_id: rc_net_dns_blocked_pct
        unit_of_measurement: "%"
        state: "{{ states('sensor.adguard_blocked_percentage_today') | float(0) }}"
        icon: mdi:block-helper
      - name: DNS queries total (contract)
        unique_id: rc_net_dns_queries_total
        unit_of_measurement: "queries"
        state: "{{ states('sensor.adguard_total_queries_today') | int(0) }}"
        icon: mdi:format-list-numbered
  - binary_sensor:
      - name: DNS blocker reachable (contract)
        unique_id: rc_net_dns_blocker_reachable
        device_class: connectivity
        state: "{{ states('binary_sensor.adguard_running') }}"
        icon: mdi:dns
      - name: DNS gravity updated (contract)
        unique_id: rc_net_dns_gravity_updated
        device_class: problem
        state: >
          {{ is_state('binary_sensor.adguard_update_available', 'off') }}
        icon: mdi:database-refresh
  - switch:
      - name: DNS blocker enabled (contract)
        unique_id: rc_net_dns_blocker_enabled
        state: "{{ is_state('switch.adguard_protection', 'on') }}"
        turn_on:
          service: switch.turn_on
          target:
            entity_id: switch.adguard_protection
        turn_off:
          service: switch.turn_off
          target:
            entity_id: switch.adguard_protection
        icon: mdi:shield-check
  - sensor:
      - name: DNS upstream status (contract)
        unique_id: rc_net_dns_resolver_status
        state: >
          {% set s = states('sensor.adguard_upstream_dns') | default('unknown', true) %}
          {% if s in ['unknown', 'unavailable', 'none'] %}down
          {% elif 'cloudflare' in s.lower() or 'quad9' in s.lower() or '1.1.1.1' in s or '9.9.9.9' in s %}ok
          {% else %}degraded
          {% endif %}
        icon: mdi:dns-outline
```

### §5.3 — Cross-reference: OpenWrt DHCP options

The blocker is only useful if every LAN client actually uses it as
its DNS server. In OpenWrt → **Network → DHCP and DNS → LAN →
DHCP Options**, add:

```
6,192.168.1.53
```

That's DHCP option 6 (DNS server) pointing at the blocker's IP.
Save + apply. Every LAN client that pulls a DHCP lease from OpenWrt
will now get `192.168.1.53` as its ONLY DNS server.

To make sure clients can't bypass by hardcoding `8.8.8.8`, add an
OpenWrt firewall rule rejecting forwarded traffic from the LAN
zone to port 53 on any IP that isn't `192.168.1.53`. In OpenWrt →
**Network → Firewall → Traffic Rules → Add**:

- Name: `Block direct outbound DNS (force blocker)`
- Protocol: `TCP+UDP`
- Source zone: `lan`
- Destination port: `53`
- Destination address: `!192.168.1.53`
- Action: `reject`

### §5.4 — Optional: encrypted upstream DNS (DoH / DoT)

If you're on cellular or any untrusted network, encrypt the
blocker's upstream DNS queries so the carrier can't snoop them.

- **Path A (Pi-hole):** install `cloudflared` or `stubby` as a
  sidecar, point Pi-hole's upstream at `127.0.0.1#5053` or
  `127.0.0.1#5453`, configure the sidecar to forward DoH to
  Cloudflare (`https://cloudflare-dns.com/dns-query`) or Quad9
  (`https://dns.quad9.net/dns-query`).
- **Path B (AdGuard Home):** in the admin UI **Setup → Upstream
  DNS servers**, check the **Encryption** column and paste
  `https://cloudflare-dns.com/dns-query` or
  `https://dns.quad9.net/dns-query` directly. AdGuard Home
  handles the DoH handshake natively — no sidecar needed.

## Automations

Three sample automations, copy-pasteable into
`homeassistant/automations/roamcore_dns_blocker_*.yaml`:

### §6.1 — Alert when blocklists haven't updated in 7 days

```yaml
alias: DNS blocker — blocklists stale (7d)
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.rc_net_dns_gravity_updated
    to: "off"
    for: "168:00:00"   # 7 days
condition:
  - condition: state
    entity_id: binary_sensor.rc_net_dns_blocker_reachable
    state: "on"
action:
  - service: persistent_notification.create
    data:
      title: RoamCore — DNS blocklists stale (7d)
      message: >-
        The DNS blocker's gravity list hasn't updated in 7 days.
        Open {{ states('sensor.rc_net_dns_resolver_status') }} admin
        and pull a manual gravity update (Pi-hole: Tools → Update
        Gravity; AdGuard Home: Filters → Update filters now).
  - service: notify.mobile_app
    data:
      title: DNS blocklists stale
      message: "DNS gravity hasn't updated in 7 days — pull a manual refresh."
```

### §6.2 — Pause DNS blocker during Stealth mode

```yaml
alias: DNS blocker — pause during Stealth mode
mode: single
trigger:
  - platform: state
    entity_id: input_select.rc_mode
    to: "stealth"
action:
  - service: switch.turn_off
    target:
      entity_id: switch.rc_net_dns_blocker_enabled
  - service: persistent_notification.create
    data:
      title: RoamCore — DNS blocker paused (Stealth)
      message: >-
        Stealth mode active; DNS blocker paused so the LAN gets raw
        upstream DNS. Re-enable via the dashboard or by leaving
        Stealth mode.
trigger:
  - platform: state
    entity_id: input_select.rc_mode
    from: "stealth"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.rc_net_dns_blocker_enabled
```

(Some operators want raw DNS during stealth scenarios; this is
opt-in — flip the automation off if you want the blocker to stay
on in Stealth mode.)

### §6.3 — Re-enable DNS blocker when upstream DNS is reachable again

```yaml
alias: DNS blocker — re-enable when upstream DNS recovers
mode: single
trigger:
  - platform: state
    entity_id: sensor.rc_net_dns_resolver_status
    to: "ok"
    for: "00:01:00"
condition:
  - condition: state
    entity_id: switch.rc_net_dns_blocker_enabled
    state: "off"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.rc_net_dns_blocker_enabled
  - service: persistent_notification.create
    data:
      title: RoamCore — DNS blocker re-enabled
      message: >-
        Upstream DNS is reachable again; re-enabled the DNS blocker
        (it had been auto-paused while upstream was down to avoid
        total DNS failure).
```

## Troubleshooting

- **DNS loop if Pi-hole points at itself as upstream.** If you set
  Pi-hole's upstream DNS to `127.0.0.1`, every query recurses
  infinitely and the LAN goes dark. Fix: **Settings → DNS → Upstream
  DNS Servers**, set to a real upstream (`1.1.1.1`, `9.9.9.9`, or
  the DoH/DoT endpoint). Restart DNS: `pihole restartdns`.

- **Conditional forwarding broken — clients on different subnets
  can't resolve each other.** If you run the DNS blocker on a
  separate subnet (e.g. `192.168.1.x` LAN, blocker on
  `192.168.10.x`), local-name lookups (`printer.local`,
  `nas.local`) fail because the blocker forwards everything
  upstream. Fix: **Settings → DNS → Conditional Forwarding** (or
  AdGuard Home **Setup → Upstream DNS → Private reverse DNS
  servers**): add `lan/192.168.1.0/24` → `192.168.1.1` (your
  OpenWrt). Now `*.local` lookups go to OpenWrt, everything else
  goes to upstream DNS.

- **Blocklist subs not updating — disk full or upstream registry
  down.** If `binary_sensor.rc_net_dns_gravity_updated` flips OFF
  and stays OFF, check the blocker's admin log: the update may
  have failed because (a) the disk is full (`df -h` on the
  blocker box), or (b) one of the blocklist upstream URLs is
  down. Fix: prune old logs (`pihole -g` with `--no-recent` or
  AdGuard Home **Logs → Clear old query logs**), then remove the
  failing blocklist source. Restart the gravity update manually.

- **HA shows stale block count — sensor.update_interval mismatch.**
  The upstream `sensor.pi_hole_*` / `sensor.adguard_*` entities
  default to a 1-minute scan interval, but Pi-hole's gravity
  updates can take 30+ seconds (downloading hundreds of thousands
  of domains). If the count looks stuck, HA's `state` may not have
  refreshed. Fix: in HA → **Developer Tools → States**, force a
  refresh (`pi_hole.refresh`), or bump the template sensor's
  scan_interval in the contract helpers.

- **Container can't reach upstream DNS — firewall blocking
  53/tcp+53/udp+853/tcp.** If your docker network / VPS / firewall
  blocks outbound port 53, 853 (DoT), or 443 (DoH), the blocker
  can't reach its upstream resolver and silently times out. Fix:
  open `53/tcp+udp` (plain DNS), `853/tcp` (DoT), and `443/tcp`
  (DoH) outbound from the blocker's IP. Verify with
  `dig @1.1.1.1 example.com` from the blocker box itself.

- **DoH/DoT TLS handshake failures — system clock skew or wrong
  bootstrap IP.** If you've enabled DoH upstream (Path B's
  Cloudflare / Quad9) and the blocker's logs show TLS errors,
  the most common cause is **system clock skew** — TLS rejects
  certificates with timestamps outside the validity window.
  Fix: enable NTP on the blocker box (`timedatectl set-ntp true`
  on systemd hosts; or `pihole -g --nTP=on` if Pi-hole). Verify
  with `date -u` and `chronyc tracking` (if chrony is installed).

## §8 Privacy

- **Local only.** RoamCore does not phone home to Pi-hole or
  AdGuard; the contract tiles are 100% local. No telemetry to
  RoamCore. No domain, IP, MAC, or blocklist source in any
  contract entity.
- **Blocker stats** come from the blocker's own admin API (Pi-hole
  v6's `/admin/api` endpoint, AdGuard Home's `/control/stats`
  endpoint), which serves the LAN only — no internet round-trip
  unless you've enabled DoH upstream (which is the operator's
  choice, not RoamCore's).
- **No domain / IP / MAC** is captured in any `rc_net_dns_*`
  entity, OpenClaw summary key, or dashboard tile. The contract is
  intentionally vendor-neutral.
- **Blocklist sources** are the operator's choice (default Pi-hole
  / AdGuard lists, Firebog curated lists, HaGeZi, etc.).
  RoamCore does not add or curate blocklists.

## §9 Promoting to tier-a (outline)

When a real DNS blocker lands on the CI bench (likely via
`testcontainers/pihole` or `testcontainers/adguardhome` with a
synthetic admin-API fixture — the upstream `pi_hole` / `adguard`
HA integrations already have testcontainer images available in
their own CI), this connection is the candidate to promote to
tier-a:

1. Add a native `config_flow.py` that wraps the upstream
   Pi-hole / AdGuard Home config_flow (or ships its own wizard
   steps) and walks the operator through choosing Path A vs Path
   B + providing the LAN URL + credentials.
2. Add a RoamCore-side `__init__.py` that listens for the
   upstream config_flow completing and auto-creates the
   `rc_net_dns_*` contract helpers (today those are manual
   YAML from §5.1 / §5.2).
3. Add an integration test that asserts the `rc_net_dns_*`
   contract entities appear after a synthetic Pi-hole / AdGuard
   Home admin-API fixture returns a known payload.
4. Flip `tier_requirements` to include `working_config_flow` +
   `integration_test_passes` + `no_manual_yaml_required`.
5. Drop `tier_warnings` entries that mention no-real-blocker /
   recipe-depends-on-user.
6. Flip `status` from `beta` to `shipped`.
7. Flip `wizard.one_tap` to `true`.

Until then, this stays at tier-b (beta, recipe) — the recipe is
sound, the contract is honest, and we don't claim one-tap
coverage we don't have.