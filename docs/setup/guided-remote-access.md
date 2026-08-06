# Checking your van from anywhere

This guide walks you through setting up a remote-access path so you
can check on your van from your phone, even when you're far away
from it. RoamCore supports four remote-access paths; pick the one
that fits your life.

- **Path A — Tailscale** (free mesh VPN, recommended for most
  operators). Full step-by-step in §3 below.
- **Path B — Cloudflare Tunnel** (free, no inbound ports). Coming
  soon.
- **Path C — Nabu Casa HA Cloud** (paid; for operators who
  already subscribe). Step-by-step in §6 below.
- **Path D — Wireguard** (self-hosted VPN for technical
  operators). Coming soon.

If you'd rather not set up remote access at all, pick **Skip**
from the wizard's path drop-down.

## 1. What this is

RoamCore's remote-access wizard replaces the technical setup with
three plain-English taps so a vanlifer can reach their dashboard
from anywhere. You pick a path, drop in the credentials the wizard
asks for, and wait for the dashboard to tell you it's done. The
wizard checks the path is reachable from your phone, surfaces an
honest banner if your subscription lapses (you don't have to dig
through error logs), and preserves anything you've already typed
if you have to retry.

**Path C — Nabu Casa HA Cloud** is the simplest choice if you
already pay for Nabu Casa. Nabu Casa is Home Assistant's official
cloud relay — Home Assistant takes care of the connection for
you. The wizard's three taps are: pick Nabu Casa, paste the email
on your Nabu Casa account, wait for the dashboard to confirm
the connection works.

## 2. What you see

When you open the **Remote access setup** card on your dashboard,
you'll see:

- One sentence at the top in plain English. It tells you what's
  happening right now. For example: "Ready to help you set up
  Tailscale." or "Testing your Tailscale connection..." or "Tailscale
  is set up. You're good to go."
- A small drop-down to pick which kind of remote access you want.
  The recommended one is Tailscale — pick that unless you have a
  reason not to.
- A box to paste your Tailscale auth key.
- A box to type your Tailscale hostname (the address your phone will
  use to reach the van — it usually ends in `.ts.net`).

That's it. You don't need to type any commands, edit any files, or
restart anything yourself.

## 3. What you do

Follow these five steps, in order. Stop when you're done — the
dashboard will tell you when each step is finished.

1. **Install the Tailscale add-on in Home Assistant.** Open Home
   Assistant on your phone or laptop, go to **Settings → Add-ons →
   Add-on store**, search for **Tailscale**, and install it. Wait
   until it says the add-on is running.
2. **Pick Tailscale.** On the Remote access setup card, make sure
   the drop-down says **Tailscale**. If it says something else,
   change it back to **Tailscale**.
3. **Paste your Tailscale auth key.** On the Tailscale website
   (tailscale.com), open your account settings, create a new auth
   key, and copy it. Paste it into the box on the Remote access
   setup card. The box hides what you type so no one looking over
   your shoulder can see it.
4. **Type your Tailscale hostname.** This is the address your
   phone will use to reach the van. It looks like
   `my-van.ts.net`. If you don't know it, sign in to Tailscale on
   any device — your hostname is listed at the top of the page.
5. **Wait for the dashboard to say it's done.** The sentence at the
   top will change from "Testing your Tailscale connection..." to
   "Tailscale is set up. You're good to go." That usually takes
   under a minute. When it does, open your phone's browser and try
   typing your `my-van.ts.net` address — your van's dashboard
   should appear.

If you ever want to skip remote access entirely (for example, you
only ever check your van from home Wi-Fi), pick **Skip** from the
drop-down and you're done.

## 4. What to do if it goes wrong

Four things can go sideways, and each one has a one-step fix.

- **"Install the Tailscale add-on, then paste your auth key."**
  This means the wizard can't see Tailscale yet. Go back to step 1
  and make sure the Tailscale add-on is installed AND running.
  Once it's running, the sentence will change on its own — you
  don't need to refresh anything.

- **"We couldn't reach Tailscale. Check your internet
  connection."** This means the wizard tried to talk to Tailscale
  and couldn't. Check that your van has internet right now (look
  for the Wi-Fi or LTE indicator on the dashboard). Once it's back
  online, the dashboard will retry by itself. Your auth key is
  still in the box — you don't need to type it again.

- **Your Nabu Casa subscription paused.** If you picked Path C,
  the wizard will tell you "Your Nabu Casa subscription is paused"
  if your subscription lapsed (e.g. your card expired). Log into
  home.nabu-casa.com to resume, then the dashboard will retry by
  itself. Your account email is still in the box — you don't need
  to type it again.

- **The hostname doesn't load on your phone.** Make sure you typed
  it exactly right, including the `.ts.net` at the end. If you
  used the wrong one, fix it in the box and the dashboard will
  retry on its own.

If none of those fix it, wait five minutes and try again — Tailscale
sometimes takes a moment to catch up after a fresh install. If it's
still stuck after that, the easiest fix is to remove the Tailscale
add-on, reinstall it, and walk through these five steps again from
the top. Your Tailscale account and hostname don't change, so you
won't lose anything.

## 5. Useful links

- Tailscale installation guide: https://tailscale.com/kb/1017/install/
- Home Assistant Tailscale integration:
  https://www.home-assistant.io/integrations/tailscale/
- Home Assistant Nabu Casa cloud integration:
  https://www.home-assistant.io/integrations/cloud/
- Nabu Casa account portal: https://home.nabu-casa.com/
- RoamCore remote access overview: see the **Connectivity → Remote
  access** page in the RoamCore documentation.

You can come back to this card any time to see where you are in the
setup, change your settings, or turn remote access off if you ever
want to.

## 6. How to set up Nabu Casa HA Cloud (Path C)

Pick this if you already pay for Nabu Casa HA Cloud — Home
Assistant's official cloud relay. It's the simplest path if you
already have a subscription; the wizard does the rest in three
plain-English taps.

### 6.1 What this is

Nabu Casa is a paid service from the Home Assistant team. When
you enable it in your van, Home Assistant takes care of the
remote connection for you — you don't have to install any extra
software, you don't have to set up a VPN, and you don't have to
open any ports on your van's network. Once it's set up, you can
open your RoamCore dashboard from your phone, your laptop, or
your house — and see the same screen you'd see sitting inside
the van.

### 6.2 What you see

When you pick **Nabu Casa HA Cloud** from the remote-access
wizard's drop-down, you'll see:

- One sentence at the top in plain English. It tells you
  what's happening right now. For example: "Do you already pay
  for Nabu Casa HA Cloud?" or "Testing your Nabu Casa
  connection..." or "Nabu Casa is set up. You're good to go."
- One question — "Do you already pay for Nabu Casa HA Cloud?"
  — which the dashboard answers for you once you've enabled
  remote access in Home Assistant.
- One box to paste the email on your Nabu Casa account. The box
  hides what you type so no one looking over your shoulder can
  see it.

That's it. You don't need to type any commands, edit any files,
or restart anything yourself.

### 6.3 What you do

Follow these five steps, in order. Stop when you're done — the
dashboard will tell you when each step is finished.

1. **Subscribe to Nabu Casa HA Cloud.** Open Home Assistant,
   go to **Settings → Home Assistant Cloud**, and follow the
   prompts to start a free trial or subscribe. Nabu Casa is a
   paid service (after the trial); you can manage your
   subscription anytime at home.nabu-casa.com.
2. **Pick Nabu Casa.** On the remote-access wizard card, make
   sure the drop-down says **Nabu Casa HA Cloud**. If it says
   something else, change it back.
3. **Turn on remote access in the HA Cloud panel.** Still in
   **Settings → Home Assistant Cloud**, flip **Remote access**
   to ON. This is what tells Home Assistant to open the
   relay for you.
4. **Paste the email on your Nabu Casa account.** Use the same
   email you subscribed with. The wizard uses it only to confirm
   that you own the subscription; the box hides what you type.
5. **Wait for the dashboard to say it's done.** The sentence at
   the top will change from "Testing your Nabu Casa
   connection..." to "Nabu Casa is set up. You're good to go."
   That usually takes under a minute. When it does, open your
   phone's browser and try typing your Nabu Casa remote URL
   (you'll find it on **Settings → Home Assistant Cloud** under
   **Remote access**). Your van's dashboard should appear.

### 6.4 What to do if it goes wrong

Three things can go sideways with Nabu Casa, and each has a
one-step fix.

- **"Subscribe to Nabu Casa HA Cloud, then paste your account
  email."** This means the wizard can't talk to Nabu Casa yet.
  Go back to steps 1 + 2 + 3 and make sure your subscription
  is active AND **Remote access** is flipped ON in the HA
  Cloud panel. Once both are done, the sentence will change on
  its own — you don't need to refresh anything.

- **"We couldn't reach Nabu Casa. Check that your subscription
  is active."** This is the wizard's way of saying your Nabu
  Casa subscription has paused (most often: your card
  expired). Log into home.nabu-casa.com to resume — you can
  update your payment method and turn the subscription back on
  from there. Once it's active, the dashboard retries on its
  own. Your account email is still in the box — you don't
  need to type it again.

- **The Nabu Casa URL doesn't load on your phone.** Double-check
  that you've typed the URL exactly as shown in the HA Cloud
  panel. If you used the wrong one, fix it on your phone's
  browser bookmark or your HA Companion app settings.

If none of those fix it, wait five minutes and try again — the
Nabu Casa relay can take a moment to catch up after a fresh
subscription. If it's still stuck after that, log into
home.nabu-casa.com to confirm your subscription is active (not
paused), then walk through steps 2 + 3 + 4 again.

### 6.5 Useful links

- Nabu Casa: https://www.nabucasa.com/
- Nabu Casa account portal: https://home.nabu-casa.com/
- Home Assistant Cloud integration:
  https://www.home-assistant.io/integrations/cloud/
