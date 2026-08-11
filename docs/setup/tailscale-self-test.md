# Checking that your Tailscale tunnel works both ways

If you've already set up Tailscale so you can reach your van from anywhere, this guide shows you how to confirm — in one tap — that the tunnel is really working two ways (not just that the dashboard loads).

## 1. What this is

Tailscale is what lets you open your RoamCore dashboard from your phone when you're far away — coffee shops, trailheads, your house. Once it's set up, you should be able to open the dashboard from anywhere and see the same screen you'd see sitting inside the van. This page is a one-tap check that proves the tunnel really works in both directions: from your van out to your phone, and from your phone back to your van. A tunnel that's only working one way can still serve a cached dashboard page, which is why "the page loads" isn't the same thing as "I can reach my van." The check runs two probes — one going out from the van, one simulating your phone coming back — and tells you honestly whether both directions work.

## 2. What you see

When you open the **Tunnel self-test** card on your dashboard, you'll see one of these messages:

- **"Type your tunnel address to run a check."** — You haven't entered your tunnel address yet. Type it once below (it looks like `https://my-van.ts.net`).
- **"Ready to check your tunnel — tap Run now."** — Your tunnel address is entered, but the check hasn't run yet. Tap **Run now** to start it.
- **"Checking your tunnel — one moment..."** — The check is running. It takes about 30 seconds.
- **"Round-trip succeeded — your tunnel is two-way."** — Both directions work. You're good to reach your van from anywhere.
- **"Hub can't reach itself through the tunnel — check your Tailscale ACL."** — The van couldn't reach itself going out through the tunnel. Your Tailscale ACL rules may be blocking the address.
- **"Phone-side callback didn't arrive — check the tunnel URL."** — The van reached itself, but the simulated "phone-side" callback didn't make it back. The tunnel address you typed may be wrong.

You'll also see a **Run now** button and a box to type your tunnel address (it hides what you type so no one looking over your shoulder can see it). You can re-tap **Run now** any time to re-check — your tunnel address stays in the box.

## 3. What you do

Follow these three steps, in order. Stop when you're done.

1. **Find your tunnel address.** Sign in to Tailscale on any device — your tailnet hostname is listed at the top of the page. It usually looks like `my-van.ts.net`. The full address you type is `https://` followed by that hostname.
2. **Type your tunnel address into the box on the Tunnel self-test card.** The box hides what you type so no one looking over your shoulder can see it. Make sure you include `https://` at the start and the `.ts.net` at the end.
3. **Tap Run now.** Wait about 30 seconds. The message at the top of the card will change from "Checking your tunnel..." to one of the four end-state messages. If it says "Round-trip succeeded", you're good — open your phone's browser and try typing your tunnel address to see your dashboard.

You can re-tap **Run now** any time to re-check. Your tunnel address stays in the box, so you don't need to re-type it.

## 4. What to do if it goes wrong

Three things can go sideways, and each one has a plain-English fix.

- **"Hub can't reach itself through the tunnel — check your Tailscale ACL."** This means the van couldn't reach itself going out through the tunnel. The most common cause is a Tailscale ACL rule that blocks MagicDNS or your tailnet hostname. Open your Tailscale admin console, check the ACL page, and make sure the rule for your tailnet allows MagicDNS. If you're not sure what to change, leave the rule alone and try again in a few minutes — Tailscale sometimes takes a moment to apply changes.

- **"Phone-side callback didn't arrive — check the tunnel URL."** This means the van reached itself, but the simulated "phone-side" callback didn't make it back through the tunnel. The most common cause is a typo in the tunnel address you typed. Re-check the address: it should start with `https://` and end with `.ts.net`, with no extra path or trailing slash. If you've typed it right and it still fails, your tunnel may be partially down — restart the Tailscale add-on from the Home Assistant **Settings → Add-ons** page.

- **The check stays on "Checking your tunnel..." for more than a minute.** The dashboard will surface a notification saying "Your Tailscale tunnel can't be reached both ways." That's the dashboard telling you the check timed out. Tap **Run now** to try again — the dashboard will retry on its own with the same tunnel address.

If none of those fix it, the easiest reset is to restart the Tailscale add-on (open Home Assistant on your phone or laptop, go to **Settings → Add-ons**, find Tailscale, and tap **Restart**). Then tap **Run now** on the Tunnel self-test card to re-check. Your tunnel address stays in the box, so you don't need to re-type it.

## 5. Useful links

- [Checking your van from anywhere (Tailscale setup)](./guided-remote-access.md) — how to set up Tailscale for the first time, if you haven't yet.
- [Reaching your van from your phone on the same WiFi](./local-access-fallback.md) — what to do if your tunnel is down and you're near the van.
- [Tailscale admin console](https://login.tailscale.com/admin) — where you find your tailnet hostname and check ACL rules.
- [RoamCore Home Assistant setup](../setup.md) — the main setup walkthrough.

You can come back to the Tunnel self-test card any time to re-check your tunnel or to see whether your tunnel address is still set correctly.

---

## What you might hear us call it (operator → vanlifer)

Sometimes we use technical words. Here's what they mean in plain English.

| Operator calls it | You might call it |
| --- | --- |
| Self-test | A check that runs on its own to confirm something is working. |
| Round-trip | Going out and coming back. A round-trip means both directions work. |
| Outbound probe | A check that goes from your van out to your phone. |
| Inbound probe | A check that comes from your phone back to your van. |
| MagicDNS | The friendly hostname Tailscale gives your van (it ends in `.ts.net`). |
| ACL rules | The list of who's allowed to talk to whom on your tailnet. |
| Tunnel | The private connection between your van and your phone. |
| Tailscale | The piece of software that makes the tunnel work. |
| Two-way | Both directions — from your van to your phone, and from your phone to your van. |
| Persistent notification | A message that stays at the top of the dashboard until you dismiss it. |
| `input_button` | A button on your dashboard. |
| `input_text` | A text field on your dashboard. |
| Template sensor | A status reading that updates on its own. |
| Automation | A rule that runs on its own when something happens. |
