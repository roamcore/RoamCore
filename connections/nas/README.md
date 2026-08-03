# NAS (Network Attached Storage — Synology / QNAP / generic SMB)

**Tier:** B (recipe)
**Category:** Homelab
**Status:** beta

## What this connection is

A NAS gives RoamCore a reliable local-storage target for media,
camera footage, backups, and logs — especially valuable when you
don't want to depend on cloud services. In a van that's frequently
off-grid, a NAS (or a mini-PC pretending to be one) is the single
biggest "I don't have to worry about LTE bandwidth or cloud bills"
win you can ship:

- **Local backups (even offline)** — RoamCore's HA backups,
  Frigate's CCTV clip archive, and Trip Wrapped's HTML exports
  all have a place to land without depending on cloud storage.
- **Central media library** — movies / music / reference docs /
  maps / offline OpenStreetMap tiles / vehicle manuals all live
  on a single share that's reachable from any LAN device.
- **CCTV archival** — Frigate's event clips + continuous
  recordings can be offloaded from the RoamCore box's SD/NVMe
  to the NAS's larger-volume pool.
- **Logs + crash dumps** — long-running log files that would
  fill the RoamCore box's local storage can land on the NAS.

The recipe covers **three** NAS paths because the operator's
hardware varies:

- **Path A — Synology DSM** (richest integration surface, ~30
  sensors including storage, S.M.A.R.T., CPU, memory, active
  users, volume health, UPS status). Best when you're already
  running DiskStation Manager and want the deepest contract
  coverage.
- **Path B — QNAP** (alternative NAS vendor, similarly rich
  integration surface). Best when you have QNAP hardware.
- **Path C — Generic SMB/NFS** (any NAS that exposes shares —
  TrueNAS, Unraid, a Raspberry Pi with an external drive, an
  old mini-PC with a big disk, etc.). Best when you already have
  generic SMB/NFS storage and don't need Synology/QNAP-specific
  telemetry.

Synology DSM has a working config_flow in Home Assistant core
since 2020.12; QNAP since 2017 / modernized 2022.4. Generic SMB
uses HA's `homeassistant` network-storage block + the HA backup
integration. RoamCore does **not** ship a NAS of its own — you
bring whichever NAS hardware you want on your LAN, and RoamCore
layers the `rc_homelab_nas_*` contract tiles on top.

## Setup recipe (one-paragraph)

1. Decide Path A (Synology), Path B (QNAP), or Path C (generic
   SMB/NFS). Stand up the NAS on the LAN with a static IP
   (DHCP reservation on OpenWrt is the cleanest path).
2. (Path A/B) Expose the DSM/QNAP management API and create a
   dedicated low-privilege account for HA.
   (Path C) Create an SMB share on the NAS, set up a username +
   password, and verify it's reachable from the RoamCore box via
   `mount -t cifs //<nas-ip>/share /mnt`.
3. In Home Assistant → **Settings → Devices & Services → Add
   Integration**, search for **Synology DSM** (Path A) or **QNAP**
   (Path B) and walk the upstream config_flow — enter the NAS's
   LAN URL + credentials (Path A/B). For Path C, add the SMB
   share via the `homeassistant` network-storage block in
   `configuration.yaml`.
4. (Optional, all paths) Point HA's backup integration at a
   directory on the NAS so backups land on local storage
   instead of the RoamCore box's SD/NVMe.
5. Create the `rc_homelab_nas_*` contract tiles by importing the
   recipe §6 snippet block (template sensors over the upstream
   `sensor.synology_dsm_*` / `sensor.qnap_*` entities, or via the
   HA backup integration's reported state for backup status).
6. Enable the recipe §7 automations (storage-90%-used alert,
   S.M.A.R.T.-health-flip alert, pause Trip Wrapped exports when
   NAS is unreachable, auto-trigger backup before departure via
   Mode-based automation hook).
7. Reload the RoamCore dashboard; the `rc_homelab_nas_*` contract
   tiles appear on the Homelab section.

Full howto with copy-pasteable YAML for the helper templates,
the HA backup target wiring, 4 automations, 8 troubleshooting
entries, and the tier-a promotion outline: see
[`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`,
integration tests against a real NAS on CI, and
`wizard.one_tap: true`. We have no NAS on the CI bench to
integration-test against, and the upstream Synology DSM / QNAP /
SMB integrations are operator-chosen (Path A vs Path B vs Path C).
So this connection is honestly beta-tier: the recipe is sound
(it leans on the upstream HA core integration's existing
config_flow + the operator's own NAS deployment), but we cannot
claim one-tap automation from the RoamCore side.

The `install.config_flow: true` field in the manifest is
**UPSTREAM truth** (Synology DSM has had a working config_flow
in HA core since 2020.12, QNAP since 2017 / modernized 2022.4) —
NOT a RoamCore-owned config_flow. The `__init__.py` is a DOMAIN
stub; there is no `config_flow.py` in this folder. If we ever
ship a native RoamCore-owned wrapper around the upstream
config_flow (e.g. a wizard-side helper that auto-creates the
`rc_homelab_nas_*` contract tiles post-config_flow), we'd add a
`config_flow.py` here, flip the tier to tier-a, and update the
test to assert the new flow is real.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "nas"` marker for the audit.
- `docs/recipe.md` — the full howto (Path A Synology install +
  config_flow, Path B QNAP install + config_flow, Path C SMB
  share + backup target wiring, `rc_homelab_nas_*` template-helper
  wiring, 4 automations, 8 troubleshooting entries, tier-a
  promotion outline).
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by the connection manifest):
  [the legacy spec](../../the legacy spec)
  — note that the legacy page is actually tagged tier-b (not
  tier-c like some other legacy pages) per its frontmatter, and
  has been promoted into this single tier-b connection slice with
  Path A / Path B / Path C.
- Catalog category index: the legacy spec
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
  (`homelab` subsystem mapping for self-hosted appliances — the
  canonicalization pass will codify this in a follow-up).
- Frigate NVR slice (peers with NAS under the `homelab` bucket —
  Frigate's CCTV clips offload to the NAS): `connections/frigate/`
- DNS-blocker slice (peers with NAS under the homelab bucket —
  DNS-blocker + NAS both live in the LAN): `connections/dns-blocker/`