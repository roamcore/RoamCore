"""NAS (Network Attached Storage — Synology / QNAP / generic SMB) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up a NAS (Path A = Synology DSM, Path B =
QNAP, Path C = generic SMB/NFS) on the van's LAN, assigning it a
static IP, exposing its shares, and letting HA's upstream integration
or `homeassistant` network-storage block + backup integration pick it
up.

Upstream integrations have a working entry in HA core (or, for Path C,
via configuration.yaml + the backup integration):

  - Path A — Synology DSM (ha_integration_domain: synology_dsm):
    upstream UI walk since 2020.12. ~30 sensors (storage, S.M.A.R.T.,
    CPU, memory, active users, volume health).
  - Path B — QNAP (ha_integration_domain: qnap): upstream UI walk
    since 2017 / modernized 2022.4. Similar surface to Synology DSM.
  - Path C — Generic SMB/NFS (ha_integration_domain: smb via the
    `homeassistant` network-storage block + the HA backup
    integration): NOT a modern upstream UI walk in the strict sense,
    but the HA backup integration (which the operator uses to point
    backups at the SMB share) DOES have its own upstream UI walk.

RoamCore does NOT ship a RoamCore-owned wrapper around any of those
upstreams; the upstream-truth flag in connection.yml reflects
UPSTREAM truth (the operator adds the integration via HA's own
setup or via configuration.yaml), NOT a RoamCore-owned flow.

The audit + boundary CI can detect a `nas/` folder that claims to be
a connection via the `DOMAIN` constant exported here. The wizard
reads the manifest + recipe at runtime.

The real NAS path is:

    Synology DSM (Path A) or QNAP (Path B) or SMB/NFS box (Path C)
        -> upstream HA setup (synology_dsm / qnap upstream UI walk,
           or `homeassistant` network-storage block + backup
           integration)
        -> upstream sensor entities (sensor.synology_dsm_storage_*,
           sensor.qnap_system_* / sensor.qnap_memory_*,
           binary_sensor.synology_dsm_smart_status, etc.)
        -> RoamCore contract layer (rc_homelab_nas_storage_used_pct,
           rc_homelab_nas_storage_total_gb,
           rc_homelab_nas_storage_free_gb, rc_homelab_nas_reachable,
           rc_homelab_nas_smart_status_ok, rc_homelab_nas_last_backup_at,
           rc_homelab_nas_backup_running, rc_homelab_nas_cpu_pct,
           rc_homelab_nas_memory_pct)
        -> dashboard tiles + OpenClaw queries

See docs/recipe.md for the full howto (Path A Synology install +
upstream UI walk, Path B QNAP install + upstream UI walk, Path C SMB
share + backup target wiring, the `rc_homelab_nas_*` template-helper
wiring, 4 automations, 8 troubleshooting entries, and the tier-a
promotion outline).
"""

DOMAIN = "nas"