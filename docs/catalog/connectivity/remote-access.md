# Remote access

Check the van from anywhere: see sensor status, view cameras, get alerts, or (optionally) control systems.

## How to install

- For Tailscale (Path A, free): a Tailscale account.
- For Nabu Casa HA Cloud (Path C, paid): an active Nabu Casa
  subscription.
- For Cloudflare Tunnel (Path B, free): a Cloudflare account.

- Add this repo as a **HACS custom repository** (Category: *Integration*), then install **remote-access**.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

If you'd like a guided setup, see the Remote access setup wizard at
[`docs/setup/guided-remote-access.md`](../setup/guided-remote-access.md).
It walks you through Path A (Tailscale) or Path C (Nabu Casa HA
Cloud) step by step in plain English — Path B (Cloudflare) and Path
D (Wireguard) are coming soon in follow-up slices.

## What it does

- A Remote access tile that updates automatically.

## How it works

What RoamCore does behind the scenes.

## Useful links

Upstream docs and related references.
