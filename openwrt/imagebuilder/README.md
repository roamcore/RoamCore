# RoamCore OpenWrt Image Builder

Produces flashable sysupgrade images with the RoamCore networking API,
firewall rules, and LuCI landing page preinstalled, for each
supported target.

## Targets

| Friendly slug | Image Builder profile | Hardware |
| --- | --- | --- |
| `generic-x86-64` | `x86_64-generic` | VP2430 VM + any x86_64 box |
| `gl-mt3000` | `gl-mt3000` | GL.iNet GL-MT3000 (Beryl AX) |
| `bananapi-bpi-r3` | `bananapi-bpi-r3` | Banana Pi BPI-R3 |
| `ath79-generic` | `ath79-generic` | Atheros / MT76 catch-all |

## Build environment

The recommended way to build images is via the pinned Docker
container defined in [`Dockerfile`](Dockerfile). The container pins:

- **OpenWrt Image Builder** — version `24.10.4` by default. Override
  with `OPENWRT_VERSION=<x>` at build time.
- **Target** — `x86_64` (the host running the Image Builder inside
  the container, not the target being built for).
- **Base image** — `ubuntu:22.04` with a minimal apt set:
  `ca-certificates`, `curl`, `bash`, `xz-utils`, `git`, `file`,
  `libarchive-tools`. Nothing else is added; this keeps the base
  layer stable.

### Why a container?

- The Image Builder is a glibc Linux binary; running it on macOS or
  WSL requires a Linux container.
- Pinning the entire build environment (apt versions, wget, tar,
  libarchive) eliminates the largest source of build-time
  non-determinism.
- Reproducible builds need *every* byte-producing tool pinned; this
  is the simplest way to achieve that.

### Building without Docker

If you can run a Linux Image Builder directly, set `OPENWRT_IB_DIR`
to point at it and run `build.sh` from this directory. Example:

```bash
# 1. Download Image Builder for your target.
wget https://downloads.openwrt.org/releases/24.10.4/targets/x86_64/openwrt-imagebuilder-24.10.4-x86_64.Linux-x86_64.tar.xz
tar -xJf openwrt-imagebuilder-24.10.4-x86_64.Linux-x86_64.tar.xz
mv openwrt-imagebuilder-24.10.4-x86_64.Linux-x86_64 openwrt-ib

# 2. Run the build.
OPENWRT_IB_DIR=$PWD/openwrt-ib ./build.sh
```

The build host must be Linux x86_64. We do not support building
images on macOS, Windows, or BSD — the Image Builder's toolchain is
glibc-only.

## Usage

### Inside the Docker container

```bash
# Build all four targets.
docker build -t roamcore-imagebuilder:24.10.4 .
docker run --rm \
    -v "$PWD/../flash:/out" \
    -e OPENWRT_VERSION=24.10.4 \
    roamcore-imagebuilder:24.10.4

# Build a single target.
docker run --rm \
    -v "$PWD/../flash:/out" \
    -e OPENWRT_VERSION=24.10.4 \
    roamcore-imagebuilder:24.10.4 \
    gl-mt3000
```

The resulting images are written to `openwrt/flash/<slug>/`:

```
openwrt/flash/
├── generic-x86-64/
│   ├── generic-x86-64-roamcore-sysupgrade.itb
│   ├── generic-x86-64-roamcore-sysupgrade.itb.sha256
│   └── MANIFEST.txt
├── gl-mt3000/
│   └── …
├── bananapi-bpi-r3/
│   └── …
└── ath79-generic/
    └── …
```

### Output structure

- `*-roamcore-sysupgrade.itb` — the flashable image.
- `*.itb.sha256` — SHA-256 checksum. Compare this between builds to
  confirm reproducibility.
- `MANIFEST.txt` — human-readable summary of what was baked in
  (packages, OpenWrt version, RoamCore git commit).

## Reproducibility

We aim for **same input → same sha256** across runs. Sources of
non-determinism and our mitigations:

| Source | Mitigation |
| --- | --- |
| OpenWrt package feeds | Pin `OPENWRT_VERSION` (default 24.10.4). |
| opkg `.sig` metadata | Image Builder's `make image` does not sign output sysupgrade images, so this does not apply. |
| Squashfs compression timestamps | Image Builder always emits a deterministic tarball. |
| Build host clock | Not used by the image; logs only. |
| Bake-in tree git state | Bake-in files are committed to the repo and copied verbatim. SHA-256 is deterministic per commit. |

If you observe a hash mismatch between two builds of the same
commit, please open an issue with the two `MANIFEST.txt` files.

## Per-target package manifests

Each supported target has its own `.manifest` file under
[`manifests/`](manifests/). Adding a new target means:

1. Pick the OpenWrt Image Builder profile name (e.g. `ramips-mt7621`).
2. Copy the closest existing `.manifest` and adjust the driver /
   firmware lines.
3. Add an entry to the `TARGETS` array in `build.sh`.
4. Add a "Flash instructions" subsection to `openwrt/README.md`.

## What is baked in (the `bake/files/` overlay)

The Image Builder's `FILES=` argument merges `bake/files/` into the
final rootfs. See [`bake/files/`](bake/files/) for the current
contents:

```
bake/files/
├── etc/
│   ├── init.d/
│   │   ├── roamcore-api
│   │   └── roamcore-fw
│   ├── roamcore-api.env.example
│   └── uci-defaults/
│       └── 99-roamcore-firstboot
├── opt/
│   └── roamcore/
│       ├── api.py
│       └── iptables_mvp.sh
└── www/
    ├── cgi-bin/
    │   └── luci-static-index.html
    └── luci-static/
        └── resources/
            └── view/
                ├── roamcore_menu.js
                └── roamcore_status.js
```

These files are kept in sync with `openwrt/netstack/` by the build
script (file copy at build time). To update the API:

```bash
# 1. Edit openwrt/netstack/api/api.py (the source of truth).
# 2. Re-run the build. The build script mirrors the latest netstack
#    code into bake/files/opt/roamcore/api.py.
```

## Smoke check

```bash
bash scripts/checks/openwrt-imagebuilder-smoke.sh
```

This validates the manifests, the bake-in tree, the build script's
syntax, and that no secrets have been accidentally baked in. It does
**not** require the Image Builder or Docker — it is safe to run on
any host.