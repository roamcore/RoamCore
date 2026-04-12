# Networking

This folder is the **Networking** tag in the RoamCore catalog.

## Overview
Internet in a van is usually a mix of Wi‑Fi, LTE/5G, and sometimes Starlink. This section covers ways to monitor connectivity, failover between WANs, and basic network health—so you know when things are working (or why they aren’t).

## What belongs here
- Features/integrations related to **Networking**.

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
  <a class="rc-feature" href="catalog/networking/openwrt-controls.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">OpenWrt router controls (WAN status + sensors)</div><div class="rc-feature-sub">## What this is</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="catalog/networking/peplink.md" data-tier="c"><div class="rc-feature-left"><div class="rc-feature-title">Peplink (multi-WAN router for van internet)</div><div class="rc-feature-sub">## What this is</div></div><div class="rc-feature-right"><span class="rc-tier c">C</span></div></a>
  <a class="rc-feature" href="catalog/networking/teltonika.md" data-tier="c"><div class="rc-feature-left"><div class="rc-feature-title">Teltonika (LTE/5G router for vans)</div><div class="rc-feature-sub">## What this is</div></div><div class="rc-feature-right"><span class="rc-tier c">C</span></div></a>
</div>

<!-- RC_FEATURE_LIST_END -->
