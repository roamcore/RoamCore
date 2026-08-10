# RoamCore auto-generated dashboard

> **One sentence:** This is the rule book RoamCore uses to draw your dashboard from your devices — so the moment you plug a device in, the right card shows up in the right place, with the right name and the right picture, and you never have to touch a settings file.

This page is for anyone who wants to understand *what* the auto-generated dashboard is, *why* it exists, and *what happens behind the scenes* when a device gets added to RoamCore.

If you only want to plug a device in and see it on your dashboard, the connection wizard does this for you — you don't need to read this page. If you're curious, or you want to know why two different batteries both end up in the same battery card, keep reading.

---

## §1 What it does

The auto-generated dashboard is RoamCore's way of turning "you have a device" into "there's a card for it on your dashboard" — without you writing a single line of code or touching a settings file.

When you plug a device in, RoamCore automatically:

- **Picks the right card** for the device (a battery card, a light switch, a temperature reading, …).
- **Picks the right section** to put it in (Power, Lighting, Climate, Water, Position, Network — one of the six plain-English areas RoamCore recognises).
- **Picks the right name** for the card (the plain-English description, never the brand or the model number).
- **Picks the right picture** (an icon that matches what the device is, not who made it).
- **Picks the right behaviour** — readings update live, switches toggle on tap, buttons stay in the advanced area (because buttons are usually a power-user thing).

If a section has no devices mapped yet, it doesn't show up — so you never see an empty "Lighting" section if you don't have lights connected.

The dashboard is regenerated every time a device gets added or removed, so the screen always matches what's actually in the van.

---

## §2 What you see

The dashboard is organised into plain-English sections, one for each area of the van. Each section only appears if at least one device in that area is connected.

| Section | What it shows | Example card |
|---|---|---|
| **Power** | Batteries, solar, shore power, inverter | "State of charge of the leisure battery" — with a battery icon and a percentage. |
| **Lighting** | Interior and exterior lights | "On/off control for the interior cabin lights" — a switch you tap to toggle. |
| **Climate** | Indoor temperature, heater, AC | "Indoor cabin temperature" — with a thermometer icon and a °C reading. |
| **Water** | Fresh water level, water pump | "Fresh water tank level" — with a percentage and a water-tank icon. |
| **Position** | Where the van is right now | "Vehicle GPS latitude" — a number that updates as you drive. |
| **Network** | Whether the internet is working | "Does the van have any working internet" — yes / no, with a Wi-Fi icon. |

Every card has three things: a plain-English name at the top, a live reading in the middle, and a small icon on the left that matches what the device is. The brand never appears anywhere on the card.

If you only want the basics, you see six sections at most, and the screen is always clean. If you turn on the Advanced mode, you get extra details on each card and a few more diagnostics.

---

## §3 What you do

You don't do anything. That's the point.

When you plug a device in (a battery monitor, a solar controller, a USB temperature sensor — anything that talks to RoamCore), the connection wizard talks to the device, figures out what it is, picks the right card, picks the right section, and drops it on your dashboard. You never open a settings file, you never copy a code snippet, you never type anything.

Three things you might want to do, none of them required:

1. **Glance at the dashboard.** That's the whole job — if every section looks healthy, you can walk away.
2. **Tap a switch.** Lights, water pump, HVAC — anything that's a switch on the dashboard toggles when you tap it. Readings update on their own.
3. **Turn on the Advanced mode** (in Settings, under Display) if you want to see the technical details behind each card. Most vanlifers never need this.

If a device disappears from the dashboard, that almost always means the device went offline — refresh once, and if it's still missing, the device's own page will tell you what to check.

---

## §4 What to do if it goes wrong

**A device I just plugged in didn't show up on the dashboard.**
Open the device's page in the RoamCore catalogue. If the page says "Connected" but the card is missing, give it a minute — the dashboard regenerates every few seconds. If the page says "Needs attention" or "Offline", that's the issue to fix first.

**A whole section (Power, Lighting, …) is missing.**
That section only appears if at least one device in that area is connected. If you have no lights connected, the Lighting section is intentionally hidden — that's by design, not a bug. Plug a light in and the section appears.

**I see a card with the wrong name or wrong picture.**
The name comes from the device's plain-English description and the picture comes from the device's category — both are picked automatically. If a card looks wrong, the device's page is the place to file a note; the RoamCore team uses those notes to improve the auto-mapping.

**I turned on Advanced mode and now the cards look busy.**
That's expected — Advanced mode adds extra detail (last-updated time, raw identifiers, secondary metrics). Turn it off in Settings → Display if you want the clean view back.

**I see an error banner on a card instead of a reading.**
That means the device is reachable but the reading failed. The card's own page will tell you what to check (usually a loose wire or a settings reset on the device itself).

---

## §5 Useful links

- **[The canonical vehicle model](rc-vehicle-model.md)** — the shared vocabulary every RoamCore card uses.
- **[How RoamCore names things](rc-entity-naming.md)** — the rules behind the plain-English card names.
- **[Connection states](rc-connection-states.md)** — what the "Connected", "Needs attention", "Offline" chips mean.
- **[Troubleshooting guide](../guides/troubleshooting.md)** — if a card or device isn't behaving.

---

## Translation table

If you're used to reading RoamCore's technical docs and you want to know how the same ideas are written here, this is the cheat sheet.

| Technical term | What this page calls it |
|---|---|
| Entity | Device, sensor, reading |
| Capability | Thing you can ask about the van |
| Card | The box on the screen |
| Section | The plain-English area at the top of the screen (Power, Lighting, …) |
| Vendor-neutral | The card never mentions the brand |
| Mapping | The link between a device and its card |
| Lovelace | The dashboard layout system (we never mention it in user copy) |
| Settings file | What we mean when we say "never have to touch a settings file" |
| Advanced mode | The toggle in Settings that adds extra detail to each card |
