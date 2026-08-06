// RoamCore profile store (profile-store.js)
//
// Plain-English: this is the tiny memory that remembers your choices
// (theme, layout, "last seen") so the app feels the same every time you
// open it. Stored only on your phone — never sent anywhere.

(function () {
  'use strict';

  var NS = 'rc.profile.';
  var DEFAULTS = Object.freeze({
    theme: 'auto',     // 'auto' | 'dark' | 'light'
    layout: 'comfort', // 'comfort' | 'compact' | 'power'
    lastSeen: 0
  });

  function safeRead(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function safeWrite(key, val) {
    try { localStorage.setItem(key, String(val)); return true; }
    catch (e) { return false; } // quota / private-mode — fail soft.
  }

  function get(key) {
    var fullKey = NS + key;
    var raw = safeRead(fullKey);
    if (raw === null) { return DEFAULTS[key]; }
    if (key === 'lastSeen') {
      var n = Number(raw);
      return isNaN(n) ? 0 : n;
    }
    return raw;
  }

  function set(key, val) {
    if (!(key in DEFAULTS)) { return false; }
    return safeWrite(NS + key, val);
  }

  function reset() {
    try {
      Object.keys(DEFAULTS).forEach(function (k) { localStorage.removeItem(NS + k); });
      return true;
    } catch (e) { return false; }
  }

  // Touch the last-seen stamp on every successful Hub fetch.
  function markHubFetched() {
    set('lastSeen', Date.now());
  }

  window.addEventListener('rc:hub-fetched', markHubFetched);

  // Public API. Tiny and idempotent.
  window.RCProfile = {
    get: get,
    set: set,
    reset: reset,
    keys: Object.keys(DEFAULTS)
  };
})();
