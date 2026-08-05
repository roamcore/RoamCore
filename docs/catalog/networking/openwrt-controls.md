# OpenWrt router - auto-pair

Plug your OpenWrt router into Home Assistant in 5
steps. No manual IP entry. No SSH. No LuCI token
copy-paste.

## Step 1

Plug your OpenWrt router into the same network as
Home Assistant.

Use any free LAN port on your home router or switch.
The OpenWrt router needs power (PoE or a wall
adapter) and an Ethernet cable to the same network
Home Assistant is on.

## Step 2

Open the RoamCore app -> Settings -> Connections ->
OpenWrt.

On your phone, tablet, or laptop, open the RoamCore
app (or the RoamCore dashboard in a browser).
Navigate to **Settings -> Connections -> OpenWrt**.
You'll see the OpenWrt auto-pair screen.

## Step 3

Tap "Find my router".

The router's blue LED blinks twice when found.

RoamCore scans your network for OpenWrt routers.
When it finds one, the router's blue LED blinks
twice (about 2 seconds apart) so you can confirm
visually that it's the right one. If RoamCore
can't find your router, see "If RoamCore can't
find your router" below.

## Step 4

RoamCore finds your router and asks you to confirm
the pairing code.

RoamCore shows the router's IP address and a
short pairing code (the first 8 characters of the
token RoamCore is about to push). Tap **Confirm
pairing** to push the token to your router.

## Step 5

Done. Your router shows up under Networking ->
OpenWrt.

The router is paired. Your OpenWrt controls tiles
(internet status, active WAN, LTE signal, Starlink
state, etc.) all populate under Networking ->
OpenWrt.

---

## If RoamCore can't find your router

You'll see one of three plain-English messages.
None of them require you to read logs or copy
IP addresses:

  - **"We couldn't find your OpenWrt router on the
    network. Make sure it's plugged in."** - Check
    the Ethernet cable. Check that the router's
    power LED is on. Wait 30 seconds (the router's
    first-boot wizard takes a moment to set up).

  - **"Your OpenWrt router was found but it hasn't
    been paired with RoamCore yet. Try restarting
    the router."** - Restart the router (unplug
    power for 10 seconds, plug back in). Wait 30
    seconds for the first-boot wizard to complete.
    Try again.

  - **"Pairing didn't work. Check the network cable
    between your router and Home Assistant."** -
    Check both ends of the network cable. Try a
    different port on your home switch. Re-pair.

---

## What plugs into what

```
[OpenWrt router] --Ethernet--> [Home switch] --Ethernet--> [Home Assistant]
                                |
                                +--Ethernet--> [Your laptop / phone]
```

The OpenWrt router needs:

  - Power (PoE or wall adapter)
  - One Ethernet cable to your home network

Home Assistant needs:

  - The existing home network connection (already
    set up before you started)
  - Nothing else - RoamCore's auto-pair uses the
    existing connection

---

## Want more details?

  - **Recipe** (the full howto + the section-8
    mandatory automations + the troubleshooting
    entries + the privacy section + the tier-a
    promotion outline):
    `connections/openwrt/docs/recipe.md`
  - **Devbox runbook** (running the probe against
    a real OpenWrt on a dev box):
    `connections/openwrt/docs/runbook-devbox.md`

---

## Links

  - OpenWrt: https://openwrt.org/
  - Home Assistant: https://www.home-assistant.io/