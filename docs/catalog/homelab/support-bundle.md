# Support bundle export (logs + config snapshot)

## What it does
A documented way to generate a support bundle so issues can be debugged quickly without back-and-forth.

## Why it’s useful in a van
- Faster troubleshooting when something breaks on the road
- Clear “what to send” when asking for help

## How to install
- None

- See: `docs/howto/support-bundle.md`

## Useful links
- (Add troubleshooting video/resources later)

## How it works

What RoamCore does behind the scenes.

---

## SUPERSEDED — superseded by `connections/support-bundle/`

**This legacy 15-line tier-a "RoamCore native" claim stub is SUPERSEDED by the canonical recipe connection at [`connections/support-bundle/`](../../../connections/support-bundle/) (Wave 3 #72, PR #79).**

The legacy tier-a "RoamCore native" claim was preserved here as aspirational with the canonical surface still at `docs/howto/support-bundle.md` (44 lines, the canonical operator-facing howto) + the canonical exporter at `homeassistant/custom_components/roamcore/support_bundle.py` (286 LOC, real `async def export_support_bundle(hass, *, include_zip=True) -> dict` + 8 private helpers) + the matching `homeassistant/custom_components/roamcore/services.yaml` file (registers `export_support_bundle` with optional `zip: true`) + the handler wiring in `homeassistant/custom_components/roamcore/__init__.py` (registers `_svc_export_support_bundle` via `async_register_service`).

**Tier-a honesty:** the tier-a claim in this legacy stub is HONEST-upstream-truth. RoamCore ships + maintains + audits the canonical exporter code + the service registration + the handler wiring + the operator howto. The recipe connection at `connections/support-bundle/` is the dashboard-side companion (the 8 `rc_support_bundle_*` contract tiles + the FIVE §8 MANDATORY automations + the privacy audit). This SUPERSEDED banner is the audit's cross-reference marker for the bookkeeping flush.

**Supersession follows the established RoamCore connection-pipeline pattern (leveling #60 / mode #61 / demo-mode #62 / advanced-mode #63 / openclaw-api #64 / trip-local-tier-a #68 / trip-wrapped-tier-a #69 / bed-lift-diy-tier-c #70 / ha-installer #71 follow-up).**

**See also:**
- The recipe connection: [`connections/support-bundle/`](../../../connections/support-bundle/)
- The canonical operator howto: [`docs/howto/support-bundle.md`](../../howto/support-bundle.md)
- The canonical exporter: `homeassistant/custom_components/roamcore/support_bundle.py`
- The recipe: [`connections/support-bundle/docs/recipe.md`](../../../connections/support-bundle/docs/recipe.md)
