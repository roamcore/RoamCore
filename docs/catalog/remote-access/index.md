# Remote Access

This folder is the **Remote Access** tag in the RoamCore catalog.

## Overview
Remote access lets you check on the van from anywhere: see sensor status, view cameras, get alerts, or (optionally) control systems. This section covers safe ways to reach Home Assistant remotely, with clear notes on security and support level.

## What belongs here
- Features/integrations related to **Remote Access**.

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
  <a class="rc-feature" href="tailscale.md" data-tier="b"><div class="rc-feature-left"><div class="rc-feature-title">Tailscale (secure remote access)</div><div class="rc-feature-sub">Tailscale is a simple, secure mesh VPN. It’s a great way to access Home Assistant remotely without opening ports or relying on complex networking.</div></div><div class="rc-feature-right"><span class="rc-tier b">B</span></div></a>
</div>

<!-- RC_FEATURE_LIST_END -->
