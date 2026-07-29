# RoamCore PWA — install, offline, and push setup

This is the user guide for the RoamCore Progressive Web App (PWA) —
the phone-installed version of the dashboard. The PWA ships with
RoamCore itself, lives at `dashboard/Frontend/Setup Wizard/`, and is
entirely client-side.

## What this is

The RoamCore PWA is the same dashboard you see in Home Assistant, but
installed on your phone (or tablet) as a standalone app. It loads from
a cached service worker so it works when LTE drops, and it supports
push notifications through a user-supplied VAPID key.

There is no separate "PWA server" — it's the same static files that
Home Assistant already serves, with an added service worker, manifest,
and install/offline/push glue.

## Privacy

RoamCore takes privacy seriously, and the PWA follows the same rules
as the rest of the project:

- **No telemetry.** The PWA does not phone home, does not track usage,
  and does not include analytics SDKs.
- **No third-party CDN.** Every script, font, and asset ships from the
  RoamCore origin (the same Home Assistant host serving the dashboard).
- **Push is user-supplied.** RoamCore does **not** run a push relay.
  You bring your own VAPID key pair, host the relay wherever you want
  (a $5 VPS, a Pi at home, or a free-tier Cloudflare Worker), and the
  subscription endpoint is displayed in the PWA so you can wire it
  into your own server.
- **Offline outbox is local.** Writes queued while offline live in
  your browser's `localStorage` only. They do not leave the device
  until the next `online` event.

## Supported browsers

The PWA is a tier-b (community-supported) feature. It is tested
against:

| Browser                 | Minimum version |
|-------------------------|-----------------|
| Chrome (desktop, Android) | 121+           |
| Edge                    | 121+             |
| Firefox (desktop, Android) | 121+          |
| Safari (iOS / iPadOS)   | 16.4+ (Add-to-Home-Screen only) |

If your browser is older, the dashboard still loads — you simply lose
the install, offline, and push features.

## Install steps

### Chrome / Edge / Firefox (Android or desktop)

1. Open the RoamCore dashboard in your browser.
2. Wait for the install button to appear (top-right of the ready card
   after the shell finishes loading).
3. Tap **Install RoamCore**.
4. Confirm in the browser's install prompt.

If you don't see the button, the browser hasn't fired
`beforeinstallprompt` yet — usually because the page has only just
loaded. Refresh and wait a couple of seconds.

### iOS / iPadOS (Safari 16.4+)

iOS doesn't fire `beforeinstallprompt`. To install:

1. Open the RoamCore dashboard in Safari.
2. Tap the **Share** button (square with the up arrow).
3. Scroll down and tap **Add to Home Screen**.
4. Confirm the name and tap **Add**.

RoamCore shows a small hint card in-app the first time it detects iOS
Safari, so you don't need to remember these steps.

### After install

The app icon launches RoamCore in standalone mode (no browser chrome).
The header pill shows `online` / `offline` based on
`navigator.onLine`. The dashboard works without a connection once it
has been loaded at least once online.

## Offline behavior

The service worker pre-caches the app shell on install:

- `index.html`
- `manifest.json`
- `icon-192.svg`, `icon-512.svg`
- `pwa.js` (install / offline / push glue)

Every other request follows **cache-first** with a network fallback,
which means:

- **Cached and offline-ready:** the dashboard shell, icons, manifest.
- **Cached opportunistically:** any same-origin GET that returns a
  `200 basic` response — i.e. the next time you load the dashboard.
- **Not cached:** cross-origin requests, POST/PUT/PATCH/DELETE writes,
  opaque (CORS-blocked) responses, and anything that returns a
  non-`200` status.

### The offline outbox

When the device is offline and the PWA tries to call a write endpoint,
the call is queued in `localStorage` under the key `rc_outbox`
(capped at **50** entries). On the next `online` event, the outbox is
flushed.

This slice ships the **wiring** (queue + cap + flush trigger) so the
mechanism is exercised by the smoke gate. Real endpoints wire up once
the tile layer lands; the queue will start carrying actual contract
writes at that point.

## Push setup

Push notifications are **opt-in** and require a VAPID key pair that
**you** generate. RoamCore does not provide a relay.

### 1. Generate a VAPID pair

```bash
# One-off install (or use `pipx run`, `uv tool run`, etc.)
pip install py-vapid
vapid --gen
```

This prints two keys:

- **Application Server Key** (private) — stays on your relay server.
- **Public Key** (base64url) — what you paste into the PWA.

### 2. Paste the public key into RoamCore

In the installed PWA:

1. Open the **Push notifications** card.
2. Paste the **public key** into the input field.
3. Tap **Subscribe**.

The subscription endpoint is displayed below the buttons — copy it.

### 3. Wire the subscription into your relay

Point your own relay at the subscription endpoint. RoamCore ships no
relay on purpose, but any standard Web Push server works:

- [`web-push`](https://www.npmjs.com/package/web-push) (Node)
- [`pywebpush`](https://pypi.org/project/pywebpush/) (Python)
- [`vapid-cli`](https://www.npmjs.com/package/vapid-cli) for quick
  tests: `vapid push <endpoint> --notify`

### 4. Test

Tap **Test push** in the PWA to verify the SW notification path. The
test uses `registration.showNotification` directly and does **not**
require a backend.

## Troubleshooting

- **Install button doesn't appear.** The browser hasn't fired
  `beforeinstallprompt` yet. Most browsers require the page to have
  loaded completely and to be served over HTTPS (or `localhost`).
- **iOS hint doesn't show.** Either you're already running as a
  standalone app, or you're in an in-app browser (Facebook, IG,
  etc.). Open the page in Safari directly.
- **Push "missing-vapid-key".** Paste the public key into the input
  and tap **Subscribe** again.
- **Outbox growing past 50 entries.** The cap is intentional; very
  old entries are dropped first. If you're seeing this, your relay
  is probably down — check its logs.
- **Stale shell after an update.** Hard-refresh the dashboard once
  (or close + reopen the installed app). The service worker bumps
  `RC_CACHE_VERSION` on every release.

## What's next

Future slices will:

- Wire real contract endpoints into the outbox flush (so writes
  actually carry, not just queue).
- Expose `rc_pwa_online` as a true HA template variable so Lovelace
  can mirror the offline pill.
- Add a richer iOS hint that detects the *first* install (using
  `localStorage` rather than `navigator.standalone`).
- Auto-detect the VAPID key from a config file instead of a paste.

For now, the scaffold is enough to install RoamCore on your phone,
work offline, and get user-controlled push notifications — without
sending a single byte to anyone but your own relay.