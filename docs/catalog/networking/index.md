# Networking

Starlink, mobile routers, DNS blocking, and remote access.

<div class="rc-card-grid">
  <a class="rc-card" href="starlink.md">
    <div class="rc-card__title">🛰 Starlink</div>
    <div class="rc-card__body">Self-hosted Starlink terminal — status, latency, WAN health tile.</div>
  </a>
  <a class="rc-card" href="starlink-sleep-timer.md">
    <div class="rc-card__title">🌙 Starlink sleep timer</div>
    <div class="rc-card__body">Put Starlink to sleep at night to save battery.</div>
  </a>
  <a class="rc-card" href="peplink.md">
    <div class="rc-card__title">📡 Peplink</div>
    <div class="rc-card__body">Multi-WAN Peplink router with cellular + Starlink failover.</div>
  </a>
  <a class="rc-card" href="teltonika.md">
    <div class="rc-card__title">📡 Teltonika</div>
    <div class="rc-card__body">Teltonika RUT cellular router status + WAN health tile.</div>
  </a>
  <a class="rc-card" href="dns-blocker.md">
    <div class="rc-card__title">🛡 DNS blocker</div>
    <div class="rc-card__body">Pi-hole or AdGuard Home — vendor-neutral DNS ad-blocking.</div>
  </a>
  <a class="rc-card" href="openwrt-controls.md">
    <div class="rc-card__title">🔧 OpenWrt controls</div>
    <div class="rc-card__body">WAN status + sensors from your OpenWrt router.</div>
  </a>
  <a class="rc-card" href="remote-access.md">
    <div class="rc-card__title">🔐 Remote access</div>
    <div class="rc-card__body">Reach your van from anywhere — Tailscale + reverse proxies.</div>
  </a>
</div>

## Multi-WAN recipes

Most vans carry two WANs: cellular (Peplink/Teltonika) + Starlink.
RoamCore's recipe layer treats both as interchangeable sources so the
dashboard shows "WAN is up" without caring which one is active.