# OpenWrt router controls (WAN status + sensors)

**Support tier:** A (RoamCore native)

## What this is
RoamCore includes an OpenWrt API integration path to surface WAN/internet state into HA and enable safe control flows.

## Why it’s useful in a van
- Know which internet source is active
- Quickly spot “no internet” vs “Wi‑Fi connected but captive portal”

## Extra hardware required
- An OpenWrt router (or OpenWrt VM)

## Install / best next step
- HA package: `homeassistant/packages/roamcore_openwrt_api.yaml`
- Sensors: `homeassistant/packages/roamcore_net.yaml`

## Links
- OpenWrt: https://openwrt.org/

---

## SUPERSEDED — recipe connection has landed

The tier-a recipe connection for this feature now lives at `connections/openwrt-controls/` (Wave 8 #315, PR #83). The new connection folder adds the manifest + the `docs/recipe.md` howto + the manifest-honesty smoke check + the 27 vendor-neutral `rc_openwrt_*` + `rc_net_openwrt_*` contract tiles + the 4 `script.rc_openwrt_*` control scripts + the 5 safety tiles + the FOUR §8 MANDATORY automations (prefer-WAN selector drives the correct script + LTE-SIM-missing alert + firewall-state alert + restart-network confirm guard) + the cross-references to dns-blocker Wave 3 #37 + remote-access Wave 3 #58 + openclaw-api Wave 3 #64 + agent-actions-allowlist Wave 3 #65 + advanced-mode Wave 3 #63 + demo-mode Wave 3 #62 + mode Wave 3 #61 + mqtt Wave 3 #34 + network-mode Wave 4 #75.

This legacy 21-line tier-a claim stub is preserved verbatim above for the catalog scrapers + the operator-facing discovery flow. See `connections/openwrt-controls/README.md` + `connections/openwrt-controls/docs/recipe.md` for the full howto.

The two RoamCore-owned packages (`homeassistant/packages/roamcore_openwrt_api.yaml` + `homeassistant/packages/roamcore_net.yaml`) are preserved verbatim on main — the slice ONLY references them as existing upstream sources via `install.packages:` (no modifications to the package contents).
