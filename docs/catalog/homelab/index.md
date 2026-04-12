# Homelab

This folder is the **Homelab** tag in the RoamCore catalog.

## Overview
Some vanlifers run a small “homelab on wheels”: a mini PC, NAS, router, cameras, and local services. This section covers useful self-hosted tools and integrations that can run locally (even without internet) for more privacy and reliability.

## What belongs here
- Features/integrations related to **Homelab**.

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
  <a class="rc-feature" href="adguard-home.md" data-tier="b"><div class="rc-feature-left"><div class="rc-feature-title">AdGuard Home (network-wide ad blocking)</div><div class="rc-feature-sub">AdGuard Home is an alternative to Pi-hole: DNS-based ad/tracker blocking with a nice UI.</div></div><div class="rc-feature-right"><span class="rc-tier b">B</span></div></a>
  <a class="rc-feature" href="ha-installer.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Home Assistant installer (one-line)</div><div class="rc-feature-sub">RoamCore ships `install.sh`/`uninstall.sh` to install the integration and assets into Home Assistant.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="nas.md" data-tier="b"><div class="rc-feature-left"><div class="rc-feature-title">NAS (Network Attached Storage)</div><div class="rc-feature-sub">A NAS gives you reliable local storage for media, camera footage, backups, and logs—especially useful when you don’t want to depend on cloud services.</div></div><div class="rc-feature-right"><span class="rc-tier b">B</span></div></a>
  <a class="rc-feature" href="pi-hole.md" data-tier="b"><div class="rc-feature-left"><div class="rc-feature-title">Pi-hole (network-wide ad blocking)</div><div class="rc-feature-sub">Pi-hole blocks ads and trackers for every device on your network by acting as DNS.</div></div><div class="rc-feature-right"><span class="rc-tier b">B</span></div></a>
  <a class="rc-feature" href="support-bundle.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Support bundle export (logs + config snapshot)</div><div class="rc-feature-sub">A documented way to generate a support bundle so issues can be debugged quickly without back-and-forth.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
</div>

<!-- RC_FEATURE_LIST_END -->
