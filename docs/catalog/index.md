# What RoamCore connects to

RoamCore talks to the things in your van — power, water, heating, lights,
internet, location — and shows you what's happening on one dashboard.


## Tier legend

How to read the letters next to each feature:

- **A — Full** — RoamCore maintains this natively. Vendor-neutral contract (`rc_*`), automated tests, no upstream dependency.
- **B — Partial** — RoamCore wraps an existing Home Assistant integration or upstream project. Works, but may have gaps; you depend on the upstream project for some functionality.
- **C — 3rd party** — RoamCore provides a thin layer on top of someone else's project (e.g. NFC tags, dashboard tablet). You're relying on their maintenance.

## Power

Batteries, solar, shore power, and inverter control. See state of charge,
how fast you're charging, and whether you need to plug in tonight.

[Browse Power](power/)

## Water

Fresh and grey water tanks, pump status, leak detection, and freeze-risk
monitoring.

[Browse Water](water/)

## Comfort

Lights, fans, HVAC, bed lift, audio — the everyday "make the van feel
like home" automations.

[Browse Comfort](comfort/)

## Connectivity

Mobile internet, Starlink, Wi-Fi management, and remote access.

[Browse Connectivity](connectivity/)

## Location

Map, GPS tracking, presence detection, and trip history.

[Browse Location](location/)

## Safety

Smoke, CO, gas sensors, smart locks, and prebuilt safety automations.

[Browse Safety](safety/)

## Security

NFC tags and other quick-access controls.

[Browse Security](security/)

## Automation

Van "modes" (driving, parked, quiet night) and other state-based
automations.

[Browse Automation](automation/)

## Maintenance

Tablet dashboards, leveling, and other keep-the-van-working features.

[Browse Maintenance](maintenance/)

## Miscellaneous

Anything that doesn't fit a category — NAS, atomic time, timezone sync.

[Browse Misc](misc/)