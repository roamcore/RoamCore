# Remote access

Remote access (vendor-neutral remote-access umbrella for HA, covering Tailscale + Cloudflare Tunnel + Nabu Casa HA Cloud + Wireguard — operator picks ONE path).

## What you need

- Tailscale account (free for personal use)
- Cloudflare account for Cloudflare Tunnel (free tier)

## Install

- Add this repo as a **HACS custom repository** (Category: *Integration*), then install **remote-access**.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- Access enabled
- Access url
- Access active
- Access active path
- Access peer count
- Access last verified minutes ago
- Access hostname resolvable
- Access verify now
- Access path
