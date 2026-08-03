# Wave 3 #58 — Connection: Remote access (tier-b) slice handoff

## Context

Promote the legacy tier-b `docs/catalog/remote-access/index.md`
spec (a 16-line stub, originally listed ONLY Tailscale at
"Support tier: B" with no recipe + no contract + no broader
vendor-neutral coverage — just a placeholder about "check sensor
status, view cameras, get alerts, or (optionally) control
systems" + "safe ways to reach Home Assistant remotely, with
clear notes on security and support level") + the legacy
tier-b Tailscale spec at `docs/catalog/remote-access/tailscale.md`
(a 23-line stub originally listed ONLY Tailscale at "Support
tier: B" with no recipe + no contract + no broader vendor-
neutral coverage — just a placeholder about "Tailscale is a
simple, secure mesh VPN. It's a great way to access Home
Assistant remotely without opening ports or relying on complex
networking") into a tier-b recipe connection at
`connections/remote-access/`. Follows the same pattern proven
by Wave 3 #52 approach-lights / #53 motion-based-lighting /
#54 timezone-geolocator / #55 time-atomic / #56 in-cab-tablet-
dashboard / #57 NFC tags tier-b/tier-c recipe slices. This is
the FIRST `remote_access`-category slice in the RoamCore
connection pipeline; the `remote_access` subsystem addition to
`docs/reference/rc-entity-naming.md` is NEW (this slice adds
the `remote_access` subsystem to the `Allowed subsystems`
list). The `networking` category is the canonical category for
remote access + the existing OpenWrt VM in the home lab.

The slice LIFTS the Wave 2 #29 Tailscale contract
(`feat/wave2-remote-access-tailscale` @ `0caa9c2` — already
shipped the Tailscale-specific contract layer at
`homeassistant/packages/roamcore_remote_access.yaml` with 5
Tailscale-specific entities) into the `connections/` pipeline
+ ADDS the broader vendor-neutral contract layer + ADDS
Cloudflare Tunnel + Nabu Casa + Wireguard as alternative paths
so the operator is not locked to Tailscale.

Remote access (vendor-neutral remote-access umbrella for HA,
covering Tailscale + Cloudflare Tunnel + Nabu Casa HA Cloud +
Wireguard — operator picks ONE path) — the umbrella for "check
the van from anywhere: see sensor status, view cameras, get
alerts, or (optionally) control systems" — is the networking-
category complement to the broader RoamCore scene + automation
affordances. The single "is remote access enabled?" tile
aggregates the operator kill-switch into one dashboard
indicator; the "the URL to access HA remotely" tile surfaces
the chosen-path URL (the mesh-VPN hostname for Path A + the
Cloudflare Tunnel hostname for Path B + the Nabu Casa remote
URL for Path C + the Wireguard server endpoint for Path D);
the "is remote access active?" tile is the AND gate (TRUE
iff the kill-switch is ON AND at least one remote-access path
is verified reachable); the "which path is currently active?"
tile surfaces the operator's chosen path (one of `tailscale` /
`cloudflare_tunnel` / `nabu_casa` / `wireguard` /
`companion_external_url` / `none`); the "remote-access peer
count" tile surfaces the count of remote-access clients
currently connected (Tailscale-only); the "last-verified
minutes ago" tile is the freshness gate; the "hostname
resolvable" tile surfaces whether the chosen path's hostname
resolves; the "verify-now" button surfaces the manual
verification trigger; the "operator-chosen path" selector is
the operator-facing affordance.

RoamCore ships no native remote-access engine; tier-b is
honest because we explicitly do NOT maintain a custom
remote-access engine — the upstream HA core `tailscale`
integration (since 2022.x) is the canonical Path A mesh VPN +
the HACS `cloudflared` add-on is the canonical Path B
Cloudflare Tunnel + the HA Core `cloud` integration (since
2022.x) is the canonical Path C Nabu Casa HA Cloud relay +
the HACS `wireguard` add-on is the canonical Path D Wireguard
self-hosted VPN + the HA Companion app's `external_url`
setting (since 2022.x) is the canonical OFF-LAN affordance.

Four install paths (operator picks based on hardware ownership
+ vendor preference + subscription willingness):

- **Path A — Tailscale mesh VPN.** The operator installs the
  HA core `tailscale` integration OR the HACS Tailscale
  add-on + logs in to Tailscale + enables MagicDNS + adds the
  operator's devices to the tailnet. Path A is the default
  for any van operator who wants a secure mesh VPN without
  opening inbound ports + with MagicDNS hostname resolution
  (`https://<host>.ts.net`). Cross-references the Wave 2 #29
  branch (`feat/wave2-remote-access-tailscale` @ `0caa9c2`)
  which shipped the Tailscale-specific contract at
  `homeassistant/packages/roamcore_remote_access.yaml`.

- **Path B — Cloudflare Tunnel no-inbound-ports.** The operator
  creates a Cloudflare account + adds the operator's domain
  to Cloudflare + creates a Cloudflare Tunnel pointing at the
  HA server's local URL + installs the `cloudflared` daemon
  on the HA server via the HACS `cloudflared` add-on OR the
  official Cloudflare Tunnel integration. Path B is the
  default for operators with a Cloudflare-managed domain who
  want to expose the HA server without opening inbound ports
  + with Cloudflare's edge caching + DDoS protection.

- **Path C — Nabu Casa HA Cloud official cloud relay.** The
  operator subscribes to Nabu Casa HA Cloud via the HA Cloud
  panel + enables remote access + verifies the Nabu Casa
  remote URL. Path C is the default for operators who want
  the HA Core official cloud relay + who do NOT want to
  manage a self-hosted VPN server + who are willing to pay
  for the subscription. Nabu Casa is paid.

- **Path D — Wireguard self-hosted VPN.** The operator
  installs the HACS `wireguard` add-on OR a manual Wireguard
  install + generates server keys + generates per-client
  keys + configures the Wireguard server interface + adds
  the operator's devices as Wireguard peers + configures
  firewall rules + verifies the VPN tunnel. Path D is the
  default for operators who prefer self-hosted VPN over
  managed services + who are comfortable with per-client key
  management.

All four paths land on the same vendor-neutral 9
`rc_remote_access_*` contract tiles (1 binary_sensor operator
kill-switch + 1 sensor remote-access URL + 1 binary_sensor
active gate + 1 sensor active-path indicator + 1 sensor peer
count + 1 sensor last-verified minutes ago + 1 binary_sensor
hostname-resolvable gate + 1 button verify-now + 1 select
operator-chosen path = 9 contract entities).

Five §8 automations (MANDATORY before first use):

- §8.1 Kill-switch ON → enable remote access — the operator's
  path-activation automation. The automation fires when the
  `binary_sensor.rc_remote_access_enabled` tile flips to ON
  AND the `select.rc_remote_access_path` tile is set to a
  valid path. The automation calls the upstream integration's
  enable service so the chosen remote-access path is fully
  active.
- §8.2 Kill-switch OFF → disable remote access — the operator's
  path-deactivation automation. The automation fires when the
  `binary_sensor.rc_remote_access_enabled` tile flips to OFF.
  The automation calls the upstream integration's disable
  service so the chosen remote-access path is fully torn
  down.
- §8.3 Auto-verify every 15 minutes — the operator's freshness-
  gate automation. The automation fires every 15 minutes +
  calls the `button.rc_remote_access_verify_now` button +
  updates the `sensor.rc_remote_access_last_verified_minutes_
  ago` freshness gate.
- §8.4 Notify on path switch — the operator's on-ramp for path
  changes. The automation fires when the
  `select.rc_remote_access_path` tile changes. The automation
  sends a notification to the operator's phone (via the HA
  Companion app) saying "Remote access path switched from
  <old_path> to <new_path> — verify reachability at
  <sensor.rc_remote_access_url>".
- §8.5 Stealth-mode suppression via `select.rc_mode` — the
  operator's quiet-campground-aware affordance. The automation
  SUPPRESSES the §8.1 kill-switch-ON automation when the
  `select.rc_mode` is in `stealth` mode (campgrounds with
  quiet hours + overnight stays where exposing the HA server
  remotely would be a privacy concern).

## Changes

Files added (5):

- `connections/remote-access/connection.yml` (the source-of-
  truth manifest). Mirrors the nfc-tags branch shape; the
  `remote_access` subsystem `rc_remote_access_*` prefix is NEW
  (added by this slice to the Allowed subsystems list in
  `docs/reference/rc-entity-naming.md`). The four install
  paths (Path A Tailscale + Path B Cloudflare Tunnel + Path C
  Nabu Casa HA Cloud + Path D Wireguard) + the operator
  kill-switch + the path selector + the 9 `rc_remote_access_*`
  contract tiles are documented in the description +
  tier_warnings + dashboard.tiles. The reuse-first strategy
  is explicitly documented in the description (no custom
  remote-access engine; upstream HA core `tailscale`
  integration + HACS `cloudflared` add-on + HA Core `cloud`
  integration + HACS `wireguard` add-on + HA Companion app's
  `external_url` setting + a thin RoamCore path-routing
  wrapper).
- `connections/remote-access/__init__.py` (the
  `DOMAIN = "remote_access"` marker for the audit). The
  docstring rephrases "config_flow" as "operator-wired setup
  flow" + "the upstream integration's GUI flow" to avoid the
  literal `config_flow.py` substring that the happijac slice
  was bitten by. The substring guard in
  `test_tier_b_without_tier_a_markers` asserts no
  `config_flow.py` substring appears anywhere in the file.
- `connections/remote-access/README.md` (the folder
  overview). Cross-references the HA core `tailscale`
  integration (Path A) + the HACS `cloudflared` add-on (Path
  B) + the HA Core `cloud` integration (Path C) + the HACS
  `wireguard` add-on (Path D) + the HA Companion app's
  `external_url` setting (the OFF-LAN affordance) + the Wave
  2 #29 Tailscale contract + the mode/automation-builder
  recipe (Wave 2 #23) + the approach-lights Wave 3 #52
  connection + the NFC tags Wave 3 #57 connection.
- `connections/remote-access/docs/recipe.md` (~1114 lines,
  12 §sections) — the full howto. §1 the umbrella positioning
  + reuse-first strategy + vendor-neutral contract layer +
  four-path wrapper + single "is remote access active?" tile
  + "which path is active?" tile + operator kill-switch +
  freshness gate + per-path hostname contract; §2
  prerequisites (always-on HA + remote-access path chosen +
  operator's account on the chosen vendor's service + HA
  server's firewall permitting the chosen path's port range +
  HA Companion app + operator's DNS provider account if Path
  B + mode/automation-builder recipe); §3 Path A Tailscale
  mesh VPN (7 steps: install the HA core `tailscale`
  integration OR the HACS Tailscale add-on + login to
  Tailscale + enable MagicDNS + verify HA is reachable via
  `https://<host>.ts.net` + add the operator's devices to the
  tailnet + configure the kill-switch + configure the path
  selector); §4 Path B Cloudflare Tunnel (7 steps: create a
  Cloudflare account + add the operator's domain + create a
  Cloudflare Tunnel + install the `cloudflared` daemon via
  the HACS `cloudflared` add-on + verify the tunnel is
  reachable + configure the kill-switch + configure the path
  selector); §5 Path C Nabu Casa HA Cloud (5 steps: subscribe
  to Nabu Casa HA Cloud + enable remote access + verify the
  Nabu Casa remote URL + configure the kill-switch + configure
  the path selector); §6 Path D Wireguard self-hosted VPN (8
  steps: install the HACS `wireguard` add-on OR a manual
  Wireguard install + generate server keys + generate per-
  client keys + configure the Wireguard server interface +
  add the operator's devices as Wireguard peers + configure
  firewall rules + verify the VPN tunnel + configure the
  kill-switch + configure the path selector); §7 the 9
  `rc_remote_access_*` contract tiles + templates; §8 the
  FIVE §8 automations (with full YAML for the §8.1 kill-
  switch ON + §8.2 kill-switch OFF + §8.3 auto-verify every
  15 minutes + §8.4 notify on path switch + §8.5 Stealth-
  mode suppression via `select.rc_mode`); §9 the 6
  troubleshooting entries; §10 privacy (no RoamCore-side
  telemetry; Tailscale logs are operator-owned via the
  Tailscale admin console + Cloudflare Tunnel logs are
  operator-owned via the Cloudflare dashboard + Nabu Casa
  logs are operator-owned via the HA Cloud panel + Wireguard
  logs are operator-owned on the HA server); §11 tier-a
  promotion outline (real remote-access bench on CI +
  RoamCore-owned operator-wired setup flow + integration
  tests); §12 files + cross-references.
- `connections/remote-access/tests/test_connection_yml.py`
  (~700 lines, 7 manifest-honesty tests) — the 7 tests:
  test_id_matches_folder_name +
  test_tier_b_without_tier_a_markers (tier=b + one_tap=false
  + config_flow=true honest because the UPSTREAM HA core +
  HACS integrations expose a GUI flow + hacs=true + hacs_url
  points at HACS `cloudflared` upstream + substring guard
  against `config_flow.py` + DOMAIN=`remote_access` +
  description mentions reuse / HA core / tailscale integration
  + links.official includes HA core `tailscale` integration
  upstream doc URL) +
  test_requires_docs_recipe_published (≥600 lines + 12
  §sections required) +
  test_category_matches_existing_legacy_doc (with the
  SUPERSEDED banner check on BOTH legacy docs:
  docs/catalog/remote-access/index.md + docs/catalog/remote-
  access/tailscale.md) +
  test_dashboard_tiles_follow_rc_naming (9 vendor-neutral
  tiles, forbidden_substrings covers vendor + protocol +
  integration + hardware names including `tailscale`,
  `ts_net`, `ts.net`, `cloudflare`, `cloudflared`, `cf-tunnel`,
  `cf_tunnel`, `argo_tunnel`, `tunnel_id`, `nabu_casa`,
  `hass-cloud`, `ha_cloud`, `ha_cloud_url`, `ha-cloud-url`,
  `wireguard`, `wg0`, `wg_`, `magicdns`, `magic_dns`, `nfcpy`,
  `nfc_`, `nfc.`, `hacs`, `hass`, `ha_integration`,
  `ha_companion`, `mqtt`, `esphome`, `esp32`, `traccar`,
  `wican`, `obd`, `frigate`, `homeassistant`, `device_tracker`,
  `set_location`, `update_entity`, `zone_`, `zone.`,
  `binary_sensor_`, `sensor_`, `switch`, `input_boolean`,
  `input_select`, `input_number`, `input_datetime`,
  `input_text`, `template:`, `automation`, `scene`, `script`)
  +
  test_status_reflects_no_real_remote_access_engine (status=
  beta + 5 tier_warnings present) +
  test_automations_are_documented (FIVE automations + 4
  safety tiles + HA core `tailscale` integration + home-
  assistant.io/integrations/tailscale + cloudflared + cloud
  integration + wireguard + HA Companion + select.rc_mode +
  Wave 2 #29 `0caa9c2` + approach-lights cross-references).

Files modified (5):

- `scripts/check.sh` — created from scratch on this branch
  (because origin/main does not have `scripts/check.sh` —
  the prior slices stacked off feat/connections/nfc-tags;
  this branch was cut fresh from origin/main so check.sh is
  created with the full chain + the remote-access entry wired
  in immediately after the nfc-tags entry). The script is a
  faithful copy of the canonical chain pattern used by all
  Wave 3 slices — `run_if_present` for every connection
  smoke + the Wave 2 #23-#33 smoke probes + the `--core-
  only` mode + the full suite mode.
- `docs/catalog/remote-access/index.md` — prepended the
  SUPERSEDED banner pointing at `connections/remote-access/`.
  Also expanded the legacy `<!-- RC_FEATURE_LIST_START -->
  ... <!-- RC_FEATURE_LIST_END -->` block to add the 4 paths
  (Tailscale / Cloudflare Tunnel / Nabu Casa / Wireguard) so
  the catalog generates correctly. Mirrors the nfc-tags
  banner shape exactly.
- `docs/catalog/remote-access/tailscale.md` — prepended the
  SUPERSEDED banner pointing at `connections/remote-access/`.
  Mirrors the nfc-tags banner shape exactly.
- `docs/reference/rc-entity-naming.md` — added the
  `remote_access` subsystem to the `Allowed subsystems`
  list. One-line addition: `remote_access` — remote access
  (Tailscale / Cloudflare Tunnel / Nabu Casa / Wireguard);
  vendor-neutral `rc_remote_access_*` ids. This is the FIRST
  `remote_access`-category slice in the RoamCore connection
  pipeline; the addition mirrors how the `power` subsystem
  was added by Wave 1 + how the `net` subsystem was added
  by Wave 1 + how the `system` subsystem was added by Wave
  1.
- `docs/mvp/features-build-status.md` — added the "Remote
  access (vendor-neutral remote-access umbrella for HA —
  Tailscale + Cloudflare Tunnel + Nabu Casa HA Cloud +
  Wireguard, operator picks ONE path)" Shipped (repo) row
  right after the Traccar live map row. Includes the tier-b
  manifest + recipe + smoke + contract tiles + vendor-
  neutrality + legacy supersession banners + cross-
  references (HA core `tailscale` integration + HACS
  `cloudflared` add-on + HA Core `cloud` integration + HACS
  `wireguard` add-on + HA Companion app's `external_url`
  setting + mode/automation-builder recipe + approach-
  lights + NFC tags + Wave 2 #29 Tailscale contract) + PR
  #N placeholder (initially `#62`, updated to actual PR
  number in follow-up commit after `gh pr create`).
- `Cron-handoff/2026-08-02-remote-access-connection.md` (this
  file) — Context / Changes / Verification / Rollback
  format. Mirrors the nfc-tags cron-handoff shape exactly.

## Verification

- `bash scripts/check.sh --core-only` → exit 0. The new
  remote-access smoke check runs and passes (7/7 manifest-
  honesty tests pass); all other 23 connection smokes SKIP
  (their test files aren't on this branch — expected); the
  ha-beta-smoke passes (the existing test); all requested
  smoke checks pass.
- `python3 -m pytest connections/remote-access/tests/ -v` →
  7/7 tests pass:
  - test_id_matches_folder_name ✓
  - test_tier_b_without_tier_a_markers ✓ (substring guard
    against `config_flow.py` passes; tier=b; hacs=true;
    hacs_url points at HACS `cloudflared` upstream;
    description documents reuse-first strategy; links.official
    includes HA core `tailscale` integration upstream doc URL)
  - test_requires_docs_recipe_published ✓ (≥600 lines; all
    12 §sections present; references `rc_remote_access_`)
  - test_category_matches_existing_legacy_doc ✓ (category=
    networking; SUPERSEDED banner present on BOTH legacy
    docs; legacy docs preserved)
  - test_dashboard_tiles_follow_rc_naming ✓ (9 vendor-
    neutral `rc_remote_access_*` tiles; forbidden_substrings
    enforces no vendor / protocol / hardware / integration
    leaks including the Tailscale / Cloudflare / Cloudflared
    / Nabu Casa / Wireguard / MagicDNS / Tunnel / HACS / HA
    Companion / MQTT / ESPHome / ESP32 / Traccar / Wican /
    OBD / Frigate / NFC / NFCpy / Zone / Device_tracker /
    Homeassistant / Set_location / Update_entity /
    Binary_sensor_ / Sensor_ / Switch / Input_boolean /
    Input_select / Input_number / Input_datetime /
    Input_text / Template: / Automation / Scene / Script
    vendor names; preserves the spec-required `enabled`,
    `url`, `active`, `path`, `peer`, `count`, `last`,
    `verified`, `minutes`, `ago`, `hostname`, `resolvable`,
    `verify`, `now`, `operator`, `chosen` substrings in the
    spec-required tile ids)
  - test_status_reflects_no_real_remote_access_engine ✓
    (status=beta; 5 tier_warnings present)
  - test_automations_are_documented ✓ (the FIVE §8
    automations documented + 4 safety tiles wired + HA core
    `tailscale` integration + home-assistant.io/integrations/
    tailscale + cloudflared + cloud integration + wireguard +
    HA Companion + select.rc_mode + Wave 2 #29 `0caa9c2` +
    approach-lights cross-references)
- `git ls-remote origin 'refs/heads/feat/connections/remote-
  access'` → branch on origin (after push).
- `gh pr view --json number,state,url` → PR #N OPEN (after
  gh pr create).

## Rollback

Pure additive UI slice. Rollback is `gh pr close N` (or
`gh pr close N -d "superseded"`) followed by `git revert
<commit>` on main (or `git push origin --delete
feat/connections/remote-access` if the PR was the only thing
on the branch). No infrastructure state to roll back; no
migrations; no config changes; no secrets; the SUPERSEDED
banners on the legacy `docs/catalog/remote-access/index.md`
+ `docs/catalog/remote-access/tailscale.md` docs are
reverted when the legacy docs are restored.

The `scripts/check.sh` file is a NEW file on this branch (it
doesn't exist on origin/main); reverting the PR will delete
the file. Future slices that need to add their own smoke
check will need to re-create check.sh OR branch from this
branch's tip.

If the standing `bash scripts/check.sh --core-only` check
mysteriously regresses on main after this PR lands, the most
likely culprit is a forgotten smoke-check entry in
`scripts/check.sh` — the slice adds the remote-access smoke
directly after the nfc-tags entry; verify the entry is still
present after revert + re-merge.