# Reaching your van from your phone on the same WiFi

If your Tailscale connection ever stops working, you can still open your RoamCore dashboard from your phone while your phone is on the same WiFi as the Hub — at `roamcore.local`, no IP needed.

## 1. What this is

Tailscale is the way you usually reach your van from far away — coffee shops, trailheads, your house. Sometimes though, Tailscale might be down (your account is paused, your phone's cellular signal is too weak for the VPN, the Hub's internet is offline). When that happens, this fallback makes sure you can still reach the dashboard from the Hub's own WiFi. You don't have to do anything to set it up — it's already running.

## 2. What you see

When you open the **Local access fallback** card on your dashboard, you'll see one of these three messages:

- **"Reachable at `roamcore.local` from your phone on this WiFi."** — The fallback is working. Use this address from any device on the Hub's WiFi.
- **"Reachable at `<ip>:8123` instead — open that in your browser."** — The fallback isn't resolving the friendly name right now, but you can use the IP directly.
- **"Local address fallback unavailable — make sure your phone is on the Hub's WiFi."** — The Hub can't answer on its own WiFi right now. Check that your phone is connected to the Hub's WiFi (not your cellular or your house WiFi).

You can also see a **Retest** button — tap it any time to re-check whether the fallback is working.

## 3. What you do

Follow these three steps, in order. Stop when you're done.

1. **Make sure your phone is on the Hub's WiFi.** Open your phone's WiFi settings and pick the network that your Hub is broadcasting (the name usually ends in `-RoamCore` or `-Hub`). If your phone stays on cellular or your house WiFi, `roamcore.local` won't resolve.
2. **Open `roamcore.local` in Safari (or your browser of choice).** Type it exactly like that — the word `roamcore`, then a dot, then the word `local`. The dashboard should load just like it would over Tailscale.
3. **Bookmark it for next time.** Tap the share button and pick **Add to Home Screen** so you have one-tap access next time you're near the van.

That's it. You don't need to type any commands, edit any files, or restart anything yourself.

## 4. What to do if it goes wrong

If `roamcore.local` doesn't open:

1. **Check that your phone is on the Hub's WiFi** (not cellular, not your house network). The friendly name `roamcore.local` only works while your phone is on the same WiFi as the Hub.
2. **Try the Hub's IP directly.** The Hub's screen shows its IP address — type `http://<that-ip>:8123` into your browser. Same dashboard, same bookmarks.
3. **Tap the Retest button** on the Local access fallback card. If the message changes from "unavailable" to one of the reachable messages, you're good.
4. **If neither name nor IP works**, your Hub's WiFi may be turned off. Restart the Hub by unplugging power for 10 seconds, then plugging it back in.

If you've tried all of the above and it still doesn't work, reach out through your normal support channel.

## 5. Useful links

- [Checking your van from anywhere (Tailscale setup)](./guided-remote-access.md) — how to set up Tailscale for when you're far from the van.
- [RoamCore Home Assistant setup](../setup.md) — the main setup walkthrough.
- [RoamCore on GitHub](https://github.com/RoamCore/RoamCore) — the project source.

---

## What you might hear us call it (operator → vanlifer)

Sometimes we use technical words. Here's what they mean in plain English:

| Operator calls it | You might call it |
| --- | --- |
| mDNS responder | The thing on the Hub that says "I'm here, my name is `roamcore`" to any phone on the same WiFi. |
| `roamcore.local` hostname | The friendly address you type into your browser instead of an IP. |
| `avahi` | The background service that does the above. You never need to know this — it's already running on the Hub. |
| `binary_sensor` | An on/off indicator on your dashboard. |
| Template sensor | What your dashboard shows you in plain English. |
| Automation | A rule that runs on its own (for example: "every 60 seconds, check whether the friendly name still works"). |
| `shell_command` | An action the Hub takes behind the scenes (for example: probing the WiFi to see if the friendly name resolves). |
| Tailscale fallback | The safety net this whole guide is about. |
| Local-only access | Reaching your van from the same WiFi, without going through the internet. |