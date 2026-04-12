# Bed Lift

This folder is the **Bed Lift** tag in the RoamCore catalog.

## Overview
A bed lift can save space and make daily life smoother—if it’s reliable and easy to control. This section covers sensors and controls for lift systems (buttons, limit switches, position sensors), plus safety-focused recipes like “lock out movement when something is in the way”.

## What belongs here
- Features/integrations related to **Bed Lift**.

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
  <a class="rc-feature" href="diy-bedlift.md" data-tier="c"><div class="rc-feature-left"><div class="rc-feature-title">DIY bed lift (actuators / motor + strap)</div><div class="rc-feature-sub">A DIY bed lift is usually either linear actuators or a winch/motor + strap system, controlled by a relay/driver and protected with limit switches.</div></div><div class="rc-feature-right"><span class="rc-tier c">C</span></div></a>
  <a class="rc-feature" href="happijac.md" data-tier="c"><div class="rc-feature-left"><div class="rc-feature-title">HappiJac bed lift</div><div class="rc-feature-sub">HappiJac bed lifts are a popular off-the-shelf system. The HA integration is usually custom because the stock controller is not designed as a smart-home device.</div></div><div class="rc-feature-right"><span class="rc-tier c">C</span></div></a>
</div>

<!-- RC_FEATURE_LIST_END -->
