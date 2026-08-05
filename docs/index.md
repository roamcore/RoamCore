# RoamCore

RoamCore connects the things in your van — power, water, internet, sensors,
locks — to Home Assistant, so you have one dashboard instead of ten apps.

## Pick what you want to add

Browse the [Catalog](catalog/) to see what RoamCore can connect to — every
entry is a real integration you can install and use today. The catalog is
grouped by what the thing does for you in the van: Water, Comfort,
Connectivity, Homelab, Safety, Security, and more. No jargon, no
"advanced modes", no up-sells.

<div class="rc-grid">
  <a class="rc-card" href="catalog/">
    <div class="rc-card-title">Browse the Catalog</div>
    <div class="rc-card-sub">Everything RoamCore connects to.</div>
  </a>
  <a class="rc-card" href="howto/homeassistant-installer/">
    <div class="rc-card-title">Install RoamCore</div>
    <div class="rc-card-sub">One-line installer.</div>
  </a>
  <a class="rc-card" href="guides/troubleshooting/">
    <div class="rc-card-title">Troubleshooting</div>
    <div class="rc-card-sub">If something doesn't work, start here.</div>
  </a>
</div>

---

## The part most people don't expect

Once you've connected a few things, RoamCore includes an optional agent
([OpenClaw](https://github.com/openclaw/openclaw)) that you can ask
questions in plain English:

- *"Is the water tank low and we're not plugged in?"*
- *"Warm up the bed before I get back."*
- *"Why did the inverter switch off at 3am?"*
- *"What changed since I last drove?"*

The agent reads the same state Home Assistant sees, so the answer is
based on what's actually happening in the van — not a script. It's
optional. Everything RoamCore connects works without it. But it's the
part we think changes the experience from "dashboard you have to read"
to "thing you can ask", and the part that gets the most attention when
people see a working build.

If you want to try it: [Install OpenClaw →](https://github.com/openclaw/openclaw)
or read the [JSON API reference](reference/openclaw-json-api.md).