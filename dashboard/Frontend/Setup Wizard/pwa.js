/*
 * RoamCore PWA tier-b client glue.
 *
 *   Day 1 (0b6a2ba) shipped a static manifest + service worker + app
 *   shell. This slice upgrades that scaffold to production-grade:
 *
 *     - Real install (beforeinstallprompt + iOS Add-to-Home-Screen hint)
 *     - Offline detection (navigator.onLine pill + localStorage outbox)
 *     - Push notifications (user-supplied VAPID key, no RoamCore relay)
 *
 *   Privacy:
 *     - No telemetry, no analytics, no third-party CDN.
 *     - Push subscription is opt-in: the user pastes their own VAPID
 *       public key. The subscription endpoint is displayed so they can
 *       wire it into their own push relay. RoamCore hosts no relay.
 *     - Outbox only persists in localStorage on this device.
 *
 *   Style:
 *     - Vanilla DOM, design tokens from index.html :root vars only.
 *     - No frameworks, no bundlers, no new top-level dependencies.
 */

(function () {
  'use strict';

  // ----- Configuration constants (kept in sync with sw.js) -----
  const RC_CACHE_VERSION = 'rc-shell-v1';        // mirrored; sw.js bumps to v2
  const RC_OUTBOX_KEY = 'rc_outbox';
  const RC_OUTBOX_MAX = 50;
  const RC_VAPID_KEY_STORAGE = 'rc_vapid_public_key';
  const RC_SUBSCRIPTION_STORAGE = 'rc_push_subscription';

  // ----- Helpers -----
  function $id(id) { return document.getElementById(id); }

  function isIOS() {
    // iPad/iPhone/iPod on Safari (excludes in-app browsers).
    const ua = (navigator.userAgent || '').toLowerCase();
    const isiOS = /ipad|iphone|ipod/.test(ua);
    const isStandalone = window.navigator.standalone === true;
    return isiOS && !isStandalone;
  }

  function safeParse(raw, fallback) {
    try { return JSON.parse(raw); } catch (_e) { return fallback; }
  }

  // ----- Connectivity pill (extension of Day 1) -----
  function rcUpdateConn() {
    const el = $id('rc-conn');
    if (!el) return;
    const online = navigator.onLine;
    el.textContent = online ? 'online' : 'offline';
    el.classList.toggle('rc-status-ok', online);
    el.classList.toggle('rc-status-offline', !online);
    el.setAttribute('data-rc-online', online ? '1' : '0');
  }
  window.addEventListener('online', rcUpdateConn);
  window.addEventListener('offline', rcUpdateConn);
  rcUpdateConn();

  // ----- Install prompt (real install) -----
  // Capture the event so we can fire it from our own button instead of
  // relying on the browser's passive mini-bar.
  let deferredInstallPrompt = null;
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    const btn = $id('rc-pwa-install-btn');
    if (btn) btn.hidden = false;
    const ev = new CustomEvent('rc-pwa-installable', { detail: { available: true } });
    window.dispatchEvent(ev);
  });

  function rcTriggerInstall() {
    const btn = $id('rc-pwa-install-btn');
    if (!deferredInstallPrompt) {
      if (btn) btn.setAttribute('data-rc-install-state', 'unavailable');
      return;
    }
    deferredInstallPrompt.prompt();
    deferredInstallPrompt.userChoice.then((choice) => {
      if (btn) btn.setAttribute('data-rc-install-state', choice.outcome || 'unknown');
      deferredInstallPrompt = null;
    }).catch(() => {
      if (btn) btn.setAttribute('data-rc-install-state', 'error');
      deferredInstallPrompt = null;
    });
  }
  window.rcTriggerInstall = rcTriggerInstall;

  // Bind the install button (works even if the prompt already fired).
  document.addEventListener('DOMContentLoaded', () => {
    const btn = $id('rc-pwa-install-btn');
    if (btn) {
      btn.addEventListener('click', rcTriggerInstall);
      // If the page loaded after the prompt already fired, hide the button.
      if (!deferredInstallPrompt && !isIOS()) btn.hidden = true;
    }
  });

  // ----- iOS Add-to-Home-Screen hint -----
  function rcShowIosHint() {
    if (!isIOS()) return;
    const card = $id('rc-pwa-ios-hint');
    if (!card) return;
    card.hidden = false;
    card.setAttribute('data-rc-shown', '1');
  }
  function rcHideIosHint() {
    const card = $id('rc-pwa-ios-hint');
    if (!card) return;
    card.hidden = true;
  }
  window.rcShowIosHint = rcShowIosHint;
  window.rcHideIosHint = rcHideIosHint;
  document.addEventListener('DOMContentLoaded', () => {
    rcShowIosHint();
    const close = $id('rc-pwa-ios-hint-close');
    if (close) close.addEventListener('click', rcHideIosHint);
  });

  // ----- Offline outbox (localStorage-backed) -----
  // A future slice will wire actual API calls. For now, the queue exists
  // and is exercised by the smoke gate. Capped at RC_OUTBOX_MAX entries.
  const RcOutbox = {
    list() {
      return safeParse(window.localStorage.getItem(RC_OUTBOX_KEY) || '[]', []);
    },
    push(entry) {
      const items = RcOutbox.list();
      items.push(Object.assign({ ts: Date.now() }, entry));
      if (items.length > RC_OUTBOX_MAX) items.splice(0, items.length - RC_OUTBOX_MAX);
      window.localStorage.setItem(RC_OUTBOX_KEY, JSON.stringify(items));
      return items.length;
    },
    clear() {
      window.localStorage.removeItem(RC_OUTBOX_KEY);
    },
    size() {
      return RcOutbox.list().length;
    },
  };
  window.RcOutbox = RcOutbox;

  // ----- API wrapper that auto-queues writes when offline -----
  // Pure stub for the scaffold: in slice #10 we only prove the wiring.
  // Real contract endpoints land once tiles arrive.
  async function rcFetchMaybeQueue(url, options) {
    const opts = Object.assign({ method: 'GET' }, options || {});
    if (opts.method === 'GET' || navigator.onLine) {
      // Try the network; on failure, fall back to cache via the SW.
      try { return await fetch(url, opts); }
      catch (e) { return Response.error(); }
    }
    // Offline + write: queue and report a synthetic 202.
    RcOutbox.push({ url: url, method: opts.method, body: opts.body || null });
    return new Response(JSON.stringify({ queued: true }), {
      status: 202, headers: { 'content-type': 'application/json' }
    });
  }
  window.rcFetchMaybeQueue = rcFetchMaybeQueue;

  // Flush the outbox when connectivity returns. No-op until real endpoints exist.
  async function rcFlushOutbox() {
    if (!navigator.onLine) return 0;
    const items = RcOutbox.list();
    if (!items.length) return 0;
    // Placeholder: in this slice we just clear after counting. Real relay
    // calls happen once backend integration lands.
    RcOutbox.clear();
    return items.length;
  }
  window.rcFlushOutbox = rcFlushOutbox;
  window.addEventListener('online', rcFlushOutbox);

  // ----- Push notifications (user-supplied VAPID) -----
  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = window.atob(base64);
    const out = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; ++i) out[i] = raw.charCodeAt(i);
    return out;
  }

  async function rcSubscribePush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      return { ok: false, error: 'push-not-supported' };
    }
    const keyRaw = (window.localStorage.getItem(RC_VAPID_KEY_STORAGE) || '').trim();
    if (!keyRaw) {
      return { ok: false, error: 'missing-vapid-key' };
    }
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(keyRaw),
    });
    const json = sub.toJSON();
    window.localStorage.setItem(RC_SUBSCRIPTION_STORAGE, JSON.stringify(json));
    const out = $id('rc-pwa-push-endpoint');
    if (out) out.textContent = json.endpoint || '(no endpoint)';
    return { ok: true, endpoint: json.endpoint };
  }
  window.rcSubscribePush = rcSubscribePush;

  async function rcTestPush() {
    if (!('serviceWorker' in navigator)) return { ok: false, error: 'sw-unsupported' };
    const reg = await navigator.serviceWorker.ready;
    await reg.showNotification('RoamCore', {
      body: 'Test',
      tag: 'rc-pwa-test',
    });
    return { ok: true };
  }
  window.rcTestPush = rcTestPush;

  // Expose a tiny debug surface so the smoke gate (and human operators)
  // can introspect state without scraping the DOM.
  window.RcPwa = {
    cacheVersion: RC_CACHE_VERSION,
    isIOS: isIOS,
    outboxSize: () => RcOutbox.size(),
  };
})();