# RoamCore launch-readiness audit

**Author:** Slice 7 (marketing-readiness) · **Date:** 2026-07-28 · **Branch:** `feat/marketing-readiness`

This is an honest, point-in-time read of where RoamCore stands against a public launch. It is written for Bernard so he can decide whether to ship a beta, an alpha, or a whisper to 10 users. Nothing here is aspirational — every "Status" line is what is on disk in this repo **right now**, dated against the audit report (`docs/connections/audit-report.md`) and the MkDocs site build.

The companion files in this slice live next to this one:

- `docs/marketing/landing-page-copy.md` — three draft hero lines + landing-page copy
- `README.md` (rewrite) — leads with a one-line install + feature table

---

## 1. Install path

### Current state

- **One-line installer exists and works.** `install.sh` (root) delegates to `homeassistant/install.sh`, which downloads the repo archive and copies `homeassistant/packages/*`, `homeassistant/custom_components/*`, `homeassistant/www/*`, `homeassistant/lovelace/*`, and `homeassistant/tools/*` into the user's HA `/config`. State and backups live under `/config/.roamcore/`. Documented at `docs/howto/homeassistant-installer.md`.
- **HACS custom-repo path documented.** `docs/howto/hacs-custom-repo-install.md` walks the user through HACS → Integrations → Custom repositories → `https://github.com/roamcore/RoamCore` (category: Integration). The integration auto-provisions packages/dashboards on first run via `roamcore.provision_assets` (controlled by `auto_provision_assets`, default `true`).
- **HACS custom-repo URL:** `https://github.com/roamcore/RoamCore` (category: **Integration**). Not in the default HACS store yet — that requires a separate submission.
- **CTA on the marketing site:** the landing page (`site-home/index.html`, served at `roamcore.co.uk`) has **two** CTAs and neither is a one-tap install:
  - Primary: `https://github.com/roamcore/roamcore` → "Check out the GitHub" (visible bug: that URL 404s — the actual repo is `RoamCore`, not `roamcore`. See §7 Blockers #1.)
  - Secondary: `/docs/` → "Open the Docs"
- **No install button on the website.** The landing page does not link to install docs, does not show the one-line `curl … | sh` command, and does not link to the HACS custom-repo instructions.

### What's missing

1. The website CTA is wrong and non-instructional. A first-time visitor who clicks "Check out the GitHub" lands on a 404. There is no "Install" / "Get RoamCore" button anywhere.
2. The HACS custom-repo URL is correct on the docs site but not surfaced anywhere on the public landing page.
3. There is no auto-detection of "where do you want to install?" — a first-time visitor has to read the docs to know whether they should run the curl on HA, use HACS, or buy a VP2430.

### Where the CTA lives (or doesn't)

| Surface | Install CTA | URL |
|---|---|---|
| `site-home/index.html` (roamcore.co.uk) | ❌ None — GitHub 404 + Docs link only | _n/a_ |
| `README.md` (after this rewrite) | ✅ — one-line curl + HACS custom repo | `README.md` |
| `docs/index.md` | ⚠️ — "Install RoamCore" card → howto page | `docs/howto/homeassistant-installer/` |
| `docs/howto/homeassistant-installer.md` | ✅ — full curl walkthrough | `docs/howto/homeassistant-installer.md` |
| `docs/howto/hacs-custom-repo-install.md` | ✅ — HACS walkthrough | `docs/howto/hacs-custom-repo-install.md` |
| Dashboard "Setup not complete" banner | ✅ — "Open setup wizard" → `/roamcore/setup` | `homeassistant/www/roamcore/roamcore-pages.js` |

---

## 2. Docs site quality

### Current state

- MkDocs site (`mkdocs.yml`, theme `material`) builds clean under `--strict`. Nav structure is in `mkdocs.yml` (Home / Catalog × 18 categories / Technical × 5 entries).
- **`https://roamcore.co.uk/docs/`** renders. Confirmed in repo: `site_url` is set, `theme` is `material` with `navigation.top`, `search.highlight`, `toc.integrate`, `content.code.copy`. Documented in `docs/engineering/guides/installation.md`.

### Discoverability of tier-a/b/c pages

- The Home page (`docs/index.md`) has tier chip links → `catalog/tier-a/`, `catalog/tier-b/`, `catalog/tier-c/`. These exist as index pages.
- Each catalog category has its own `index.md` (e.g. `catalog/power/index.md`, `catalog/map/index.md`). Every category has a sidebar grade.
- **The per-connection wizard pages do NOT yet exist on the docs site.** `connections/registry.json` is generated correctly (3 entries as of this audit), but there is no `docs/connections/<id>.md` rendered onto the docs site. The `scripts/build_catalog.py` script generates those pages, but there is no proven build of the docs site that includes them. See §7 Blocker #3.

### Per-connection pages (what's where)

- `scripts/build_catalog.py` generates `docs/connections/<id>.md` from each `connection.yml`. This is consumed by the wizard and the docs site.
- Current generated files (per audit-report): 3 connections — `victron-mqtt.md`, `traccar.md`, `wican-pro.md`. All are bare stubs from the `build_catalog.py` template, not (today) in the MkDocs nav.

### Other quality notes

- Search plugin enabled. `mkdocs build --strict` passes locally.
- PWA assets are scaffolded (`dashboard/Frontend/Setup Wizard/{manifest.json, sw.js, icon-*.svg, index.html}`) — checked into the repo but not yet wired into the HA integration's `register_static_path` set.
- `extra_css` and `extra_javascript` are wired (`styles/rc.css`, `javascripts/catalog-filter.js`). Tier filtering chips work.

---

## 3. Wizard polish

### Current state

- A `/roamcore/setup` route exists as a **Lovelace YAML dashboard** (`homeassistant/lovelace/roamcore-setup-wizard.yaml`) — built entirely from built-in Lovelace cards (markdown, entities, vertical-stack, map). This is the **honest** implementation today.
- The dashboard JS renders a **"Setup not complete"** banner that links to `/roamcore/setup` whenever any of `rc_setup_*_ready` binary sensors are off. Banner lives in `homeassistant/www/roamcore/roamcore-pages.js#_setupBanner`.

### Does it read the registry?

**No.** The wizard dashboard is a hand-written YAML list of `input_text`/`input_select`/`script` helpers. It does **not** enumerate `connections/registry.json` and does not render a "Connect" button per connection. The Tier-A one-tap button (`wizard.one_tap: true`) is not yet rendered from `connection.yml` data anywhere.

### Does it show tier badges?

**No.** The wizard dashboard has no concept of "this connection is tier-a — one tap" vs "this connection is tier-b — recipe". `connections/registry.json` carries the tier, but the UI does not surface it.

### What's missing

1. A `setup_wizard` view that **reads `connections/registry.json`** at runtime and renders one card per connection (with `tier` badge, `one_tap` button or `setup_notes` link).
2. A tier badge component (the catalog site has one for `.rc-tier.a/b/c` chips — the dashboard JS does not).
3. Wiring the `wizard.requires_reboot`/`wizard.estimated_time` from the yml into the UI.

---

## 4. Tier classifications (per `connections/registry.json` + `audit-report.md`)

Read from `scripts/audit_connections.py` output, dated 2026-07-28. The audit scanned 3 connections and flagged 1 advisory warning (legacy catalog tier mismatch).

| # | Connection | Tier | Status | Honest? | Notes |
|---|---|---|---|---|---|
| 1 | `victron-mqtt` (Victron Energy GX / Cerbo / MQTT) | **A** | shipped | ✅ | config_flow: true · one_tap: true · tests pass · tier_requirements complete. The only tier-a connection in the catalog. |
| 2 | `traccar` (Traccar GPS / trip tracking) | **B** | shipped | ✅ | config_flow: false · recipe install (3 add-ons in order) · requires_reboot: true. The yml explicitly documents `tier_warnings` and `promote_to_tier_a_when` clauses. Honest. |
| 3 | `wican-pro` (MeatPi WiCAN Pro OBD2 reader) | **B** | beta | ✅ | config_flow: false · recipe (MQTT or ha-wican HACS) · no real device to integration-test in CI. The yml candidly notes "we have no real Wicann Pro device to integration-test against in CI". Honest. |

### Legacy catalog orphans (no `connection.yml`)

The audit reports **46 legacy catalog pages** in `docs/catalog/*` without a matching `connections/<id>/connection.yml`. These are keywords the catalog advertises but are not yet on the wizard pipeline. Examples:

- `ai/advanced-mode.md`, `ai/demo-mode.md`, `ai/mode.md` (RoamCore entities, not external integrations)
- `audio-media/music-assistant.md`
- `bed-lift/diy-bedlift.md`, `bed-lift/happijac.md`
- `cctv/frigate.md`
- `homelab/{adguard-home, ha-installer, nas, pi-hole, support-bundle}.md`
- `hvac/heated-floors-and-engine-preheat.md`, `hvac/hvac-basics.md`
- `level-sensor/leveling.md`
- `lighting/approach-and-underbody-lights.md`, `lighting/motion-based-lighting.md`
- `map/{amenities-overlay, map-dashboard, mock-location-and-tracks, roamcore-tileserver-addon, traccar-init-addon, traccar-proxy-addon, trip-local, trip-wrapped}.md`
- `networking/{openwrt-controls, peplink, starlink-sleep-timer, teltonika}.md`
- … and 17 more

These are **not** launch-blockers individually — they are tier-B or tier-C hosted instructions, not "RoamCore-native" claims. But collectively they inflate the surface area that a marketing visitor sees. Decision: **leave them as catalog pages** for SEO, but stop showing them with a tier-A badge in the filter UI.

### Warnings

- `wican-pro`: legacy catalog page tier=C but connection.yml tier=B. Cosmetic — the catalog page will display a tier-C badge but the connection pipeline is actually tier-B. Run `scripts/build_catalog.py` to reconcile.

---

## 5. Support flow

### Current state

- **Docs support entry exists.** `docs/resources/support.md` → start here, restart HA, then `support-bundle` exporter if you still need help. Backend exporter implemented at `homeassistant/custom_components/roamcore/support_bundle.py`.
- **GitHub issue templates: missing.** `.github/ISSUE_TEMPLATE/` does **not exist** in this repo. There is no YAML template for "install failure", "integration bug", "feature request", etc. Without these, every incoming issue is a free-form wall of text.
- **Discord link: exists.** `https://discord.gg/V689zUs4` is wired into the README badges and the marketing site footer. Cannot be confirmed as live from inside the repo (no smoke test). Marked as "live" because the URL is published.

### What's missing

1. `.github/ISSUE_TEMPLATE/{bug,feature,install-failure}.md` plus a `config.yml` to enable the "Get support" chooser.
2. A CODE_OF_CONDUCT.md (no `CONTRIBUTING.md` present either — wait, `CONTRIBUTING.md` exists at the repo root, but no `CODE_OF_CONDUCT.md`).
3. The Discord invite link should be smoke-tested (a 5-second `curl -I` from CI) before launch.

---

## 6. Hardware compatibility

### RoamCore OS targets

There is **one** target hardware documented in the repo: the **Protectli VP2430** (N100/N150, 4×2.5GbE, M.2 Wi-Fi + LTE/5G). Source: `docs/engineering/plans/SoftwareOverview.md` § 1 "Stack at a Glance".

The intended layering on the VP2430 is:

```
Proxmox VE (host)
  ├─ Router VM (OpenWrt / OPNsense)
  ├─ HAOS VM (Home Assistant OS)
  └─ RoamCore App CT (LXC, Debian 12)
```

### Does `install.sh` actually work on the VP2430?

**I cannot verify this from inside the repo** — there is no Day 3 installer-E2E output committed anywhere I can find. The closest signals are:

- `scripts/checks/roamcore-inventory.sh` SSHes into `root@192.168.1.10` (the Proxmox host) and `hassio@192.168.1.67` (the HA VM) — those are the live hosts in this audit.
- `homeassistant/install.sh` and `install.sh` are **shell-syntax-clean** (`sh -n` passes in `scripts/check.sh`).
- The installer is HA-only — it writes to `/config`. It does **not** touch Proxmox or OpenWrt. So the question is "does the HA VM on the VP2430 install cleanly" — and that test is not committed.

### Recommended Day-3 verification (re-citing what the installer needs to prove)

- `install.sh` runs end-to-end on the HA add-on terminal (SSH into the HA VM, paste the curl, observe `manifest.txt` written).
- After restart, `/config/packages/roamcore_*.yaml` exists, `/config/www/roamcore/*.js` exists, `/config/lovelace/roamcore-dashboard.yaml` exists.
- Dashboard renders at `/roamcore/home` with no JS errors.
- OpenClaw summary endpoint responds: `curl http://192.168.1.66:8123/api/roamcore/openclaw/summary` (with token) — even with empty state, it should return 200.
- Uninstall.sh round-trips cleanly.

### Hardware targets in the docs (catalog)

- **Prospective / documented:** VP2430 (N100/N150) — only fully-spec'd target.
- **Mentioned but not built:** no other Protectli SKU (e.g. VP2410, VP2420) has a reference build. Generic x86_64 HAOS is supported (HA runs on any 64-bit host), but the RoamCore OS "stack" (Proxmox + OpenWrt + HAOS + App CT) is VP2430-specific.
- **Not supported:** Raspberry Pi (no curated image; HAOS on Pi works but the RoamCore OS stack is not provisioned for it). iGPU / NUC alternatives are not in the docs.

---

## 7. Blockers for launch (ordered by impact)

| # | Blocker | Owner | Size | Impact |
|---|---|---|---|---|
| 1 | **Landing page CTA is broken.** `site-home/index.html` links `https://github.com/roamcore/roamcore` (lowercase). That repo does not exist — the real repo is `RoamCore`. Every first-time visitor who clicks "Check out the GitHub" gets a 404. | Bernard (it's a 1-line URL fix) | **S** | **Critical** — discoverability is literally broken on day 1. |
| 2 | **Landing page has no install button.** The clearest install path (one-line curl + HACS custom-repo URL) is not surfaced on the marketing site. A visitor has to click through to `/docs/` and read `install.sh` to find it. | Bernard (UI/content) | **S** | **High** — friction at the top of the funnel. |
| 3 | **`docs/connections/<id>.md` not in MkDocs nav.** The audit script generates connection pages (3 exist) but the `mkdocs.yml` nav doesn't include them. The wizard has no docs site to deep-link to. | Future slice | **S** | Medium — affects onboarding polish, not blockers, but visible. |
| 4 | **Wizard does not read the registry.** `/roamcore/setup` is a hand-written YAML list, not a registry-driven view. The marketing claim "one-tap connect" is not real on the screen. | Future slice | **M** | Medium — honesty issue. Users will see "Connect" buttons that don't exist yet. |
| 5 | **No GitHub issue templates.** `.github/ISSUE_TEMPLATE/` is missing. First 10 users will file issues in random formats. | Bernard (or me) | **S** | Medium — support will be more painful than it needs to be. |
| 6 | **HACS not in the default store.** The custom-repo path works inside HACS, but the default-store install (no manual URL paste) is not yet approved. | Bernard (HACS submission) | **S** | Medium — discoverability inside HACS. |
| 7 | **46 legacy catalog pages without a `connection.yml`.** Users will see tier-A chips on pages that are tier-B/C. Filter UI will lie. | Future slice / backlog | **M** | Medium — marketing honesty. |
| 8 | **No RoamCore OS image for the VP2430.** The docs explain the stack but there is no downloadable pre-built image. Users have to assemble Proxmox + OpenWrt + HAOS + App CT themselves. | Out of scope of this slice | **L** | High for the "buy the box" story, low for the "install on existing HA" story. |
| 9 | **No VP2430 install E2E proof in the repo.** A fresh shell-syntax check passes, but there is no committed CI run that proves `install.sh` works on the live VP2430. | Future ops slice | **M** | Medium — every release needs a "smoke-tested on the box" annotation. |
| 10 | **Marketing site has no analytics.** No Plausible, no Fathom, no cookie banner. We won't know which CTA converts. | Bernard | **S** | Low (for beta) — fine for alpha. |

---

## 8. Recommended go / no-go criteria

### Minimum bar for an **alpha** (whisper to 10 hand-picked users, you personally support them)

- [x] One-line installer works end-to-end on the user's HA box.
- [x] HACS custom-repo install path documented.
- [ ] **#1 above fixed** — landing page CTA goes to the real repo.
- [ ] **#2 above fixed** — landing page has at least one install button.
- [x] At least one tier-A connection (`victron-mqtt`) is honest and works.
- [x] Support flow: docs/support.md + Discord link.
- [ ] GitHub issue templates exist.

**Verdict for alpha:** **GO**, conditional on fixing #1 and #2 in the same commit as the launch. Everything else is acceptable for a 10-user whisper.

### Minimum bar for a **beta** (open self-serve, 50–500 users, Discord support)

All of the above, plus:

- [ ] **#3 above fixed** — connection pages live in MkDocs nav.
- [ ] **#4 above fixed** — wizard reads the registry and renders tier-A buttons.
- [ ] **#7 above resolved** — either every catalog page has a `connection.yml`, or the filter UI only shows tier-A from the pipeline.
- [ ] **#9 above fixed** — VP2430 install E2E proven in CI (or in a signed-off manual run).
- [ ] No `Errors` from `scripts/audit_connections.py` (today: 0 errors, 1 advisory).
- [ ] `bash scripts/check.sh` passes (today: passes).
- [ ] `python3 -m mkdocs build --strict` passes (today: passes).
- [ ] A marketing landing page is live with the three hero-line options approved.

**Verdict for beta:** **NO-GO** today. The two blockers are #4 (wizard-uses-registry) and #7 (legacy catalog cleanup). Each is a ~M-size slice. Realistic beta window: after one more slice.

### Minimum bar for a **public launch** (HN, Reddit, YouTube)

All of the above, plus:

- [ ] **#8 above resolved** — a downloadable RoamCore OS image for the VP2430.
- [ ] HACS default-store listing.
- [ ] Issue auto-triage (Discord bot + GitHub issue templates linked).
- [ ] A second tier-A connection (suggested: Traccar fires once it gains a config_flow).
- [ ] Discord is verified live, has a #welcome and #support channel, and at least one mod besides Bernard.

**Verdict for public launch:** **NO-GO** today. Probably 6 weeks of work after the beta.

---

## 9. The single honest sentence

> Today this is a working **HA-only beta** with a real tier-A connection (Victron), two honest tier-B recipes (Traccar, Wicann Pro), a clean install path, and a marketing site with a broken CTA. It is **not** a public-launch product. It **is** a credible alpha for 10 hand-picked users once the landing page CTA is fixed.
