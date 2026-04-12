# Power

This folder is the **Power** tag in the RoamCore catalog.

## Overview
Power is the heart of van life: batteries, solar, shore power, inverter/charger, and how long you can comfortably run everything. This section covers integrations and features that help you monitor state-of-charge, spot problems early, and automate “power-safe” behavior.

## What belongs here
- Features/integrations related to **Power**.

## Support tiers
- **A** = RoamCore native (supported)
- **B** = Home Assistant supported (existing integration; setup required)
- **C** = Custom/manual (no support; inspiration/potential)

## Page checklist (per item)
Every page should include:
1) **Support tier** (A/B/C)
2) **Extra hardware required** (explicit; assume HA-only otherwise)
3) **A clear install CTA** (button/link to best install path)
4) **Links** section at the bottom

## Add a new item
- Copy: `docs/catalog/_templates/integration-page.template.md`
- Place into this folder with a clear filename, e.g. `diesel-heater.md`

<!-- RC_FEATURE_LIST_START -->

## Features

<div class="rc-feature-list">
  <a class="rc-feature" href="victron-auto-addon.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Victron Auto add-on (backend connector)</div><div class="rc-feature-sub">A Home Assistant add-on used by RoamCore to connect to Victron telemetry automatically and keep power entities up to date.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="victron-mock-addon.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Victron Mock add-on (demo power data)</div><div class="rc-feature-sub">A demo/mock backend that generates Victron-like power telemetry for development and demos.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="victron.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Victron power monitoring (GX + MQTT)</div><div class="rc-feature-sub">RoamCore includes a Victron integration path that turns your Victron GX + battery/solar system into clean Home Assistant entities (SOC, solar watts, etc.) and d</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
</div>

<!-- RC_FEATURE_LIST_END -->
