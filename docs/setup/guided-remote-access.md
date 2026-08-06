# Checking your van from anywhere

This guide walks you through setting up Tailscale so you can check
on your van from your phone, even when you're far away from it.

## 1. What this is

Tailscale is a small piece of software that lets your phone and your
van talk to each other safely, over the internet, without opening
any doors into your van's network. Once it's set up, you can open
your RoamCore dashboard from a coffee shop, a trailhead, or your
house — and see the same screen you'd see sitting inside the van.

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

Three things can go sideways, and each one has a one-step fix.

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
- RoamCore remote access overview: see the **Connectivity → Remote
  access** page in the RoamCore documentation.

You can come back to this card any time to see where you are in the
setup, change your settings, or turn remote access off if you ever
want to.
