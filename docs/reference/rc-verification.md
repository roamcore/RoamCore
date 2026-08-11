# RoamCore post-install check

> **One sentence:** After RoamCore adds a device, it checks that the device is actually talking — not just that the card is on the screen — and tells you honestly in plain English if anything looks wrong, with one sentence about what to do next.

This page is for anyone who wants to understand what RoamCore checks in the background after you connect a device, and what the plain-English messages mean when something looks off.

If you only want to install a device and have it just work, you don't need to read this page. RoamCore runs the check for you and surfaces a one-line message on the tile only when something needs your attention.

---

## §1 What this is

Every device in your van — battery monitor, solar charger, water pump, GPS, anything — sends RoamCore a steady stream of small numbers (battery percentage, watts, degrees, position, …). RoamCore checks five things about those numbers, in this order, and only bothers you when one of them is wrong:

1. **The number makes sense.** A battery percentage of 150 isn't a thing; a GPS latitude of 999 isn't a place. If the number is outside the sensible range for what you're measuring, RoamCore tells you.
2. **The number is fresh.** If your battery hasn't sent anything in the last minute, RoamCore says so — because a stale number on the screen is worse than no number at all.
3. **The numbers don't jump illogically.** A battery that goes from 0% to 100% in one second isn't really doing that — the cable is loose or the sensor is confused. RoamCore flags impossible jumps.
4. **The device came back after the last restart.** If your device lost power, rebooted, and never reconnected, RoamCore says so — so you don't trust a stale number from a device that's actually offline.
5. **The right device is plugged into the right tile.** If your battery tile is somehow listening to a random Wi-Fi device, RoamCore notices the mismatch and tells you.

When all five pass, the tile stays calm and you see nothing extra. When one fails, the tile shows a plain-English sentence and a one-sentence hint about what to do.

---

## §2 What you see

When everything is fine, you see **nothing new** — the tile behaves exactly as it did before, showing the same number, the same icon, the same colour.

When something is wrong, the tile shows a short message in plain English, in this shape:

> **Your device didn't come back after the last restart.**
>
> Power-cycle the device, then check the cable or wireless link — it should reconnect on its own.

A few examples of what you might see, in plain English:

- "Your battery sent 150%, which is outside the expected range of 0 to 100%." → "Check that the right device is mapped to this tile — it looks like the wrong sensor is plugged in."
- "No fresh data in the last 60 seconds — your device might have stopped sending." → "Check the device — make sure it has power and the cable or wireless link is connected."
- "Your device sent an impossible jump in values — looks like bad data." → "Check the device — it may need a power cycle, or the wiring may be picking up electrical noise."

Each message is **one sentence** with **one next step**. No jargon, no error codes, no log dumps.

---

## §3 What you do

**Nothing, in the happy case.** If the tile looks normal, the check passed.

When you see a plain-English message on a tile, the recovery hint tells you exactly what to try, in order from cheapest to most invasive:

1. **Read the message.** It tells you which check failed (range, freshness, jump, restart, mismatch).
2. **Try the one-line fix in the message.** Usually it's "check the cable" or "power-cycle the device" — both safe, both take a minute.
3. **Wait a minute or two.** RoamCore re-checks automatically. If the issue clears, the message disappears and the tile goes back to normal.
4. **If the message stays**, the next step is to physically inspect the device — power, cabling, wireless link. The recovery hint names which one to look at.
5. **If nothing helps**, the recovery hint is your cue to contact support. The message tells the support team which check failed, which is the most useful piece of information they need.

---

## §4 What to do if it goes wrong

**The message says "no fresh data in the last 60 seconds".**
The device stopped sending. Check that it has power (the LED is on, the fuse isn't blown) and that the cable or wireless link is connected. After you fix it, wait a minute — the message will disappear on its own.

**The message says "outside the expected range".**
The number coming in doesn't make sense for what this tile is supposed to measure. Most often this means the wrong sensor is mapped to this tile — a temperature sensor is being read as a battery percentage, or a 12 V supply is being read as a solar wattage. Open the device mapping and double-check which sensor is plugged into which tile.

**The message says "impossible jump in values".**
The device sent two wildly different numbers in a very short time (a battery going from 0% to 100% in a second, for example). This usually points to a wiring problem — a loose connector or electrical noise. Power-cycle the device, check the connectors, and watch for a repeat.

**The message says "your device didn't come back after the last restart".**
The device restarted at some point (lost power, was rebooted, firmware update) and hasn't sent anything since. Power-cycle the device, then check the cable or wireless link — most devices reconnect on their own once the link is back.

**The message says "your device id doesn't look like the kind of device this should be".**
The wrong device is plugged into this tile. Open the device mapping and pick the right sensor — RoamCore knows what kind of device should be on each tile.

**The message won't go away after you've fixed the underlying problem.**
Wait 60 seconds — the check runs continuously, and the message clears as soon as the next check passes. If it stays for more than a few minutes, the fix didn't take. Re-read the message and try the next step.

---

## §5 Useful links

- The canonical vehicle model — what each tile means and how devices are categorised: see the [canonical vehicle model page](rc-vehicle-model.md).
- The RoamCore entity naming convention — how tile ids are kept stable across vendors: see the [entity naming page](rc-entity-naming.md).
- Connection states — what each state of a connected device means: see the [connection states page](rc-connection-states.md).
- Troubleshooting guides — broader help when a tile just won't behave: see the [troubleshooting guide](../guides/troubleshooting.md).

### Operator → vanlifer cheat sheet

If you read a RoamCore log or a developer page and see a word that isn't on this list, it's almost certainly something we should be hiding from you — please file an issue.

| You see this in code or a log | We mean this in the van |
|---|---|
| device, sensor, reading | the thing RoamCore is measuring |
| connection, link | how RoamCore talks to your device |
| auto-find, auto-discovery | RoamCore noticed your device on its own |
| the app store for Home Assistant | HACS (developer-only term) |
| card, panel, screen | the box on the dashboard |
| rule | an automation that runs on its own |
| action | a script that does a thing |
| preset | a saved scene |
| trigger | a service call that starts something |
| auto-discovery on your WiFi | mDNS / Zeroconf (developer-only) |
| the messaging system | MQTT (developer-only) |
| secure remote access | Tailscale (developer-only) |
| backup connection | a failover link (developer-only) |
| access code, password | a token / API key (developer-only) |
