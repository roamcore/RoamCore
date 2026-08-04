# Time

> **SUPERSEDED — Wave 3 #55 (2026-08-02).** This legacy tier-c placeholder spec has been promoted to a tier-c recipe connection at [`connections/time-atomic/`](../../../connections/time-atomic/). The new connection ships a vendor-neutral NTP-disciplined atomic-time recipe over the upstream chrony / systemd-timesyncd / HA core `time_date` integration + GPS-disciplined NTP + GPS-from-Traccar + GPS-from-HA Companion + GPS-from-network-location + browser NTP fallback. The legacy tier-c content below is preserved for historical context only — do NOT wire a new install from this doc; use the recipe in the connection folder.

**Replaced by:** [`connections/time-atomic/`](../../../connections/time-atomic/)

**Recipe:** [`connections/time-atomic/docs/recipe.md`](../../../connections/time-atomic/docs/recipe.md)

---

Keep HA's clock accurate even when offline (in a van with intermittent connectivity).

## What you need

- Nothing extra — uses what's already in the van.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature time-atomic`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- A Time tile that updates automatically.
