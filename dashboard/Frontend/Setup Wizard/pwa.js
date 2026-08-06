// RoamCore PWA glue (pwa.js)
//
// Plain-English: this is the part of the app that talks to your phone's
// "install" button, knows when you're online or offline, and tells the
// service worker when to wake up. Kept tiny so it loads instantly even
// on a weak LTE signal.

(function () {
  'use strict';

  var ONLINE_FLAG = 'rc.online';

  function setOnline(online) {
    try { document.documentElement.setAttribute('data-rc-online', online ? 'true' : 'false'); } catch (e) {}
    try { localStorage.setItem(ONLINE_FLAG, online ? '1' : '0'); } catch (e) {}
    try {
      var ev = new CustomEvent('rc:online-changed', { detail: { online: online } });
      window.dispatchEvent(ev);
    } catch (e) {}
  }

  // Service worker registration — idempotent across reloads.
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('./sw.js').then(function (reg) {
        // When a new SW is waiting, let the page opt into upgrading.
        function trackWaiting(r) {
          if (!r) { return; }
          r.addEventListener('updatefound', function () {
            var sw = r.installing;
            if (!sw) { return; }
            sw.addEventListener('statechange', function () {
              if (sw.state === 'installed' && navigator.serviceWorker.controller) {
                try {
                  var ev = new CustomEvent('rc:sw-updated');
                  window.dispatchEvent(ev);
                } catch (e) {}
              }
            });
          });
        }
        trackWaiting(reg);

        // Periodic update check: cheap + doesn't fetch when offline.
        try {
          setInterval(function () {
            if (navigator.onLine) { reg.update().catch(function () {}); }
          }, 60 * 60 * 1000);
        } catch (e) {}
      }).catch(function () {
        // Silent: SW registration is best-effort. The app still works
        // online without a SW; the user just won't see the offline shell.
      });
    });
  }

  // Online/offline detection — wires to the recovery pill in offline.html.
  function readInitial() {
    try { return localStorage.getItem(ONLINE_FLAG) === '1'; } catch (e) { return navigator.onLine; }
  }
  setOnline(readInitial());
  window.addEventListener('online', function () { setOnline(true); });
  window.addEventListener('offline', function () { setOnline(false); });

  // Last-seen stamp — written by the page whenever it successfully
  // fetches Hub data. The offline shell reads it and renders honestly.
  function markLastSeen() {
    try { localStorage.setItem('rc.lastSeen', String(Date.now())); } catch (e) {}
  }
  window.addEventListener('rc:hub-fetched', markLastSeen);
  window.addEventListener('load', markLastSeen);
})();
