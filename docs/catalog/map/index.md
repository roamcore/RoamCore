# Map

This folder is the **Map** tag in the RoamCore catalog.

## Overview
Maps and location features help you understand where the van is, where it’s been, and what’s nearby. This section includes tracking, trip history, offline maps, and overlays that can make planning and “where did we park?” moments much easier.

## What belongs here
- Features/integrations related to **Map**.

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
  <a class="rc-feature" href="map-dashboard.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">RoamCore Map (dashboard + route)</div><div class="rc-feature-sub">RoamCore provides a map experience inside Home Assistant, including current location and route/trip context.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="mock-location-and-tracks.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Mock location + tracks (dev/demo)</div><div class="rc-feature-sub">RoamCore includes developer/demo mocks for location trails and tracks, useful for testing map and Trip Wrapped flows without real driving data.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="offline-tileserver.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Offline maps / Tile server (PMTiles)</div><div class="rc-feature-sub">RoamCore includes a local tile server path so maps can render reliably without depending on third-party map providers.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="roamcore-tileserver-addon.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">RoamCore TileServer add-on</div><div class="rc-feature-sub">A Home Assistant add-on that serves map tiles locally for reliable map rendering.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="traccar-init-addon.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Traccar Init add-on (first boot provisioning)</div><div class="rc-feature-sub">An add-on to help with first-boot provisioning for Traccar-backed flows.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="traccar-proxy-addon.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Traccar Proxy add-on</div><div class="rc-feature-sub">A Home Assistant add-on that proxies Traccar endpoints to make setup and local integration more reliable.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="traccar.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Traccar (GPS tracking) integration</div><div class="rc-feature-sub">RoamCore ships Traccar support via its own proxy/init components so you can use Traccar as a reliable location history source in Home Assistant.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="trip-local.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Trip Local (local GPX / local trip tools)</div><div class="rc-feature-sub">RoamCore includes a “Trip Local” path for working with local trip data/tools inside Home Assistant.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
  <a class="rc-feature" href="trip-wrapped.md" data-tier="a"><div class="rc-feature-left"><div class="rc-feature-title">Trip Wrapped (route recap report)</div><div class="rc-feature-sub">Trip Wrapped generates a shareable, beautiful HTML report of a trip/route.</div></div><div class="rc-feature-right"><span class="rc-tier a">A</span></div></a>
</div>

<!-- RC_FEATURE_LIST_END -->
