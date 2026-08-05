# Hardware

Reference hardware for RoamCore.

- `MainHub/Overview.md` — the design notes for the RoamCore Hub (the VP2430 single-box appliance).
- `roamcore-hub-bom.yml` — the canonical list of every part inside the Hub (with supplier + price + link).

The Hub manifest is validated by `scripts/build/hub-bom-validate.py` and exercised end-to-end by `scripts/checks/hub-bom-smoke.sh`. Every change to the manifest must keep both green.
