// RoamCore service worker (sw.js)
//
// Plain-English: this is the part of the app that lets it work without
// internet. It remembers the parts of the app you've already opened so
// you can see them again even if your van is out of LTE range, and it
// shows you an honest "couldn't reach your van" page instead of a blank
// screen when the Hub is unreachable.

/* global self, caches */

(function () {
  'use strict';

  var CACHE_VERSION = 'rc-shell-v3';
  var SHELL_FILES = [
    './',
    './index.html',
    './offline.html',
    './manifest.json',
    './icon-192.svg',
    './icon-512.svg',
    './pwa.js',
    './install-banner.js',
    './profile-store.js'
  ];

  self.addEventListener('install', function (event) {
    event.waitUntil(
      caches.open(CACHE_VERSION).then(function (cache) {
        return cache.addAll(SHELL_FILES).catch(function () {
          // Best-effort: don't break install if one asset 404s in dev.
          return Promise.resolve();
        });
      }).then(function () { return self.skipWaiting(); })
    );
  });

  self.addEventListener('activate', function (event) {
    event.waitUntil(
      caches.keys().then(function (keys) {
        return Promise.all(keys.map(function (key) {
          if (key !== CACHE_VERSION) { return caches.delete(key); }
          return null;
        }));
      }).then(function () { return self.clients.claim(); })
    );
  });

  // Allow the page to tell us to activate a waiting SW immediately.
  self.addEventListener('message', function (event) {
    if (event && event.data && event.data.type === 'SKIP_WAITING') {
      self.skipWaiting();
    }
  });

  self.addEventListener('fetch', function (event) {
    var req = event.request;
    if (req.method !== 'GET') { return; }

    var url;
    try { url = new URL(req.url); } catch (e) { return; }
    if (url.origin !== self.location.origin) { return; }

    // Navigation requests: network-first, fall back to cached shell,
    // fall back to offline.html so the user sees something honest.
    if (req.mode === 'navigate') {
      event.respondWith(
        fetch(req).then(function (resp) {
          // Refresh the shell cache with the fresh index when online.
          if (resp && resp.ok) {
            var copy = resp.clone();
            caches.open(CACHE_VERSION).then(function (cache) {
              cache.put(req, copy).catch(function () {});
            });
          }
          return resp;
        }).catch(function () {
          return caches.match(req).then(function (cached) {
            return cached || caches.match('./offline.html');
          });
        })
      );
      return;
    }

    // Static assets: cache-first, fall back to network, fall back to offline.
    event.respondWith(
      caches.match(req).then(function (cached) {
        if (cached) { return cached; }
        return fetch(req).then(function (resp) {
          if (resp && resp.ok) {
            var copy = resp.clone();
            caches.open(CACHE_VERSION).then(function (cache) {
              cache.put(req, copy).catch(function () {});
            });
          }
          return resp;
        }).catch(function () {
          return caches.match('./offline.html');
        });
      })
    );
  });
})();
