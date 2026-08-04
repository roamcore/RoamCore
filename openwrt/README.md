# RoamCore OpenWrt image

A flashable OpenWrt image with the RoamCore networking API, firewall
rules, and a "RoamCore status" LuCI landing page preinstalled.
Designed to bring any supported router (or VM) onto RoamCore in one
flash + one reboot.

## What you get on first boot

- A clean OpenWrt install with LuCI (web UI on `http://192.168.1.1`).
- The RoamCore networking API on `http://192.168.1.250:8080`. No
  authentication required on first boot — the API is LAN-only.
- A firewall service that applies the RoamCore NAT + forwarding rules.
- A first-boot wizard (`/etc/uci-defaults/99-roamcore-firstboot`) that
  asks for the Home Assistant IP and generates a fresh `RC_API_TOKEN`.
- A "RoamCore status" card at the top of LuCI.

## Flash instructions

Pick your hardware. Every flash below assumes the router is at
`192.168.1.1` on first boot (default).

### a) x86_64 generic (the VP2430 VM form factor)

Use this when RoamCore is running inside a Proxmox VM on the
VP2430 host. Download `generic-x86-64-roamcore-sysupgrade.itb` from
the [Releases](../../releases) page. From the Proxmox host, copy the
image into the OpenWrt VM, then either flash via the VM's serial
console (`sysupgrade -n /tmp/<image>.itb`) or, if you have the GUI
up, use **System → Backup/Flash Firmware → Flash new firmware image**.
On first boot you will see a LuCI login; the API is on
`http://192.168.1.250:8080`. Verify with:

```bash
curl http://192.168.1.250:8080/api/v1/status
```

### b) GL.iNet GL-MT3000 (Beryl AX)

Download `gl-mt3000-roamcore-sysupgrade.itb`. Plug a laptop into the
GL-MT3000's LAN port. Browse to `http://192.168.1.1` and run
**System → Backup/Flash Firmware → Flash new firmware image**, then
select the `.itb` file and tick **Keep settings** OFF (we want a
clean RoamCore bake). Wait ~90 seconds for the device to reboot.
The API is now on `http://192.168.1.250:8080`. Verify:

```bash
curl http://192.168.1.250:8080/api/v1/status
```

### c) Banana Pi BPI-R3

Download `bananapi-bpi-r3-roamcore-sysupgrade.itb`. The BPI-R3 ships
with U-Boot on NAND; flash the `.itb` via the OpenWrt web UI (same
flow as the GL-MT3000 above). First boot takes ~30 seconds while UBI
attaches. If you prefer SD-card install, convert the `.itb` with
`ubinize` — see the [BPI-R3 OpenWrt wiki](https://openwrt.org/toh/sinovoip/bananapi_bpi-r3).
Verify on `http://192.168.1.250:8080/api/v1/status`.

### d) Generic Atheros / MT76 router (ath79-generic)

This is the catch-all image. Download
`ath79-generic-roamcore-sysupgrade.itb` and flash via LuCI
(**System → Backup/Flash Firmware**). If the router's subtarget is
not yet covered by the OpenWrt Image Builder, the build script will
refuse to run rather than emit a brick; pick the closest per-target
profile (see `openwrt/imagebuilder/manifests/`) or open an issue.

### After flashing — what to expect on first boot

1. The router comes up with the RoamCore LuCI page.
2. The first-boot wizard prompts on the serial console (if attached)
   for the Home Assistant IP. If no console is attached, the router
   boots into "safe mode": API on `192.168.1.250:8080`, no auth.
3. The wizard generates a fresh `RC_API_TOKEN` in
   `/etc/roamcore-api.env`. You can read it from LuCI
   (**System → RoamCore status → API token**) or over SSH
   (`cat /etc/roamcore-api.env`).
4. Run the wizard again any time:
   ```bash
   rm /etc/uci-defaults/.firstboot-done
   /etc/uci-defaults/99-roamcore-firstboot
   ```

### Verify the install (all targets)

From any machine on the same LAN:

```bash
curl http://192.168.1.250:8080/api/v1/status
```

You should see JSON with a `state` field (`running` is good). If you
see a connection refused error, the API service is not running — log
into the router via SSH and run `/etc/init.d/roamcore-api start`.

## Re-flashing as the documented recovery path

If anything goes wrong — wrong Home Assistant IP, lost token,
firewall broken — re-flash the image. It is the supported recovery
path; we do not provide in-place migration. The first-boot wizard
will run again on next boot.

## Building your own image

See [`openwrt/imagebuilder/README.md`](imagebuilder/README.md) for the
build environment and how to produce a new image with your own
package list or LuCI customisations.

## What's inside (developer view)

The image is built from the official OpenWrt Image Builder with the
following RoamCore-specific files baked in:

- `/opt/roamcore/api.py` — the RoamCore networking API (mirrored
  from `openwrt/netstack/api/api.py`).
- `/opt/roamcore/iptables_mvp.sh` — the firewall MVP (mirrored
  from `openwrt/netstack/firewall/iptables_mvp.sh`).
- `/etc/init.d/roamcore-api` — API service definition.
- `/etc/init.d/roamcore-fw` — firewall service definition.
- `/etc/uci-defaults/99-roamcore-firstboot` — first-boot wizard.
- `/www/luci-static/resources/view/roamcore_status.js` — LuCI
  RoamCore status page (first card on the LuCI overview).
- `/etc/roamcore-api.env` — environment for the API; created on
  first boot with a freshly generated `RC_API_TOKEN`.

The original sources live under `openwrt/netstack/` and are kept in
sync with the image bake-in by the build script (file copy at build
time).