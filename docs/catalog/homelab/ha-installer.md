# Home Assistant installer (one-line)

**Support tier:** A (RoamCore native)

## What this is
RoamCore ships `install.sh`/`uninstall.sh` to install the integration and assets into Home Assistant.

## Why it’s useful in a van
- Fast setup and repeatable installs
- Easy rollback if something goes wrong

## Extra hardware required
- None

## Install / best next step
- See: `docs/howto/homeassistant-installer.md`

## Links
- (Add videos/quickstart)

---

## SUPERSEDED — moved to `connections/ha-installer/` (Wave 3 #71)

**This legacy catalog page is SUPERSEDED by the new `connections/ha-installer/` connection folder (Wave 3 #71 — tier-a recipe connection).**

The legacy tier-a "RoamCore native" claim is preserved as **honest-upstream-truth**: RoamCore DOES ship + maintain the canonical installer scripts at `install.sh` + `uninstall.sh` + `homeassistant/install.sh` + `homeassistant/uninstall.sh` + the operator howto at `docs/howto/homeassistant-installer.md`. The new connection folder wraps these as a tier-a recipe connection manifest with:

- 10 `rc_ha_installer_*` contract tiles (vendor-neutral per `docs/reference/rc-entity-naming.md`)
- FIVE §8 MANDATORY automations (install-button guard + uninstall-button guard + stale-version detector + installed-assets-match-repo + install-failure capture)
- The 5-step operator flow (Run install → Verify → Pin version (optional) → Run uninstall → Reinstall)
- The idempotent guard (backups to `/config/.roamcore/backups/<timestamp>/`)
- The RC_API_TOKEN-aware wiring

See:
- `connections/ha-installer/connection.yml` — tier-a manifest
- `connections/ha-installer/README.md` — folder overview
- `connections/ha-installer/docs/recipe.md` — full operator-facing howto (13 §sections)
- `connections/ha-installer/tests/test_connection_yml.py` — 8 manifest-honesty tests (8/8 PASS)
