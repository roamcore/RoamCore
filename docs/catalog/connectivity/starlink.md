# Starlink

Starlink is your van's **long-range mobile internet** — a small dish on the roof that talks to satellites and gives you Wi-Fi almost anywhere. RoamCore can put it to sleep when you don't need it (so it doesn't drain your battery overnight), wake it back up on demand, and show you a signal-strength tile on your dashboard.

This page is the **5-step IKEA guide** for normal van owners. If you want the developer plumbing (HA helpers, automations, REST sensors, OpenWrt API wiring), see the [developer recipe](https://github.com/RoamCore/RoamCore/blob/main/connections/starlink/docs/recipe.md).

## What plugs into what

Before you touch anything, look at the picture. Every box is a thing you either have, or RoamCore sets up for you.

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 360" role="img" aria-label="Starlink wiring diagram: dish to power to router to Home Assistant to OpenClaw to your phone">
  <defs>
    <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 Z" fill="#333"/>
    </marker>
    <style>
      .box { fill: #fff; stroke: #333; stroke-width: 1.5; rx: 8; ry: 8; }
      .lbl { font: 600 13px sans-serif; fill: #111; }
      .sub { font: 11px sans-serif; fill: #555; }
      .pw  { stroke: #c0392b; stroke-width: 2; fill: none; }
      .da  { stroke: #2c3e50; stroke-width: 2; fill: none; }
      .wn  { stroke: #16a085; stroke-width: 2; stroke-dasharray: 6 4; fill: none; }
      .pl  { stroke: #2c3e50; stroke-width: 1.5; fill: none; opacity: 0.55; }
    </style>
  </defs>

  <!-- POWER SOURCE -->
  <rect class="box" x="20"  y="40" width="140" height="60"/>
  <text class="lbl" x="90"  y="62" text-anchor="middle">Battery / outlet</text>
  <text class="sub" x="90"  y="82" text-anchor="middle">12V or mains</text>

  <!-- SMART PLUG (optional) -->
  <rect class="box" x="20"  y="160" width="140" height="60"/>
  <text class="lbl" x="90"  y="182" text-anchor="middle">Smart plug</text>
  <text class="sub" x="90"  y="202" text-anchor="middle">only if Path B</text>

  <!-- STARLINK DISH -->
  <rect class="box" x="200" y="40"  width="160" height="70"/>
  <text class="lbl" x="280" y="64"  text-anchor="middle">Starlink dish</text>
  <text class="sub" x="280" y="84"  text-anchor="middle">on the roof (Gen-2 / Gen-3 / Mini)</text>

  <!-- STARLINK ROUTER -->
  <rect class="box" x="200" y="160" width="160" height="70"/>
  <text class="lbl" x="280" y="184" text-anchor="middle">Starlink router</text>
  <text class="sub" x="280" y="204" text-anchor="middle">built-in Wi-Fi</text>

  <!-- YOUR ROUTER (Path B/C only) -->
  <rect class="box" x="200" y="270" width="160" height="60" stroke-dasharray="5 4"/>
  <text class="lbl" x="280" y="290" text-anchor="middle">Your van router</text>
  <text class="sub" x="280" y="310" text-anchor="middle">Path B + C only</text>

  <!-- HOME ASSISTANT -->
  <rect class="box" x="420" y="100" width="160" height="80"/>
  <text class="lbl" x="500" y="124" text-anchor="middle">Home Assistant</text>
  <text class="sub" x="500" y="144" text-anchor="middle">the RoamCore brain</text>
  <text class="sub" x="500" y="160" text-anchor="middle">(on your Proxmox / Hub)</text>

  <!-- DASHBOARD -->
  <rect class="box" x="620" y="40"  width="120" height="60"/>
  <text class="lbl" x="680" y="62"  text-anchor="middle">Dashboard</text>
  <text class="sub" x="680" y="82"  text-anchor="middle">tiles on your wall</text>

  <!-- OPENCLAW -->
  <rect class="box" x="620" y="140" width="120" height="60"/>
  <text class="lbl" x="680" y="162" text-anchor="middle">OpenClaw</text>
  <text class="sub" x="680" y="182" text-anchor="middle">chat with the van</text>

  <!-- YOUR PHONE -->
  <rect class="box" x="620" y="240" width="120" height="60"/>
  <text class="lbl" x="680" y="262" text-anchor="middle">Your phone</text>
  <text class="sub" x="680" y="282" text-anchor="middle">RoamCore app / browser</text>

  <!-- WIRES -->
  <path class="pw" d="M90,100 L90,160" marker-end="url(#arr)"/>
  <path class="pw" d="M90,220 L90,260 L200,260 L200,75" marker-end="url(#arr)"/>
  <text class="sub" x="100" y="248" fill="#c0392b">power</text>

  <path class="da" d="M280,110 L280,160" marker-end="url(#arr)"/>
  <text class="sub" x="288" y="138">dish cable</text>

  <path class="pl" d="M280,230 L280,270" marker-end="url(#arr)"/>
  <text class="sub" x="288" y="252">ethernet (B/C)</text>

  <path class="wn" d="M360,180 Q390,180 420,140" marker-end="url(#arr)"/>
  <text class="sub" x="362" y="172" fill="#16a085">Wi-Fi (Path A)</text>

  <path class="wn" d="M360,300 Q390,260 420,180" marker-end="url(#arr)"/>
  <text class="sub" x="362" y="296" fill="#16a085">Wi-Fi (B/C)</text>

  <path class="da" d="M580,120 L620,70" marker-end="url(#arr)"/>
  <text class="sub" x="582" y="98">tiles</text>

  <path class="da" d="M580,140 L620,170" marker-end="url(#arr)"/>
  <text class="sub" x="582" y="158">agent</text>

  <path class="da" d="M580,160 L620,270" marker-end="url(#arr)"/>
  <text class="sub" x="582" y="248">PWA</text>

  <rect x="20" y="300" width="380" height="48" fill="#fafafa" stroke="#ddd"/>
  <text class="lbl" x="32" y="318">Legend</text>
  <line x1="32" y1="332" x2="62" y2="332" class="pw"/>
  <text class="sub" x="68" y="336">power</text>
  <line x1="120" y1="332" x2="150" y2="332" class="da"/>
  <text class="sub" x="156" y="336">ethernet / data</text>
  <line x1="248" y1="332" x2="278" y2="332" class="wn"/>
  <text class="sub" x="284" y="336">Wi-Fi</text>
  <line x1="332" y1="332" x2="362" y2="332" class="pl"/>
  <text class="sub" x="368" y="336">optional cable (Path B/C)</text>
</svg>
```

**What each line means:**

- **Power (red)** — electricity from your battery or wall outlet. Goes to the smart plug (if you have one) and into the Starlink power supply, which feeds the dish.
- **Ethernet / data (solid blue)** — wired links: the dish's own cable to its router, your router to your Home Assistant box.
- **Wi-Fi (dashed green)** — what your phone, laptop, and Home Assistant actually use to reach the internet. The dish's built-in router broadcasts it.
- **Optional cable (faint blue)** — only if you have a separate router (Path B) or a VM router inside the Proxmox (Path C).

**Who powers what:**

- The **smart plug** (if you have one) powers the **whole Starlink setup** (dish + router). When RoamCore turns the plug off, Starlink goes fully to sleep. When the plug comes back on, Starlink takes about 30–90 seconds to rejoin the satellites.
- The **dish** itself draws the most power (20–60 W depending on model). That's why RoamCore tries to put it to sleep during quiet hours.

**What happens if it's unplugged:**

- If the **smart plug** is unplugged or its Wi-Fi drops, RoamCore's "reachability" tile will go red. The dish is still powered by its own supply if the plug is on — but RoamCore can't see it.
- If the **dish** loses power (cable loose, PSU unplugged), your whole van loses Starlink internet until it powers back up.
- If **Home Assistant** loses power, the tiles go away. The Starlink dish keeps working — it just doesn't show up on your dashboard. As soon as HA boots back up, the tiles return.

---

## Step 1 — What is Starlink in your van?

Two pieces of hardware:

- **The dish** — sits outside (roof, ladder, window mount). Talks to satellites.
- **The router** — small box, comes with the dish. Broadcasts Wi-Fi. Has a local web page at `http://192.168.100.1/` where you can see signal stats and change settings.

That's it. Starlink is a self-contained terminal — it does not need a third-party router, but you **can** put one in front of it if you want (for better Wi-Fi range, multiple SSIDs, VPN, etc.).

---

## Step 2 — Plug it in

1. Mount the dish where it has a clear view of the sky.
2. Run the cable from the dish to the Starlink power supply (the white brick).
3. Plug the power supply into a wall outlet **or** into a controllable smart plug (see Step 3).
4. Wait ~90 seconds. The dish will point itself at the sky and acquire a satellite.
5. Connect your phone or laptop to the Starlink Wi-Fi network. The network name and password are on the back of the router.
6. Open a browser and go to `http://192.168.100.1/`. If you see Starlink's status page, you have internet.

**You're done with Step 2 when:** your phone shows the Starlink Wi-Fi network, and you can load a webpage on it.

---

## Step 3 — Pick your setup

RoamCore can wire Starlink into your dashboard in **three different ways**, depending on how your van is set up. Pick the one that matches.

| Your situation | Pick this | What RoamCore does |
|---|---|---|
| **"I just use the Starlink Wi-Fi as-is"** (Starlink Mini, or no extra router) | **Path A — Starlink Mini / built-in Wi-Fi only** | Reads signal and reachability straight from `http://192.168.100.1/`. No extra hardware. Easiest. |
| **"I have my own router plugged into the Starlink router"** (Peplink, Teltonika, GL.iNet, an old travel router, etc.) | **Path B — Separate router with a smart plug** | Uses a smart plug you already own to put Starlink to sleep. Gives you a "wake for 30 minutes" button and quiet-hours scheduling. |
| **"I run OpenWrt as a VM inside the Proxmox box"** (VP2430 setup) | **Path C — VM router inside the VP2430** | RoamCore talks to the OpenWrt API to manage the WAN. Best if you already have the Proxmox box and want one place to control all your networking. |

**Not sure?** If your Starlink is a Mini and you connect your phone directly to its Wi-Fi → **Path A**. If you connect your phone to a router that has "Starlink" plugged into its WAN port → **Path B**. If your phone connects to a Wi-Fi network that comes out of the Proxmox box → **Path C**.

**Common rule for all three paths:**

- **Gen-2 and Gen-3** dishes (and Starlink Mini) work with all paths. Signal-strength tile will show a number.
- **Gen-1** (the round "dishy" from 2021) has no local web API. The signal tile will be grayed out, but reachability and sleep/wake still work.
- RoamCore does not call Starlink's cloud. Everything runs locally on your LAN.

---

## Step 4 — Tell RoamCore about it

Open the RoamCore **Setup wizard** in your dashboard. It will ask one question first: **"How do you want to use Starlink?"** Pick the path from Step 3.

The wizard then does this for each path:

- **Path A** — RoamCore probes `http://192.168.100.1/` three times (with a short backoff between tries). If it can see the dish, it writes a few helpers and you're done (~10 min). If it can't, you get a plain-English message: *"I can't reach your Starlink — is the dish powered and are you on its Wi-Fi?"*
- **Path B** — RoamCore asks you to pick the smart-plug entity from Home Assistant (the one that controls the outlet the Starlink PSU is plugged into). It checks that the entity is exposed and switchable, then wires up the sleep / wake / quiet-hours contract (~25 min).
- **Path C** — RoamCore asks for the OpenWrt API URL (e.g. `http://192.168.1.250/cgi-bin/luci`) and a bearer token. It probes the API to confirm it works, then wires the contract to the OpenWrt side instead of a smart plug (~30 min).

**Re-running the wizard is safe.** It detects what you've already set up and only adds what's missing. Nothing gets duplicated.

**What if I get stuck?** See [Troubleshoot](#troubleshoot) below. Every error message in the wizard is plain English, not a code dump.

For the full developer plumbing (HA helpers, automations, REST sensors, OpenWrt API wiring, entity names), see the [developer recipe](https://github.com/RoamCore/RoamCore/blob/main/connections/starlink/docs/recipe.md).

---

## Step 5 — See it on your dashboard

Once the wizard finishes, open your RoamCore dashboard and look under **Networking**. You should see these tiles:

- **Sleep state** — shows `awake` / `asleep` / `waking`. Updated in real time.
- **Allow sleep** — a toggle. When ON, RoamCore will put Starlink to sleep during your quiet hours. When OFF, Starlink stays on 24/7.
- **Wake for 30 minutes** — a button. Press it when you need the internet for a video call, a download, or remote access. The dish comes back up for 30 min, then goes back to whatever the sleep timer says.
- **Reachable** — green dot when the dish (or smart plug, or OpenWrt) responds. Red when it doesn't.
- **Signal strength** — a 0–100% number. Grayed out on Gen-1.
- **Quiet hours start / end** — the time window when RoamCore is allowed to put Starlink to sleep. Default: 23:00 → 06:00.

You can also ask OpenClaw ("is Starlink on?", "wake Starlink for 30 minutes", "what's the Starlink signal?") and it'll answer from the same data.

**You're done when:** the tiles are visible, the "reachable" tile is green, and the "signal strength" tile shows a non-zero number on Gen-2 / Gen-3 / Mini.

---

## Troubleshoot

Three things go wrong most often. Pick the one that matches what you're seeing.

### "The dish won't come online"

What you see: the **Reachable** tile is red, or stays red after wake-up.

What it usually means: the dish can't see a satellite (obstruction, stowed, or still booting).

**Fix it:**

1. **Check the sky.** Can the dish see open sky in the direction it's pointing? Parked under a dense tree, inside a metal building, or next to a tall wall will block the signal.
2. **Check that the dish isn't in stow mode.** Gen-3 detects motion and parks itself if you start driving. It should un-stow when you stop. If it doesn't, open the Starlink app on your phone (connected to its Wi-Fi) and tap "Stow" off.
3. **Wait longer.** After a full power-down, Gen-3 takes up to 90 seconds to acquire a satellite. Gen-2 is faster (~30 s). Watch the dish — it should slowly rotate to point at the sky.
4. **If you have a smart plug (Path B):** the plug might be on, but the dish itself has a problem. Try unplugging the Starlink PSU from the smart plug for 30 seconds, then plugging it back in. This forces a hard reboot.
5. **Still nothing?** Power-cycle the Starlink power supply (unplug from the wall, count to 10, plug back in). The router Wi-Fi will disappear for ~90 seconds while the dish re-acquires.

### "The dashboard says 'can't reach Starlink' right after I run the wizard"

What you see: a red error in the setup wizard. **Don't panic** — this is the wizard telling you exactly what's wrong, in plain English.

Common messages and what they mean:

- **"I can't reach your Starlink — is the dish powered and are you on its Wi-Fi?"** → Your Home Assistant box can't talk to `http://192.168.100.1/`. Most often: Home Assistant is on a different network (e.g. a Peplink LAN) than the Starlink router. Fix: put HA on the same network, or add a static route from HA's network to `192.168.100.0/24`.
- **"I can't find the smart plug you picked"** → You picked an entity id that doesn't exist in Home Assistant. Go to **Developer Tools → States** and copy the exact entity id of your smart plug.
- **"That plug isn't switchable"** → You picked a sensor (read-only) instead of a switch. Look for a `switch.*` entity, not a `binary_sensor.*`.
- **"I can't reach the OpenWrt API"** (Path C) → The URL is wrong, the OpenWrt VM is off, or the token is wrong. Open the URL in a browser from your phone first to confirm it works.
- **"You didn't give me the info I need"** → A required field was left blank. Scroll up — the wizard will mark the empty field in red.

**Re-run the wizard.** Each run is safe; it won't make a mess if it fails halfway.

### "Everything was working, then it stopped"

What you see: tiles were green yesterday; today they're red. No settings changed.

What it usually means: something you depend on silently dropped out.

**Fix it:**

1. **Is the Starlink power supply actually on?** Check the wall outlet, the smart-plug switch state, and the PSU's own indicator light.
2. **Did the smart plug's integration drop its pairing?** (Path B) — Wi-Fi plugs occasionally lose their cloud or local connection. Re-pair in **Settings → Devices & Services**, then check the plug in **Developer Tools → States**.
3. **Did the Home Assistant box restart?** A reboot takes a few minutes to bring all the tiles back. The "Reachable" tile is the first to update; the signal-strength tile may take 60 seconds (it polls the dish once a minute).
4. **Did the Starlink firmware update?** Gen-3 firmware updates have, historically, changed the JSON schema at `http://192.168.100.1/api/console/dish-status.json`. If the signal-strength tile suddenly reads 0 forever, open **Developer Tools → Template** in HA and inspect the JSON. Look for a different field name (e.g. `snr_db` → `snr`).
5. **Check the RoamCore mode.** If you're in **Stealth** mode and "Allow sleep" is on, Starlink will sleep during the quiet-hours window. That's expected. To keep it awake, flip "Allow sleep" off, or change the quiet-hours window.

If nothing in this list fits, the [developer recipe](https://github.com/RoamCore/RoamCore/blob/main/connections/starlink/docs/recipe.md) has a longer troubleshooting section, and OpenClaw can read the live state for you ("is Starlink reachable? when was it last awake?").

---

## What you see on your dashboard

When everything is wired up, your RoamCore dashboard shows a **Starlink** section under **Networking** with these tiles:

- **Sleep state** (`awake` / `asleep` / `waking`)
- **Allow sleep** (toggle — when ON, the quiet-hours timer is armed)
- **Wake for 30 minutes** (button)
- **Reachable** (green / red)
- **Signal strength** (0–100% — grayed out on Gen-1)
- **Quiet hours start** / **Quiet hours end** (time helpers you can edit)

---

## Tier and what's next

This is a **tier-b (recipe) connection** today. That means: the recipe is solid, RoamCore honestly does what it says, but we don't yet claim one-tap automation across every Starlink install — because Path A (Mini-only) still depends on the Starlink local API behaving the way its docs say, and Paths B and C depend on a smart plug / OpenWrt token you bring.

**What would change this to tier-a** (RoamCore Certified, one-tap install): a Starlink test fixture landing in CI (a synthetic `dish-status.json` plus a fake plug entity) so we can assert the contract end-to-end without a real dish on the bench. The 3-path wizard shipped in Wave 9 #108 (see [developer recipe](https://github.com/RoamCore/RoamCore/blob/main/connections/starlink/docs/recipe.md)) is the first step toward that — Path A (Starlink Mini-only) is the tier-a promotion candidate because it needs no operator wiring.

Until then, you can rely on the recipe; just don't expect the catalog to claim this is hands-off. We don't ship aspirational claims.
