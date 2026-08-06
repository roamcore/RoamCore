# Cloudflare Tunnel — user guide (IKEA 5-step)

<!-- Wave 9 #122.b — Phase 6 Cloudflare Tunnel (Path B). User-facing IKEA 5-step doc. -->

## What this is

Use **Cloudflare Tunnel** to reach your Hub from anywhere — free, and
you don't need a Tailscale account. The wizard opens an outbound tunnel
from your Hub to Cloudflare's edge, then you reach your Hub via a
hostname you control (for example `my-van.example.com`). Cloudflare
Tunnel is the right pick if you already own a domain on Cloudflare and
don't want to manage a Tailscale tailnet.

If you don't have a domain on Cloudflare, **Tailscale** (Path A) is the
easier choice — pick Tailscale in the wizard and skip this guide.

## What you see

The same RoamCore dashboard you already use at home, opened via your own
hostname instead of a Tailscale IP. From any browser, type
`https://my-van.example.com` and you'll land on the Hub's login page —
no app, no VPN toggle, no inbound port open on your van's firewall.
Cloudflare's edge handles the HTTPS termination + DDoS protection; your
Hub only talks outbound to Cloudflare.

The Hub's "Remote access" dashboard tile flips from
**Off** to **On**, the URL tile shows your hostname, and the
"is remote access active?" tile turns green once the tunnel is up.

## What you do

Three steps in the wizard:

1. **Open the wizard.** On the Hub, go to **Settings → RoamCore setup
   wizard → Remote access**. Pick **Cloudflare Tunnel** from the
   remote-access path list.

2. **Paste your tunnel token.** Cloudflare gives you a tunnel token when
   you create a tunnel in the Cloudflare dashboard
   (Zero Trust → Networks → Tunnels → Create a tunnel →
   Cloudflared → copy the token). Paste that token into the wizard's
   "Your tunnel token from Cloudflare" field. The wizard treats it as a
   password (you'll see dots, not the raw text) — it never logs the
   token, never displays it back to you, and never commits it to your
   Hub's config.

3. **Pick a hostname you control.** Enter the hostname you want to use
   to reach your Hub, for example `my-van.example.com`. That hostname
   must already point at Cloudflare's nameservers — Cloudflare manages
   the DNS for your domain. Click **Connect**. The wizard calls the
   Cloudflare Tunnel daemon on your Hub, waits up to 30 seconds for it
   to come up, and flips the "Remote access" tile to **On** when the
   tunnel is reachable from the edge.

## What to do if it goes wrong

Five common things to check, in order:

1. **"Cloudflare rejected the tunnel token."** Open your Cloudflare
   dashboard, go to **Zero Trust → Networks → Tunnels**, and confirm
   the tunnel exists. Copy the token again from the tunnel's
   configuration page — paste it into the wizard. Tokens can be
   revoked by Cloudflare if you rotate them; the wizard can't tell the
   difference between a typo and a revocation, so always paste the
   freshest token.

2. **"We couldn't reach Cloudflare."** Check your internet connection.
   Cloudflare Tunnel is outbound-only — your Hub opens a connection
   to Cloudflare's edge over HTTPS port 7844. If you're on a
   campground Wi-Fi that blocks outbound HTTPS to non-standard ports,
   Cloudflare Tunnel won't work on that network. Try your phone's
   hotspot or a different Wi-Fi.

3. **"The hostname needs to be on a domain you manage in Cloudflare."**
   The hostname you picked (for example `my-van.example.com`) must
   belong to a domain that's added to your Cloudflare account and
   whose nameservers point at Cloudflare. If you have a domain on a
   different registrar, transfer the DNS to Cloudflare first
   (Cloudflare's free plan includes DNS hosting).

4. **The URL loads but the Hub login page never appears.** Open the
   Hub's dashboard at home (on your LAN), go to **Settings → Add-ons
   → Cloudflared** (or **Settings → Devices & Services →
   Cloudflare**), confirm the add-on or integration is started, and
   check that the tunnel token matches the one in the wizard.

5. **The Hub's "is remote access active?" tile is red even though the
   URL loads.** The wizard auto-verifies the tunnel every 15 minutes —
   if the tile is red, give it a few minutes, or press **Verify now**
   on the dashboard. If the tile stays red for over an hour, check
   the four items above.

If none of those fix it, post the **Hub diagnostic bundle** (from
**Settings → RoamCore → Diagnostics → Export**) to the RoamCore
support channel — the bundle includes the tunnel's last-known status
without revealing your token or hostname.

## Useful links

- **Cloudflare dashboard (tunnels)** —
  <https://one.dash.cloudflare.com/?to=/:account/:zone/access/tunnels>
- **Cloudflare Tunnel docs (developers)** —
  <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/>
- **HACS Cloudflared add-on** —
  <https://github.com/hassio-addons/addon-cloudflared>
- **RoamCore Tailscale (Path A) — the recommended alternative if you
  don't already have a domain on Cloudflare** —
  [Tailscale user guide](tailscale.md)
- **RoamCore remote-access umbrella (the full recipe)** —
  `connections/remote-access/docs/recipe.md` (the §4 Path B section
  walks the operator through every wiring detail; this user guide is
  the IKEA summary)