# How RoamCore knows where each device belongs

> **One sentence:** RoamCore automatically organises whatever you plug in — battery, solar, water, network — without you telling it which is which.

This page is for anyone who wants to understand *how* a new device ends up in the right place on the RoamCore dashboard, and what to do if it doesn't.

If you only want to install a device and see it on your dashboard, the connection wizard does all of this for you. You don't need to read this page. If you're curious, or you want to know why a Victron SmartShunt and a Renogy battery monitor both show up in the same `Battery` tile, keep reading.

---

## §1 What this is

Every device in your van — Victron, Renogy, a generic USB temperature sensor, anything — has its own brand-specific way of talking. Without help, your dashboard would need one card per brand, and switching brands would mean rebuilding the dashboard. RoamCore solves this with a **shared vocabulary** of "things in a van" — battery, solar, water, network, position, lighting — and a smart layer that quietly translates whatever you plug in into that vocabulary.

You do nothing. RoamCore looks at the device, decides which box on the dashboard it belongs in, and puts it there.

---

## §2 What you see

When you open the RoamCore dashboard, you see one **tile** per thing in the van. The tile is labelled in plain English (Battery, Solar, Fresh Water, Internet, GPS) and shows you the current value.

When you plug in a new device, the right tile just *updates with the new value*. You don't have to drag anything, you don't have to edit a YAML, you don't have to pick from a dropdown. The tile was already there — now it's showing real data from the new device.

If a device doesn't fit any known tile, RoamCore doesn't drop it on the floor. It goes into a "things we haven't categorised yet" panel in Advanced mode and stays out of your way.

---

## §3 What you do

**Nothing.** This is automatic.

If you're the curious type and want to peek under the hood: there is a small list of rules that tell RoamCore "an entity that mentions battery + voltage is the leisure battery voltage." That list lives in the RoamCore repo (it's plain text — you can read it in your browser). You don't need to edit it, and RoamCore will never ask you to. It's there so that power users can suggest new mappings if a new device appears that RoamCore doesn't recognise yet.

---

## §4 What to do if it goes wrong

If a device shows up in the wrong tile (for example, your water pump is showing up under "Lighting"), or if a device doesn't show up at all:

1. Open the **About this tile** panel on the tile that's wrong. It tells you which rule RoamCore used to decide where the device belongs.
2. If the rule is obviously wrong (e.g. the rule says "anything with `pump` in the name is a light"), file an issue against the RoamCore repo with the entity name from the panel. RoamCore will add a better rule and the next update will fix it for everyone.
3. If the device doesn't show up at all, the rule list probably doesn't have an entry for it yet. File the same kind of issue with the entity name — RoamCore's maintainers will add a rule.

In either case the message is the same: **file an issue with the entity name, RoamCore will fix it in a future update.** You don't need to edit anything yourself.

---

## §5 Useful links

- **The canonical tile list** — the full vocabulary of "things in a van" that RoamCore knows about. It's plain English and lives in the RoamCore repo.
- **The naming convention** — explains why every tile is labelled the way it is (so the dashboard stays stable when you switch brands).
- **The connection wizard** — the setup flow that adds a new device. It runs the same smart layer automatically; you don't need to know any of this to use it.
