# How RoamCore knows which device is which

> **One sentence:** This is the rule book RoamCore uses to recognise what each device in your van is telling it, so the same dashboard card always means the same thing no matter which brand of device you have.

This page is for anyone who wants to understand *how* RoamCore decides that a battery sensor from one brand and a battery sensor from another brand are both "the battery", and what happens when a brand new sensor shows up that RoamCore has never seen before.

If you only want to install devices and see them on your dashboard, the connection wizard does this for you — you don't need to read this page. If you want to know why a Victron battery sensor and a Renogy battery sensor both show up in the same `Battery` card, or what RoamCore does with a sensor it doesn't recognise yet, keep reading.

---

## §1 What it does

RoamCore reads every device in your van and figures out which "box on the dashboard" each device is telling it about. It uses three layers of recognition, in this order:

| Layer | What it means | How sure RoamCore is |
|---|---|---|
| **Exact rule** | "If a sensor is named exactly this, it is exactly that." | Very sure. |
| **Schema example** | "If a sensor is named like the ones RoamCore already knows about, it is that." | Quite sure. |
| **Fuzzy hint** | "If a sensor has the word `battery` in its name, it's probably about the battery." | Not very sure — RoamCore shows a small "low confidence" note so you know to check. |

The result is a **canonical map**: a simple list that says "the Renogy battery sensor is the same battery as the Victron battery sensor, which is the same battery as any other brand". One box on the dashboard, one source of truth, no matter how many devices you have.

If RoamCore cannot recognise a sensor at all, it goes into an *Advanced mode* panel rather than onto the main dashboard. The novice dashboard only ever shows devices RoamCore is confident about.

---

## §2 What you see

You don't see the mapping layer directly. What you see is the **result** of it working: the dashboard always shows the same card for the same thing.

- **One battery card, no matter which brand.** Whether you have a Victron SmartShunt, a Renogy battery monitor, or a generic USB battery sensor, the dashboard shows a single `Battery` card with the percentage full. You never have to remember "is the battery on the left or the right today".
- **Cards appear under stable names.** The card is always called something like `Battery`, `Solar`, `Lights`, `Water` — never `vt_battery_soc_percent` or `renogy_battery_indicator`. The names behind the scenes can change as you swap brands; the names on the dashboard never do.
- **A small note when RoamCore is unsure.** If a sensor only matched the "fuzzy hint" layer (because it has the word `battery` in its name but RoamCore has never seen that exact sensor before), the dashboard shows a small "low confidence" note on that card so you know to check the wiring. Once you confirm the sensor is wired correctly, RoamCore remembers it and the note goes away.

You also see a count in the setup wizard: *"12 devices recognised, 2 need your attention"*. The 2 are the ones RoamCore couldn't confidently map; the wizard walks you through confirming them.

---

## §3 What you do

For the typical case, you don't do anything. The mapping layer runs on its own when RoamCore starts up.

There are three situations where you might want to do something:

1. **You added a brand new device.** Plug it in. RoamCore scans it, recognises it if there's a matching rule, and adds the right card to your dashboard. If RoamCore doesn't recognise it, you see it in the "needs your attention" list in the setup wizard — click on it, confirm what it's for (battery, solar, water, …), and RoamCore adds the rule automatically. From then on, that brand is recognised forever.
2. **You swapped a device for a different brand.** Unplug the old one, plug in the new one. RoamCore re-scans, finds the new device, and (because the dashboard reads the canonical name, not the brand name) the dashboard card stays exactly where it was. You don't have to update any settings.
3. **You want to see what RoamCore has recognised.** Open the Advanced panel in the dashboard. You'll see every device, the rule that matched it, and the confidence level. This is the only place you'll ever see the internal names; the main dashboard never shows them.

If you're a developer or a tinkerer and you want to add your own rules, the Advanced panel also has a "mapping rules" editor. The rules are simple — "this sensor name is exactly that thing on the dashboard" — and the editor validates them as you type so you can't accidentally break the naming rules.

---

## §4 What to do if it goes wrong

**A device doesn't appear on the dashboard at all.**
First, check the setup wizard's "needs your attention" list — if it's there, click on it and confirm what the device is. Second, open the device's settings in Home Assistant's Developer Tools and look at the raw sensor names. If you see names like `sensor.vt_battery_soc_percent`, the vendor layer is working but the rule isn't in place yet — RoamCore will offer to add it automatically. If the names are completely different (e.g. `sensor.foobar_xyz`), the device isn't supported yet and you should file an issue with the brand and model.

**A device shows up twice on the dashboard.**
This means RoamCore found two sensors pointing at the same thing (for example, two battery sensors reporting at the same time). Open the Advanced panel, find both copies, and disable the one you don't want. RoamCore will remember your choice.

**A device shows up but with a "low confidence" note.**
RoamCore wasn't 100% sure which box to put the device in. It made its best guess (based on the word in the sensor name) and flagged it. Open the device in the setup wizard, confirm what it's actually for, and RoamCore will turn the fuzzy guess into a permanent rule. The "low confidence" note then disappears.

**You renamed a device in Home Assistant.**
Don't. Renaming a device outside RoamCore breaks the mapping layer's ability to recognise it. If you want a friendlier name, do it through RoamCore's Advanced panel — the friendly name goes on the dashboard card, the internal name stays exactly as the brand published it.

**The setup wizard can't find any of your devices.**
Check that your devices are powered on and connected to your van's network. RoamCore only sees devices that are reachable. If a device is on but RoamCore still can't see it, check the device's own app — some devices need a specific "remote access" or "local network" toggle enabled before they broadcast their readings.

---

## §5 Useful links

- **The canonical vehicle model** — the list of every "box" on the dashboard (battery, solar, lights, water, position, network) and what each one means. `docs/reference/rc-vehicle-model.md`.
- **Entity naming rules** — the technical rule book for how every name on the dashboard is built. `docs/reference/rc-entity-naming.md`.
- **Connection states** — what the colours and labels on the dashboard tiles mean (online / offline / needs attention). `docs/reference/rc-connection-states.md`.
- **Troubleshooting guide** — the larger playbook when something in RoamCore isn't behaving. `docs/guides/troubleshooting.md`.
- **How to read the mapping layer's output** — if you're a developer or tinkerer, this is the deeper "for developers" page that explains the rule schema. It's not on the public docs site on purpose — ask the RoamCore community if you need it.

---

## Appendix: words used in this page

RoamCore tries to use plain English in everything you read. When you see a word here that you want translated into the more technical RoamCore word, this table is for you.

| What this page says | What a developer would say |
|---|---|
| Box on the dashboard | Canonical capability id (e.g. `rc_power_battery_soc`) |
| The device RoamCore sees | Vendor entity id (e.g. `sensor.vt_battery_soc_percent`) |
| Rule book | Mapping rules (the JSON file at `connections/_schema/capability_mapping_rules.json`) |
| "Needs your attention" list | Unmapped entities (returned by `unmapped_entities()`) |
| "Low confidence" note | Fuzzy suffix match with confidence < 0.7 |
| Setup wizard | Connection / onboarding flow |
| Advanced panel | The "Advanced mode" toggle + its drill-down |
| Brand new device | Unrecognised vendor entity (no rule, no schema example, no fuzzy hint) |