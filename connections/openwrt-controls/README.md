# OpenWrt controls — tier-a recipe connection

Vendor-neutral OpenWrt API integration path to surface WAN/internet state into HA + enable safe control flows. The umbrella wraps the existing RoamCore-owned packages (`homeassistant/packages/roamcore_openwrt_api.yaml` (235 LOC) + `homeassistant/packages/roamcore_net.yaml` (238 LOC)) and adds the recipe layer (the 27 `rc_openwrt_*` + `rc_net_openwrt_*` contract tiles + the 4 `script.rc_openwrt_*` control scripts + the FOUR §8 MANDATORY automations + the 5 safety tiles + the legacy SUPERSEDED banner + the docs cross-references).

This folder is the **tier-a recipe connection** for OpenWrt controls — it ADDS the manifest + the recipe.md howto + the smoke WITHOUT modifying the existing package contents (the two packages are referenced verbatim via `install.packages:`).

## Status

- Tier: a (recipe)
- Category: networking
- Status: beta (no pytest bench fixtures for the OpenWrt REST API surface — see §12 of the recipe)
- Version: 0.1.0
- PR: #83

## Folder layout

```
connections/openwrt-controls/
├── README.md                  ← this file
├── __init__.py                ← DOMAIN marker stub
├── connection.yml             ← tier-a manifest
├── docs/
│   └── recipe.md              ← the FIVE-step operator flow + the 27 contract tiles + the 4 control scripts + the 5 safety tiles + the FOUR §8 MANDATORY automations + the 5 §9 troubleshooting entries + the §10 privacy section + the §11 tier-a promotion outline + the §12 bench-fixture gap + the §13 links
└── tests/
    └── test_connection_yml.py ← 7 manifest-honesty tests (mirrors the dns-blocker / map-dashboard / demo-mode / openclaw-api pattern)
```

## Tier-a recipe shape

This connection is a **tier-a recipe** over two RoamCore-owned HA packages:

- **`homeassistant/packages/roamcore_openwrt_api.yaml`** (235 LOC) — the 30+ `rc_openwrt_*` REST sensors (resource templates pointing at the OpenWrt router's LuCI ubus-rpc JSON endpoints) + the `rest_command.rc_openwrt_*` invocations + the 4 `script.*` WAN preference drivers (`rc_openwrt_prefer_starlink` + `rc_openwrt_prefer_lte` + `rc_openwrt_prefer_auto` + `rc_openwrt_restart_network`) + the `input_text.rc_openwrt_api_url` + `input_text.rc_openwrt_api_token` helpers that hold the operator-supplied API URL + the LuCI ubus-rpc token from the OpenWrt VM at 192.168.1.250 (per TOOLS.md).
- **`homeassistant/packages/roamcore_net.yaml`** (238 LOC) — the 25+ `rc_net_*` unique_ids (sensors + binary_sensor) including the 12 `rc_net_openwrt_*` tiles that surface OpenWrt-derived networking state: WAN status + Wi-Fi SSID + Wi-Fi client count + firewall backend + fw4 OK + iptables NAT MVP detected + iptables NAT table OK + RoamCore firewall running + Starlink / LTE bytes today / month.

Both packages are ALREADY SHIPPED on main and are loaded via the standard HA `packages:` mechanism. The tier-a claim IS honest: RoamCore DOES own + ship + maintain those packages. The tier-a-but-flagged honesty: there are no pytest integration tests against a controlled bench (the OpenWrt REST API is the actual surface; the bench-fixture gap is documented in §12 of the recipe).

## The 27 contract tiles

The 27 contract tiles are vendor-neutral (no `luci`, `ubus`, `rpcd`, `uci`, `openwrt`, `uhttpd`, `netifd`, `fw4`, `nftables`, `iptables`, `wpad`, `hostapd`, `wpa_supplicant`, `dnsmasq`, `odhcpd`, `qmi`, `mbim`, `modemmanager`, `sstp`, `wireguard`, `pptpd` names leak into the rc_* ids):

### 15 `rc_openwrt_*` (OpenWrt subsystem — NEW)

| Entity ID | Purpose | Source package |
|-----------|---------|----------------|
| `binary_sensor.rc_openwrt_internet` | internet reachable via OpenWrt default route | `roamcore_openwrt_api.yaml` |
| `binary_sensor.rc_openwrt_active_wan` | true if any WAN interface is up | `roamcore_openwrt_api.yaml` |
| `sensor.rc_openwrt_uptime_s` | router uptime in seconds | `roamcore_openwrt_api.yaml` |
| `select.rc_openwrt_preferred_wan` | Starlink / LTE / Auto (operator pickable; drives `script.rc_openwrt_prefer_*`) | `roamcore_openwrt_api.yaml` |
| `sensor.rc_openwrt_starlink_state` | derived Starlink WAN state (up / down / degraded) | `roamcore_openwrt_api.yaml` |
| `sensor.rc_openwrt_lte_state` | derived LTE WAN state (up / down / sim-missing) | `roamcore_openwrt_api.yaml` |
| `binary_sensor.rc_openwrt_lte_sim_ready_state` | true when LTE SIM is registered | `roamcore_openwrt_api.yaml` |
| `binary_sensor.rc_openwrt_lte_registration_state` | true when LTE modem is registered on the network | `roamcore_openwrt_api.yaml` |
| `sensor.rc_openwrt_lte_provider_name` | operator-readable LTE provider name | `roamcore_openwrt_api.yaml` |
| `sensor.rc_openwrt_lte_signal_rssi` | LTE RSSI (dBm) | `roamcore_openwrt_api.yaml` |
| `sensor.rc_openwrt_router_cpu_pct` | router CPU % | `roamcore_openwrt_api.yaml` |
| `sensor.rc_openwrt_router_memory_pct` | router RAM % | `roamcore_openwrt_api.yaml` |
| `sensor.rc_openwrt_router_temp_c` | router temperature (°C) | `roamcore_openwrt_api.yaml` |
| `sensor.rc_openwrt_router_load_1m` | router 1-minute load average | `roamcore_openwrt_api.yaml` |
| `sensor.rc_openwrt_router_uptime_s` | router uptime in seconds (mirrors `rc_openwrt_uptime_s`) | `roamcore_openwrt_api.yaml` |

### 12 `rc_net_openwrt_*` (existing `net` subsystem, OpenWrt-derived)

| Entity ID | Purpose | Source package |
|-----------|---------|----------------|
| `sensor.rc_net_openwrt_wan_status` | current WAN interface status (up / down / connecting) | `roamcore_net.yaml` |
| `sensor.rc_net_openwrt_wifi_ssid` | current 2.4/5GHz Wi-Fi SSID | `roamcore_net.yaml` |
| `sensor.rc_net_openwrt_wifi_clients` | Wi-Fi client count | `roamcore_net.yaml` |
| `sensor.rc_net_openwrt_firewall_backend` | fw4 / iptables / nftables (operator-readable) | `roamcore_net.yaml` |
| `binary_sensor.rc_net_openwrt_fw4_ok` | true if fw4 firewall is healthy | `roamcore_net.yaml` |
| `binary_sensor.rc_net_openwrt_iptables_mvp_detected` | true if iptables NAT MVP is detected | `roamcore_net.yaml` |
| `binary_sensor.rc_net_openwrt_iptables_nat_table_ok` | true if iptables NAT table is healthy | `roamcore_net.yaml` |
| `binary_sensor.rc_net_openwrt_roamcore_fw_running` | true if the RoamCore firewall ruleset is loaded | `roamcore_net.yaml` |
| `sensor.rc_net_openwrt_starlink_today_rx_mb` | Starlink bytes received today (MB) | `roamcore_net.yaml` |
| `sensor.rc_net_openwrt_starlink_month_rx_mb` | Starlink bytes received this month (MB) | `roamcore_net.yaml` |
| `sensor.rc_net_openwrt_lte_today_rx_mb` | LTE bytes received today (MB) | `roamcore_net.yaml` |
| `sensor.rc_net_openwrt_lte_month_rx_mb` | LTE bytes received this month (MB) | `roamcore_net.yaml` |

## The 4 control scripts

The 4 `script.rc_openwrt_*` control scripts are NOT contract tiles — they are `script.*` references from the RoamCore-owned helper entities in `homeassistant/packages/roamcore_openwrt_api.yaml`. The operator's preferred-WAN selector drives the correct script invocation via §8.1, and the §8.4 restart-network confirm guard BLOCKS the `script.rc_openwrt_restart_network` script invocation unless `input_boolean.rc_openwrt_confirm_restart` is ON.

| Script | Purpose | Confirm-flag? |
|--------|---------|---------------|
| `script.rc_openwrt_prefer_starlink` | set preferred WAN to Starlink | no |
| `script.rc_openwrt_prefer_lte` | set preferred WAN to LTE | no |
| `script.rc_openwrt_prefer_auto` | set preferred WAN to Auto (OpenWrt default route policy) | no |
| `script.rc_openwrt_restart_network` | restart OpenWrt network (CRITICAL — requires confirm-flag per §8.4) | YES (§8.4) |

## The 5 safety tiles

The 5 safety tiles are wired into the FOUR §8 MANDATORY automations:

| Entity ID | Purpose | Drives §8 automation |
|-----------|---------|----------------------|
| `select.rc_openwrt_preferred_wan` | operator pickable | §8.1 |
| `button.rc_openwrt_restart_network` | CRITICAL — requires confirm-flag | §8.4 |
| `input_boolean.rc_openwrt_confirm_restart` | confirm-flag for §8.4 | §8.4 |
| `binary_sensor.rc_openwrt_lte_sim_ready_state` | triggers §8.2 | §8.2 |
| `binary_sensor.rc_net_openwrt_roamcore_fw_running` | triggers §8.3 | §8.3 |

## The FOUR §8 MANDATORY automations

1. **§8.1 prefer-WAN selector drives the correct script** — triggers when `select.rc_openwrt_preferred_wan` changes value; calls `script.rc_openwrt_prefer_starlink` for Starlink / `script.rc_openwrt_prefer_lte` for LTE / `script.rc_openwrt_prefer_auto` for Auto; writes an audit-log entry with the previous value + the new value + the timestamp.
2. **§8.2 LTE-SIM-missing alert** — triggers when `binary_sensor.rc_openwrt_lte_sim_ready_state` flips to OFF while `binary_sensor.rc_openwrt_active_wan` is true AND `select.rc_openwrt_preferred_wan` is LTE; fires a critical notification warning the operator.
3. **§8.3 firewall-state alert** — triggers when `binary_sensor.rc_net_openwrt_fw4_ok` flips to OFF OR `binary_sensor.rc_net_openwrt_roamcore_fw_running` flips to OFF; fires a critical notification.
4. **§8.4 restart-network confirm guard** — triggers when the operator presses `button.rc_openwrt_restart_network` (or invokes `script.rc_openwrt_restart_network` directly); checks `input_boolean.rc_openwrt_confirm_restart` — if FALSE, BLOCKS the script invocation; if TRUE, clears the confirm-flag AFTER successful script invocation.

## Bench-fixture gap acknowledgment

There are no pytest integration tests for the OpenWrt packages on the CI bench (the OpenWrt REST API is the actual surface; the OpenWrt VM is on the operator's home LAN at 192.168.1.250 per TOOLS.md, NOT on CI). The slice documents the canned fixture responses needed for tier-a promotion in §11 of the recipe (offline / online / degraded / LTE-missing events + integration tests asserting the preferred-WAN selector calls the correct `script.rc_openwrt_prefer_*` + restart-network BLOCKS without confirm-flag).

## OpenWrt 192.168.1.250 development mgmt IP pointer

The OpenWrt VM (on the Proxmox host, VMID 100) is reachable from the Clawdbot host at `192.168.1.250` (per TOOLS.md — the temporary dev mgmt IP set inside the VM). The operator's LuCI ubus-rpc token goes into `input_text.rc_openwrt_api_token` (the operator retrieves the token from the OpenWrt LuCI UI at `http://192.168.1.250/cgi-bin/luci/admin/services/rpcd` → "Generate Token").

## See also

- `docs/catalog/networking/openwrt-controls.md` — legacy 21-line tier-a claim stub (now superseded with the SUPERSEDED banner appended at the end)
- `docs/recipe.md` — the FIVE-step operator flow + the 27 contract tiles + the 4 control scripts + the 5 safety tiles + the FOUR §8 MANDATORY automations + the 5 §9 troubleshooting entries + the §10 privacy section + the §11 tier-a promotion outline + the §12 bench-fixture gap + the §13 links
- `tests/test_connection_yml.py` — 7 manifest-honesty tests (mirrors the dns-blocker / map-dashboard / demo-mode / openclaw-api pattern)
- `scripts/check.sh` — registers the openwrt-controls smoke check (run via `bash scripts/check.sh --core-only`)