# RoamCore Hub

> **RoamCore Certified — reference platform**

Tells you exactly what's inside a RoamCore Hub — the router box, the antennas, the cables — and where to buy each part, so you can see what's in your van or build your own.

## What you get

The RoamCore Hub is the small metal box that sits in your van and quietly runs your whole dashboard. Inside it are a router, the Home Assistant software, your Wi-Fi, your cellular modem, and a small sensor that knows when your van is level and how warm or humid it is inside.

You plug it into 12 V power, screw four antennas onto the back, and connect it to your Starlink or 4G. Everything else is automatic — your dashboard appears on your phone, your laptop, and the in-van tablet.

## Five steps to a working Hub

### 1. Mount the box

Pick a dry, ventilated spot in your van. Screw the four anti-vibration mounts into the floor or a shelf, then click the Hub onto them. The Hub needs a clear 5 cm of airspace around it for cooling.

### 2. Connect power

Run the fused 12 V lead from your Electrical Box (or any clean 12 V source) to the screw terminal on the side of the Hub. Tighten the two screws so the wire can't pull free if the van hits a bump.

### 3. Screw on the antennas

- **WIFI 1 and WIFI 2** (top-left and top-right): the two black Wi-Fi antennas.
- **CELL 1 and CELL 2** (bottom row): the two 4G antennas. Keep CELL 3 and CELL 4 capped unless you're upgrading to 5G (see below).
- Hand-tighten each antenna. Don't use pliers — the brass threads snap if you over-tighten.

### 4. Plug in your internet

- **Port 1 (WAN)**: plug the cable from your Starlink router (use the Starlink Ethernet Adapter, not the Wi-Fi router only).
- **Ports 2, 3, 4 (LAN)**: plug in your Electrical Box, Water Box, and Safety Box — or any wired device.
- Power on. After about two minutes the Wi-Fi SSID named **RoamCore-Setup** will appear.

### 5. Open the dashboard

On your phone, join the **RoamCore-Setup** Wi-Fi. A small page will open automatically. Follow the five on-screen steps — it will ask which 4G SIM you have, name your van, and pick a password for your normal Wi-Fi. When the page says **Done**, the dashboard is live at the address printed on the quick-start card.

## What plugs into what

```
                          ┌────────────────────────────┐
                          │                            │
   Starlink router ─────► │  Port 1 (WAN)              │
                          │                            │
   Electrical box  ─────► │  Port 2 (LAN)              │
                          │                            │   Cell 1 ◄── 4G antenna (SMA)
   Water box        ─────► │  Port 3 (LAN)    Hub      │   Cell 2 ◄── 4G antenna (SMA)
                          │                  (VP2430)  │   Cell 3 ◄── (capped — 5G upgrade)
   Safety box       ─────► │  Port 4 (LAN)              │   Cell 4 ◄── (capped — 5G upgrade)
                          │                            │
                          │  12 V ──── Electrical box  │   Wi-Fi 1 ◄── Wi-Fi antenna (RP-SMA)
                          │                            │   Wi-Fi 2 ◄── Wi-Fi antenna (RP-SMA)
                          └────────────────────────────┘
```

The Hub runs two virtual machines side-by-side: a small router that handles Starlink and 4G failover, and Home Assistant that draws your dashboard. You never need to log into either of them by hand.

## Going from 4G to 5G later (optional)

When you're ready for faster cellular, you can upgrade without rewiring the van:

1. Power down the Hub.
2. Slide the LTE card out of its M.2 slot, slide the 5G card in.
3. Screw the four antenna leads onto the four labelled connectors on the new card (MAIN 1, AUX 1, MAIN 2, AUX 2).
4. Uncap CELL 3 and CELL 4 on the back panel and screw on the two extra antennas (from the 5G kit).
5. Power on. The dashboard will switch to the 5G view on its own.

The whole swap takes about ten minutes with a single screwdriver. The Hub reboots into its previous dashboard — your settings, Wi-Fi name, and password stay the same.

## What to do if it goes wrong

If the dashboard page won't open, the most common cause is that the antenna leads aren't fully screwed on — power down, tighten each one by hand, then power back on. If the Wi-Fi **RoamCore-Setup** network never appears after three minutes, check that the 12 V wire is live at the screw terminal (a small green LED on the side of the Hub should be on). If it's still missing, the quick-start card has the support QR code — scan it and we'll walk you through it.

## Find a part

If a part is damaged or you want to build a second Hub, every component in the box — and where to buy it — is listed in the Hub manifest. The manifest is the short, plain list that says: this part, this supplier, this price. Ask the Hub to print it from the dashboard, or read it directly on the project site.
