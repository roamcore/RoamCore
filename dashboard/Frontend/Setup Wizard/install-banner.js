// RoamCore install banner (install-banner.js)
//
// Plain-English: this is the small "Add RoamCore to your home screen"
// banner that appears once on Android/Chrome. iOS shows a tiny hint
// instead. The banner never shows twice if you've already dismissed it.

(function () {
  'use strict';

  var DISMISS_KEY = 'rc.installBanner.dismissed';

  function safeRead(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function safeWrite(key, val) {
    try { localStorage.setItem(key, val); } catch (e) {}
  }

  function isStandalone() {
    try {
      return window.matchMedia('(display-mode: standalone)').matches ||
        window.navigator.standalone === true;
    } catch (e) { return false; }
  }

  function isIOS() {
    return /iphone|ipad|ipod/i.test(window.navigator.userAgent || '');
  }

  function buildBanner(promptEvent) {
    var banner = document.createElement('div');
    banner.id = 'rc-install-banner';
    banner.setAttribute('role', 'region');
    banner.setAttribute('aria-label', 'Install RoamCore');
    banner.style.cssText = [
      'position:fixed',
      'left:12px',
      'right:12px',
      'bottom:14px',
      'max-width:560px',
      'margin:0 auto',
      'background:#0B0F16',
      'color:rgba(255,255,255,0.92)',
      'border:1px solid rgba(255,255,255,0.10)',
      'border-radius:14px',
      'padding:12px 14px',
      'display:flex',
      'align-items:center',
      'gap:10px',
      'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif',
      'font-size:14px',
      'box-shadow:0 12px 36px rgba(0,0,0,0.45)',
      'z-index:1000'
    ].join(';');

    var text = document.createElement('div');
    text.style.cssText = 'flex:1;line-height:1.35';
    text.textContent = 'Add RoamCore to your home screen so it opens with one tap, even offline.';

    var installBtn = document.createElement('button');
    installBtn.type = 'button';
    installBtn.textContent = 'Install';
    installBtn.style.cssText = [
      'background:linear-gradient(135deg,#7CFFB2,#5BE3FF)',
      'color:#070A0F',
      'border:none',
      'border-radius:10px',
      'padding:8px 14px',
      'font-weight:700',
      'font-size:13px',
      'cursor:pointer',
      '-webkit-tap-highlight-color:transparent'
    ].join(';');

    var dismissBtn = document.createElement('button');
    dismissBtn.type = 'button';
    dismissBtn.setAttribute('aria-label', 'Dismiss install banner');
    dismissBtn.textContent = '×';
    dismissBtn.style.cssText = [
      'background:transparent',
      'color:rgba(255,255,255,0.65)',
      'border:none',
      'font-size:22px',
      'line-height:1',
      'padding:4px 8px',
      'cursor:pointer'
    ].join(';');

    function dismiss() {
      safeWrite(DISMISS_KEY, '1');
      if (banner.parentNode) { banner.parentNode.removeChild(banner); }
    }

    installBtn.addEventListener('click', function () {
      if (!promptEvent) { dismiss(); return; }
      promptEvent.prompt();
      promptEvent.userChoice.then(function () { dismiss(); }, function () { dismiss(); });
    });
    dismissBtn.addEventListener('click', dismiss);

    banner.appendChild(text);
    banner.appendChild(installBtn);
    banner.appendChild(dismissBtn);
    return banner;
  }

  function buildIOSHint() {
    var hint = document.createElement('div');
    hint.id = 'rc-ios-hint';
    hint.style.cssText = [
      'position:fixed',
      'left:12px',
      'right:12px',
      'bottom:14px',
      'max-width:560px',
      'margin:0 auto',
      'background:#0B0F16',
      'color:rgba(255,255,255,0.92)',
      'border:1px solid rgba(255,255,255,0.10)',
      'border-radius:14px',
      'padding:12px 14px',
      'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif',
      'font-size:14px',
      'z-index:1000'
    ].join(';');
    hint.textContent = 'Tap the Share button, then “Add to Home Screen” to install RoamCore.';
    return hint;
  }

  function maybeShow() {
    if (isStandalone()) { return; }
    if (safeRead(DISMISS_KEY) === '1') { return; }

    // Android / Chrome path: beforeinstallprompt fires when the app is
    // installable. iOS doesn't fire this event — show a one-time hint.
    window.addEventListener('beforeinstallprompt', function (e) {
      e.preventDefault();
      if (safeRead(DISMISS_KEY) === '1') { return; }
      if (!document.getElementById('rc-install-banner')) {
        document.body.appendChild(buildBanner(e));
      }
    });

    if (isIOS() && safeRead(DISMISS_KEY) !== '1') {
      // Only show iOS hint once per page-load.
      if (!document.getElementById('rc-ios-hint')) {
        document.body.appendChild(buildIOSHint());
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', maybeShow);
  } else {
    maybeShow();
  }
})();
