# Safety

This folder is the **Safety** tag in the RoamCore catalog.

## Overview
Safety is about early warning and clear alerts: CO/smoke, propane, leaks, low battery, and temperature risks. This section focuses on integrations and recipes that help you catch problems fast—especially when you’re asleep or away from the van.

## What belongs here
- Features/integrations related to **Safety**.

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
  <a class="rc-feature" href="deadbolts.md" data-tier="b"><div class="rc-feature-left"><div class="rc-feature-title">Deadbolts (smart locks)</div><div class="rc-feature-sub">Smart deadbolts let you monitor lock state (locked/unlocked) and (optionally) control it from Home Assistant.</div></div><div class="rc-feature-right"><span class="rc-tier b">B</span></div></a>
  <a class="rc-feature" href="smart-automations.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Smart Automations (one-click enable)</div><div class="rc-feature-sub">A small set of prebuilt automations you can enable/disable from the RoamCore UI (implemented as native HA automations under the hood).</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="smoke-co-gas-sensors.md" data-tier="b"><div class="rc-feature-left"><div class="rc-feature-title">Smoke / CO / Gas sensors</div><div class="rc-feature-sub">Safety sensors that trigger clear alerts when something dangerous happens: smoke, carbon monoxide, propane/LPG, or other gases.</div></div><div class="rc-feature-right"><span class="rc-tier b">B</span></div></a>
</div>

<!-- RC_FEATURE_LIST_END -->
