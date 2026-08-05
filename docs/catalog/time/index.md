# Time

Atomic time and timezone handling so the van's clock stays accurate offline.

<!-- RC_FEATURE_LIST_START -->

## Features

<div class="rc-feature-list">
  <a class="rc-feature" href="timezone-geolocator/" data-tier="c"><div class="rc-feature-left"><div class="rc-feature-title">Time zone auto-detection (GeoLocator)</div><div class="rc-feature-sub">RoamCore includes notes for using GeoLocator to keep time zone correct based on location.</div></div><div class="rc-feature-right"><span class="rc-tier c" title="3rd party">C</span></div></a>
  <a class="rc-feature" href="atomic-time/"><div class="rc-feature-left"><div class="rc-feature-title">Time (atomic) — NTP-synchronized time with offline-resilience</div><div class="rc-feature-sub">RoamCore includes notes for keeping HA's clock accurate even when offline (in a van with intermittent connectivity) via NTP + GPS + RTC fallback paths.</div></div></a>
</div>

<!-- RC_FEATURE_LIST_END -->
