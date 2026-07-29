# PWA (Progressive Web App) — phone-installed dashboard

**Support tier:** B (RoamCore tier-b / community-supported)

## What this is
The RoamCore dashboard installed as a standalone app on your phone
(Android, iOS, desktop). Loads from a cached service worker so it
works without network, and supports push notifications via a
user-supplied VAPID key.

## Why it’s useful in a van
- Phone-home-screen icon with no browser chrome.
- Dashboard still works when LTE drops (cache-first shell).
- Get push notifications from your own self-hosted relay — no
  third-party trackers, no RoamCore-hosted relay.

## Extra hardware required
- None (any modern phone with a tier-b-supported browser).

## Install / best next step
- See: `docs/setup/pwa.md`
- Source: `dashboard/Frontend/Setup Wizard/` (manifest + sw + pwa.js).

## Links
- (Add troubleshooting video/resources later)