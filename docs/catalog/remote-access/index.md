# Remote Access

> **SUPERSEDED — Wave 3 (2026-08-02).** This legacy tier-b placeholder spec has been promoted to a tier-b recipe connection at [`connections/remote-access/`](../../../connections/remote-access/). The new connection ships a vendor-neutral remote-access recipe covering Tailscale Path A + Cloudflare Tunnel Path B + Nabu Casa Path C + Wireguard Path D, six automations (auto-discovery + auth-gateway + kill-switch + audit-log + rate-limit + connection-failover), and the privacy + tier-a promotion outline. The legacy tier-b content below is preserved for historical context only — do NOT wire a new install from this doc; use the recipe in the connection folder.

**Replaced by:** [`connections/remote-access/`](../../../connections/remote-access/)

**Recipe:** [`connections/remote-access/docs/recipe.md`](../../../connections/remote-access/docs/recipe.md)

---

Reach your van from anywhere — Tailscale is the recommended path.

<div class="rc-card-grid">
  <a class="rc-card" href="tailscale.md">
    <div class="rc-card__title">🔐 Tailscale</div>
    <div class="rc-card__body">Secure mesh VPN — your phone becomes part of the van's LAN.</div>
  </a>
</div>

## How it works

Tailscale creates a private overlay network between your devices. Your
phone, your laptop, and the van all see each other as if they were on
the same Wi-Fi — no port-forwarding, no public IPs.