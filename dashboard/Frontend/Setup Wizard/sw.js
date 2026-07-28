/*
 * RoamCore service worker — offline-first shell cache.
 *
 * Cache-first strategy for the static app shell so the PWA loads instantly
 * and works without network (mission-critical: a van owner should still
 * see the dashboard if LTE drops). Bump RC_CACHE_VERSION on every release
 * to invalidate all old clients.
 */
const RC_CACHE_VERSION = 'rc-shell-v1';
const RC_CACHE_NAME = `roamcore-${RC_CACHE_VERSION}`;

const RC_SHELL = [
  './',
  './index.html',
  './manifest.json',
  './icon-192.svg',
  './icon-512.svg',
];

self.addEventListener('install', (event) => {
  // Pre-cache the shell, then take over immediately so the user gets the
  // new SW on next launch instead of waiting for all tabs to close.
  event.waitUntil(
    caches.open(RC_CACHE_NAME).then((cache) => cache.addAll(RC_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  // Drop every cache that isn't the current version. Anything stale from
  // a previous RC_CACHE_VERSION gets nuked on activate.
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== RC_CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  // Only handle same-origin GETs; let the browser do its thing for cross-origin.
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Cache-first with a network fallback that populates the cache.
  // Navigation requests fall back to the cached index.html so deep links work offline.
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req).then((res) => {
        // Only cache successful basic responses; skip opaque/cors error pages.
        if (res && res.status === 200 && res.type === 'basic') {
          const clone = res.clone();
          caches.open(RC_CACHE_NAME).then((cache) => cache.put(req, clone));
        }
        return res;
      }).catch(() => caches.match('./index.html'));
    })
  );
});