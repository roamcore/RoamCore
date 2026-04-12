# Support tier A

One long page listing every feature currently tagged with this tier, grouped by category.

Tip: use your browser’s find (Ctrl/Cmd+F) to jump quickly (e.g. ‘victron’, ‘tailscale’).

## Ai

- [Advanced Mode (power-user toggle)](ai/advanced-mode/) — RoamCore includes an Advanced Mode toggle that can reveal extra controls and diagnostics without cluttering the default UI.
- [Agent actions allowlist (safety gateway)](ai/agent-actions-allowlist/) — A safety layer that defaults to deny and only permits explicitly-allowed agent actions, with a kill switch.
- [Demo Mode (safe demo values)](ai/demo-mode/) — Demo Mode lets RoamCore show example values when critical sensors are missing, so the UI still looks and feels complete during setup or demo
- [Mode (Auto / Travel / Camp / Stealth)](ai/mode/) — RoamCore defines a simple “Mode” entity and convenience scripts (Auto/Travel/Camp/Stealth/Off). This shows up as a user-facing control in th
- [OpenClaw JSON API (local agent contract)](ai/openclaw-json-api/) — RoamCore exposes stable JSON endpoints for local agents (system summary + skill execution) so assistants can read state and (optionally) tak

## Homelab

- [Home Assistant installer (one-line)](homelab/ha-installer/) — RoamCore ships `install.sh`/`uninstall.sh` to install the integration and assets into Home Assistant.
- [Support bundle export (logs + config snapshot)](homelab/support-bundle/) — A documented way to generate a support bundle so issues can be debugged quickly without back-and-forth.

## Hvac

- [HVAC control (heating/cooling foundations)](hvac/hvac-basics/) — RoamCore includes scaffolding and patterns for HVAC-related controls/tiles (temperature, comfort, alerts). Specific heater/AC hardware integ

## Level Sensor

- [Levelling sensor (pitch/roll + “are we level?”)](level-sensor/leveling/) — RoamCore defines a levelling contract (`rc_level_*`) and supports pitch/roll sensors so the dashboard can show an easy levelling status.

## Map

- [Mock location + tracks (dev/demo)](map/mock-location-and-tracks/) — RoamCore includes developer/demo mocks for location trails and tracks, useful for testing map and Trip Wrapped flows without real driving da
- [Offline maps / Tile server (PMTiles)](map/offline-tileserver/) — RoamCore includes a local tile server path so maps can render reliably without depending on third-party map providers.
- [RoamCore Map (dashboard + route)](map/map-dashboard/) — RoamCore provides a map experience inside Home Assistant, including current location and route/trip context.
- [RoamCore TileServer add-on](map/roamcore-tileserver-addon/) — A Home Assistant add-on that serves map tiles locally for reliable map rendering.
- [Traccar (GPS tracking) integration](map/traccar/) — RoamCore ships Traccar support via its own proxy/init components so you can use Traccar as a reliable location history source in Home Assist
- [Traccar Init add-on (first boot provisioning)](map/traccar-init-addon/) — An add-on to help with first-boot provisioning for Traccar-backed flows.
- [Traccar Proxy add-on](map/traccar-proxy-addon/) — A Home Assistant add-on that proxies Traccar endpoints to make setup and local integration more reliable.
- [Trip Local (local GPX / local trip tools)](map/trip-local/) — RoamCore includes a “Trip Local” path for working with local trip data/tools inside Home Assistant.
- [Trip Wrapped (route recap report)](map/trip-wrapped/) — Trip Wrapped generates a shareable, beautiful HTML report of a trip/route.

## Networking

- [OpenWrt router controls (WAN status + sensors)](networking/openwrt-controls/) — RoamCore includes an OpenWrt API integration path to surface WAN/internet state into HA and enable safe control flows.

## Power

- [Victron Auto add-on (backend connector)](power/victron-auto-addon/) — A Home Assistant add-on used by RoamCore to connect to Victron telemetry automatically and keep power entities up to date.
- [Victron Mock add-on (demo power data)](power/victron-mock-addon/) — A demo/mock backend that generates Victron-like power telemetry for development and demos.
- [Victron power monitoring (GX + MQTT)](power/victron/) — RoamCore includes a Victron integration path that turns your Victron GX + battery/solar system into clean Home Assistant entities (SOC, sola

## Safety

- [Smart Automations (one-click enable)](safety/smart-automations/) — A small set of prebuilt automations you can enable/disable from the RoamCore UI (implemented as native HA automations under the hood).

