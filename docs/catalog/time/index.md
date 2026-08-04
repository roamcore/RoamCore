# Time

Atomic time sync and automatic timezone via GPS.

<div class="rc-card-grid">
  <a class="rc-card" href="atomic-time.md">
    <div class="rc-card__title">🕒 Atomic time</div>
    <div class="rc-card__body">NTP-disciplined atomic time — your van is never on the wrong minute.</div>
  </a>
  <a class="rc-card" href="timezone-geolocator.md">
    <div class="rc-card__title">🌍 Timezone geolocator</div>
    <div class="rc-card__body">Auto-detect the local timezone from GPS so schedules fire at the right wall-clock.</div>
  </a>
</div>

## Why this matters in a van

A van crosses time zones regularly. Without timezone geolocation, a
6 AM "wake-up heat" automation fires at 6 AM UTC, which is wrong 8
months of the year. The geolocator fixes that automatically.