#!/bin/sh
set -eu

. "$(dirname "$0")/lib.sh"
rc_load_vars

rc_log "Applying UCI config (parameterised)"

# If DRY_RUN=1, print what would be executed and exit.
DRY_RUN="${DRY_RUN:-0}"
if [ "$DRY_RUN" = "1" ]; then
  rc_log "DRY_RUN=1: will not apply any changes"
  rc_log "Loaded variables:"
  env | grep '^RC_' | sort || true
  exit 0
fi

rc_log "LAN: ${RC_LAN_IP}/${RC_LAN_NETMASK} dev=${RC_DEV_LAN}"

# --- network ---
uci -q batch <<EOF
set network.lan=interface
set network.lan.proto='static'
set network.lan.device='${RC_DEV_LAN}'
set network.lan.ipaddr='${RC_LAN_IP}'
set network.lan.netmask='${RC_LAN_NETMASK}'

set network.wan_starlink=interface
set network.wan_starlink.proto='dhcp'
set network.wan_starlink.device='${RC_DEV_WAN_STARLINK}'
set network.wan_starlink.metric='10'
set network.wan_starlink.peerdns='0'
add_list network.wan_starlink.dns='1.1.1.1'
add_list network.wan_starlink.dns='8.8.8.8'

set network.wan_lte=interface
set network.wan_lte.proto='qmi'
set network.wan_lte.device='${RC_DEV_LTE_QMI}'
set network.wan_lte.apn='auto'
set network.wan_lte.auth='none'
set network.wan_lte.pdptype='ipv4v6'
set network.wan_lte.metric='20'
set network.wan_lte.peerdns='0'
add_list network.wan_lte.dns='1.1.1.1'
add_list network.wan_lte.dns='8.8.8.8'

commit network
EOF

# --- dhcp/dns ---
uci -q batch <<EOF
set dhcp.@dnsmasq[0]=dnsmasq
set dhcp.@dnsmasq[0].domain='${RC_DOMAIN}'
set dhcp.@dnsmasq[0].local='/${RC_DOMAIN}/'
set dhcp.@dnsmasq[0].expandhosts='1'
set dhcp.@dnsmasq[0].authoritative='1'

set dhcp.lan=dhcp
set dhcp.lan.interface='lan'
set dhcp.lan.start='${RC_LAN_DHCP_START}'
set dhcp.lan.limit='${RC_LAN_DHCP_LIMIT}'
set dhcp.lan.leasetime='${RC_LAN_DHCP_LEASETIME}'
add_list dhcp.lan.dhcp_option='6,${RC_LAN_IP}'

set dhcp.wan_starlink=dhcp
set dhcp.wan_starlink.interface='wan_starlink'
set dhcp.wan_starlink.ignore='1'

set dhcp.wan_lte=dhcp
set dhcp.wan_lte.interface='wan_lte'
set dhcp.wan_lte.ignore='1'

commit dhcp
EOF

# Local DNS records
if uci -q get dhcp.roamcore_domain >/dev/null 2>&1; then
  :
else
  uci add dhcp domain >/dev/null
  uci rename dhcp.@domain[-1]='roamcore_domain'
fi
uci set dhcp.roamcore_domain.name="${RC_DNS_ROAMCORE_NAME}"
uci set dhcp.roamcore_domain.ip="${RC_DNS_ROAMCORE_IP}"

if uci -q get dhcp.ha_domain >/dev/null 2>&1; then
  :
else
  uci add dhcp domain >/dev/null
  uci rename dhcp.@domain[-1]='ha_domain'
fi
uci set dhcp.ha_domain.name="${RC_DNS_HA_NAME}"
uci set dhcp.ha_domain.ip="${RC_DNS_HA_IP}"

# Optional static lease for HA
if [ -n "${RC_HA_STATIC_MAC}" ]; then
  if ! uci show dhcp | grep -q "=host"; then
    :
  fi
  # Create/update a named host section
  if uci -q get dhcp.homeassistant >/dev/null 2>&1; then
    :
  else
    uci add dhcp host >/dev/null
    uci rename dhcp.@host[-1]='homeassistant'
  fi
  uci set dhcp.homeassistant.name='homeassistant'
  uci set dhcp.homeassistant.mac="${RC_HA_STATIC_MAC}"
  uci set dhcp.homeassistant.ip="${RC_HA_STATIC_IP}"
  uci set dhcp.homeassistant.leasetime='infinite'
fi

uci commit dhcp

# --- firewall ---
uci -q batch <<EOF
set firewall.@defaults[0]=defaults
set firewall.@defaults[0].syn_flood='1'
set firewall.@defaults[0].input='ACCEPT'
set firewall.@defaults[0].output='ACCEPT'
set firewall.@defaults[0].forward='REJECT'

# Zones
set firewall.lan=zone
set firewall.lan.name='lan'
add_list firewall.lan.network='lan'
set firewall.lan.input='ACCEPT'
set firewall.lan.output='ACCEPT'
set firewall.lan.forward='ACCEPT'

set firewall.wan=zone
set firewall.wan.name='wan'
add_list firewall.wan.network='wan_starlink'
add_list firewall.wan.network='wan_lte'
set firewall.wan.input='REJECT'
set firewall.wan.output='ACCEPT'
set firewall.wan.forward='REJECT'
set firewall.wan.masq='1'
set firewall.wan.mtu_fix='1'

set firewall.lan_wan=forwarding
set firewall.lan_wan.src='lan'
set firewall.lan_wan.dest='wan'

# Allow DNS/DHCP/LuCI/API from LAN
set firewall.allow_dns=rule
set firewall.allow_dns.name='Allow-DNS'
set firewall.allow_dns.src='lan'
set firewall.allow_dns.dest_port='53'
set firewall.allow_dns.proto='tcpudp'
set firewall.allow_dns.target='ACCEPT'

set firewall.allow_dhcp=rule
set firewall.allow_dhcp.name='Allow-DHCP'
set firewall.allow_dhcp.src='lan'
set firewall.allow_dhcp.dest_port='67-68'
set firewall.allow_dhcp.proto='udp'
set firewall.allow_dhcp.target='ACCEPT'

set firewall.allow_luci=rule
set firewall.allow_luci.name='Allow-LuCI'
set firewall.allow_luci.src='lan'
set firewall.allow_luci.dest_port='80 443'
set firewall.allow_luci.proto='tcp'
set firewall.allow_luci.target='ACCEPT'

set firewall.allow_api=rule
set firewall.allow_api.name='Allow-RoamCore-API'
set firewall.allow_api.src='lan'
set firewall.allow_api.dest_port='8080'
set firewall.allow_api.proto='tcp'
set firewall.allow_api.target='ACCEPT'

commit firewall
EOF

# --- mwan3 ---
uci -q delete mwan3.wan_starlink 2>/dev/null || true
uci -q delete mwan3.wan_lte 2>/dev/null || true
uci -q delete mwan3.starlink_primary 2>/dev/null || true
uci -q delete mwan3.lte_backup 2>/dev/null || true
uci -q delete mwan3.failover_policy 2>/dev/null || true
uci -q delete mwan3.default_rule 2>/dev/null || true

uci -q batch <<EOF
set mwan3.wan_starlink=interface
set mwan3.wan_starlink.enabled='1'
set mwan3.wan_starlink.family='ipv4'
add_list mwan3.wan_starlink.track_ip='1.1.1.1'
add_list mwan3.wan_starlink.track_ip='8.8.8.8'
set mwan3.wan_starlink.track_method='ping'
set mwan3.wan_starlink.reliability='1'
set mwan3.wan_starlink.count='3'
set mwan3.wan_starlink.timeout='4'
set mwan3.wan_starlink.interval='10'
set mwan3.wan_starlink.down='3'
set mwan3.wan_starlink.up='3'

set mwan3.wan_lte=interface
set mwan3.wan_lte.enabled='1'
set mwan3.wan_lte.family='ipv4'
add_list mwan3.wan_lte.track_ip='1.1.1.1'
add_list mwan3.wan_lte.track_ip='9.9.9.9'
set mwan3.wan_lte.track_method='ping'
set mwan3.wan_lte.reliability='1'
set mwan3.wan_lte.count='3'
set mwan3.wan_lte.timeout='4'
set mwan3.wan_lte.interval='10'
set mwan3.wan_lte.down='3'
set mwan3.wan_lte.up='3'

set mwan3.starlink_primary=member
set mwan3.starlink_primary.interface='wan_starlink'
set mwan3.starlink_primary.metric='1'
set mwan3.starlink_primary.weight='1'

set mwan3.lte_backup=member
set mwan3.lte_backup.interface='wan_lte'
set mwan3.lte_backup.metric='2'
set mwan3.lte_backup.weight='1'

set mwan3.failover_policy=policy
add_list mwan3.failover_policy.use_member='starlink_primary'
add_list mwan3.failover_policy.use_member='lte_backup'
set mwan3.failover_policy.last_resort='default'

set mwan3.default_rule=rule
set mwan3.default_rule.dest_ip='0.0.0.0/0'
set mwan3.default_rule.proto='all'
set mwan3.default_rule.use_policy='failover_policy'

commit mwan3
EOF

# --- wireless (best-effort) ---
# Some deployments may not have AX210 in dev; these UCI keys might not exist.
uci -q set wireless.default_radio0=wifi-iface || true
uci -q set wireless.default_radio1=wifi-iface || true
uci -q set wireless.default_radio0.ssid="${RC_WIFI_SSID}" || true
uci -q set wireless.default_radio0.key="${RC_WIFI_KEY}" || true
uci -q set wireless.default_radio0.encryption='sae-mixed' || true
uci -q set wireless.default_radio0.network='lan' || true
uci -q set wireless.default_radio0.mode='ap' || true

uci -q set wireless.default_radio1.ssid="${RC_WIFI_SSID}" || true
uci -q set wireless.default_radio1.key="${RC_WIFI_KEY}" || true
uci -q set wireless.default_radio1.encryption='sae-mixed' || true
uci -q set wireless.default_radio1.network='lan' || true
uci -q set wireless.default_radio1.mode='ap' || true

uci -q set wireless.radio0.country="${RC_WIFI_COUNTRY}" || true
uci -q set wireless.radio1.country="${RC_WIFI_COUNTRY}" || true
uci -q set wireless.radio0.channel="${RC_WIFI_CHANNEL_2G}" || true
uci -q set wireless.radio1.channel="${RC_WIFI_CHANNEL_5G}" || true

uci -q commit wireless || true

rc_log "Restarting services"
/etc/init.d/network restart || true
/etc/init.d/firewall restart || true
/etc/init.d/dnsmasq restart || true
/etc/init.d/mwan3 restart || true
wifi reload || true

rc_log "Done"
