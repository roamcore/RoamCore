# Frigate — vendor-neutral NVR backend with on-device person / car / animal / package detection

**Tier:** B (recipe)
**Category:** cctv
**Status:** beta

## What this connection is

Frigate — vendor-neutral NVR backend with on-device person / car / animal / package detection that the upstream HA core `frigate` integration exposes for IP-camera motion detection + recording + audit trails — is the security-category umbrella for "the camera backend everything depends on". The recipe walks the operator through THREE upstream NVR paths (Path A HACS frigate add-on — recommended for most operators; Path B external / cloud NVR; Path C local container / VM NVR) + mounting the camera URLs (`input_text.rc_security_camera_url` a comma-separated list of camera URLs; `input_text.rc_security_camera_username`; `input_boolean.rc_security_camera_motion_enabled`) + confirming the cameras are online (`binary_sensor.rc_security_camera_online` reads TRUE) + enabling + starting recording (`input_boolean.rc_storage_recording_enabled` flips ON; the upstream `record` service exposes a GUI flow under Developer Tools → Services) + auditing (the HA core `logbook` integration is the canonical audit-log destination; `sensor.rc_security_camera_last_motion` mirrors the upstream `frigate` integration's per-camera last-motion timestamp) + reverting at any time via `button.rc_storage_recording_reset_now` (the operator-triggered one-tap reset-now — fires an automation resetting the upstream `recorder` integration's recording state + clears the per-camera offline guard + clears the storage-full guard).

RoamCore ships **no** native NVR engine. We RECIPE the well-understood upstream HA core `frigate` integration (since 2022.x — exposes the canonical NVR backend for Home Assistant automations; auto-discovers upstream cameras via the canonical upstream `frigate` discovery protocol since 2022.x) + the upstream `camera` platform (since 2022.x — exposes a GUI flow for the operator to add the upstream cameras via the HA UI under Settings → Devices & services → Integrations → Add Integration → Camera) + the HACS frigate add-on (the canonical upstream vendor-neutral local NVR add-on; auto-starts on HA boot; auto-configures the upstream HA core `frigate` integration to point at the local NVR) + the HA core `input_boolean` + `input_text` + `input_number` + `input_select` + `input_datetime` + `input_button` + `script` helper entities (since 2022.x — expose a GUI flow for the operator to add the helper entities from the HA UI under Settings → Helpers) + the upstream `recorder` integration (since 2022.x — the canonical recording service for Home Assistant automations) + the HA core `template:` sensor + binary_sensor wrappers (since 2022.x — wraps any upstream sensor state into a derived `sensor.*` entity) + the HA core `logbook` integration (since 2022.x — the canonical audit-log destination for Home Assistant automations) + the upstream `button:` domain helper (since 2022.x — exposes a GUI flow for the operator to trigger the reset-now button from the HA UI). The 12 `rc_security_*` + `rc_storage_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual NVR logic is provided by the upstream HA core `frigate` integration + the HACS frigate add-on (RoamCore does NOT fork any of these).

## The 5-step operator flow

- **Step 1 — Pick the NVR path** — the operator chooses ONE of the THREE upstream NVR paths documented in §3: Path A (HACS frigate add-on, recommended for most operators; local-only + auto-starts on HA boot + auto-configures the upstream HA core `frigate` integration to point at the local NVR; no vendor-specific credentials required); Path B (external / cloud NVR, for operators who already run an NVR off-box; the recipe documents how to wire the upstream HA core `frigate` integration to point at the external NVR + how to secure the connection with username / password); Path C (local container / VM NVR, for operators who want a Docker / Podman / LXC / VM NVR on the same Proxmox box or on a separate mini-PC; the recipe documents the vendor-neutral generic NVR wire-up).

- **Step 2 — Mount the camera URLs** — the operator configures `input_text.rc_security_camera_url` (a comma-separated list of camera URLs) + the optional `input_text.rc_security_camera_username` + the optional `input_text.rc_security_camera_password` (referenced indirectly via `secrets.yaml`) + `input_boolean.rc_security_camera_motion_enabled` (default TRUE for the recommended motion-enabled mode). The §4 operator flow walks the operator through populating the camera URLs + confirming the camera URLs are reachable.

- **Step 3 — Confirm the cameras are online** — the operator confirms `binary_sensor.rc_security_camera_online` reads TRUE (the §8.1 per-camera offline guard's canonical safety chip). The §5 operator flow walks the operator through confirming the cameras are online before the first recording.

- **Step 4 — Enable + start recording** — the operator flips `input_boolean.rc_storage_recording_enabled` ON (the upstream HA core `recorder` integration's master enable; the upstream `record` service exposes a GUI flow for the operator to record from the HA UI under Developer Tools → Services). The `binary_sensor.rc_security_camera_recording` surfaces "recording" / "idle" in the dashboard.

- **Step 5 — Audit + revert** — every camera state change + every `record` service call + every `record` event received writes an entry to `sensor.rc_security_camera_last_motion` (the resolved per-camera last-motion timestamp) + the `sensor.rc_security_camera_motion_mask` (the resolved per-camera motion-mask count) + the `sensor.rc_security_detection_person_count` + the `sensor.rc_security_detection_car_count` + the `sensor.rc_security_detection_animal_count` + the `sensor.rc_security_detection_package_count` (the resolved per-camera detection counts) + the HA core `logbook` (the canonical audit-log destination). The operator can revert at any time via `button.rc_storage_recording_reset_now`.

## Setup recipe (one-paragraph)

1. Decide which NVR path you want (most operators: Path A HACS frigate add-on; Path B external / cloud NVR if you already run an NVR off-box; Path C local container / VM NVR if you want a Docker / Podman / LXC / VM NVR on the same Proxmox box).
2. Install the HACS frigate add-on (Path A) or the external / cloud NVR (Path B) or the local container / VM NVR (Path C). The recipe documents all THREE paths in §3.
3. Install the upstream HA core `frigate` integration (auto-installed in every HA install + exposed via the HA UI under Settings → Devices & services → Integrations → Add Integration → Frigate).
4. Configure the camera URLs via `input_text.rc_security_camera_url` (a comma-separated list of camera URLs for Path A; your camera URLs for Path B / C).
5. Configure the camera username + password + motion detection toggle via `input_text.rc_security_camera_username` + `input_boolean.rc_security_camera_motion_enabled` (default empty username + TRUE motion for Path A).
6. Wire the operator-facing `binary_sensor.rc_security_camera_online` + `binary_sensor.rc_security_camera_recording` + `sensor.rc_security_camera_last_motion` + `sensor.rc_security_camera_motion_mask` + `sensor.rc_security_detection_person_count` + `sensor.rc_security_detection_car_count` + `sensor.rc_security_detection_animal_count` + `sensor.rc_security_detection_package_count` + `input_boolean.rc_storage_recording_enabled` + `sensor.rc_storage_recording_used` + `sensor.rc_storage_recording_free` + `sensor.rc_storage_recording_retention_today_count` contract tiles to point at the upstream HA core `frigate` integration's camera state + the `template:` wrappers + the `logbook` integration.
7. Wire the FIVE §8 MANDATORY automations (per-camera offline guard + cameras-online guard + per-camera motion-mask guard + storage-full guard + records-on-motion guard).
8. Verify: confirm the cameras are online → mount the camera URLs → enable → record a known test event via `record` from Developer Tools → Services → confirm the record fires + confirm `sensor.rc_security_camera_last_motion` updates → press `button.rc_storage_recording_reset_now` → confirm the recorder resets.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## The 12 `rc_security_*` + `rc_storage_*` contract tiles

### Cameras (4)

| Domain | Tile id | Purpose |
|---|---|---|
| `binary_sensor` | `rc_security_camera_online` | TRUE when the upstream `frigate` integration reports a connected camera state. The §8.1 per-camera offline guard's canonical safety chip + the §8.2 cameras-online guard's target. |
| `binary_sensor` | `rc_security_camera_recording` | Per-camera recording state (`recording` / `idle`). The §8.5 records-on-motion guard's target. |
| `sensor` | `rc_security_camera_last_motion` | Per-camera last-motion timestamp. Mirrors the upstream `frigate` integration's per-camera last-motion event. |
| `sensor` | `rc_security_camera_motion_mask` | Per-camera motion-mask count. The §8.3 per-camera motion-mask guard's target. |

### Detection (4)

| Domain | Tile id | Purpose |
|---|---|---|
| `sensor` | `rc_security_detection_person_count` | Resolved per-camera person-detection count aggregated across all cameras. Mirrors the upstream `frigate` integration's detection event log for `person` label. |
| `sensor` | `rc_security_detection_car_count` | Resolved per-camera car-detection count aggregated across all cameras. Mirrors the upstream `frigate` integration's detection event log for `car` label. |
| `sensor` | `rc_security_detection_animal_count` | Resolved per-camera animal-detection count aggregated across all cameras. Mirrors the upstream `frigate` integration's detection event log for `animal` label. |
| `sensor` | `rc_security_detection_package_count` | Resolved per-camera package-detection count aggregated across all cameras. Mirrors the upstream `frigate` integration's detection event log for `package` label. |

### Recording/storage (4)

| Domain | Tile id | Purpose |
|---|---|---|
| `input_boolean` | `rc_storage_recording_enabled` | Master enable for the upstream `recorder` integration's `record` service (default OFF for the recommended safe-default mode). The §8.5 records-on-motion guard fires whenever a `record` invocation arrives while this toggle is OFF. |
| `sensor` | `rc_storage_recording_used` | Per-camera recording storage used in gigabytes. Mirrors the upstream `recorder` integration's storage stat. |
| `sensor` | `rc_storage_recording_free` | Per-camera recording storage free in gigabytes. The §8.4 storage-full guard fires when this dips below 10 GB. |
| `sensor` | `rc_storage_recording_retention_today_count` | Per-camera recording retention today count. The §8.5 retentions-spin-down guard fires when this exceeds the operator's configured threshold. |

## The 5 §8 MANDATORY automations

- **§8.1 Per-camera offline guard** — fires when `binary_sensor.rc_security_camera_online` flips FALSE. Flips `binary_sensor.rc_security_camera_recording` to FALSE + flips `sensor.rc_security_camera_last_motion` to "unknown" + clears the per-camera detection counts to 0 + fires a critical notification warning the operator that the camera has gone offline.
- **§8.2 Cameras-online guard** — fires when `binary_sensor.rc_security_camera_online` flips TRUE. Clears the offline flag + flips `binary_sensor.rc_security_camera_recording` to TRUE + updates `sensor.rc_security_camera_last_motion` + updates the per-camera detection counts + fires a notification warning the operator that the cameras have come back online.
- **§8.3 Per-camera motion-mask guard** — fires when `sensor.rc_security_camera_motion_mask` flips to a non-zero value for an unexpected camera. Updates `sensor.rc_security_camera_motion_mask` + fires a critical notification warning the operator that the camera motion-mask has changed.
- **§8.4 Storage-full guard** — fires when `sensor.rc_storage_recording_free` dips below 10 GB. Flips `input_boolean.rc_storage_recording_enabled` to OFF + fires a critical notification warning the operator that the storage is full.
- **§8.5 Records-on-motion guard** — fires when ANY `script.*` / `automation.*` action tries to call the `record` service while `input_boolean.rc_storage_recording_enabled` is OFF. BLOCKS the record + flips `binary_sensor.rc_security_camera_recording` to FALSE + fires a critical notification warning the operator that recording is disabled.

## Why tier-b, not tier-a

Tier-a would require a RoamCore-owned NVR engine + integration code + integration tests against a real NVR engine bench (a controlled environment with canned fixture responses for camera-offline events + canned fixture responses for records-on-motion events + canned fixture responses for motion-mask changes events + canned fixture responses for storage-full events + canned fixture responses for retentions-spin-down events — all wired together in a controlled environment). We have no operator-side NVR engine bench on the CI to integration-test against (the bench requires the operator's chosen NVR path + canned fixture responses for the FIVE §8 automations). Tier-b is the honest tier: HA core `frigate` integration + the HACS frigate add-on + the upstream `camera` platform + HA core `input_boolean` + `input_text` + `input_number` + `input_select` + `input_datetime` + `input_button` + `script` helpers + HA core `recorder` + HA core `template:` + HA core `logbook` are all upstream / vendor / HACS code (not RoamCore-owned); the RoamCore wrapper is a thin upstream-entity-aggregation layer + the contract layer + the FIVE §8 MANDATORY automations + the operator-side NVR wire-up. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (`docs/catalog/cctv/frigate.md` — 669-byte tier-c claim stub, originally listed "CCTV with Frigate (spec + setup ideas): A single-page spec for a low-CPU CCTV system using Frigate + go2rtc, designed for predictable storage and practical van use" with no recipe + no contract + no automations + no install path — just a placeholder with an aspirational tier-c claim) is now superseded by this tier-b recipe connection. The legacy tier-c claim was honest-upstream-truth: RoamCore ships no native NVR engine in the repo today; the picker is honest and ships the contract layer + the recipe + the §8 automations + the operator-side NVR wire-up as tier-b.

## Files

- `connection.yml` — the source-of-truth tier-b manifest.
- `__init__.py` — `DOMAIN = "frigate"` marker for the audit.
- `README.md` — this file.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [`docs/catalog/cctv/frigate.md`](../../docs/catalog/cctv/frigate.md)
- Design doc (philosophy + NVR wire-up details + tier-a promotion outline): [`docs/design.md`](../../docs/design.md)
- HA core `frigate` integration (the canonical NVR backend umbrella): https://www.home-assistant.io/integrations/frigate/
- HA core `camera` platform (the canonical camera entity umbrella): https://www.home-assistant.io/integrations/camera/
- HA core `recorder` integration (the canonical recording service): https://www.home-assistant.io/integrations/recorder/
- HA core `input_boolean` integration (the canonical master-enable helper): https://www.home-assistant.io/integrations/input_boolean/
- HA core `input_text` integration (the canonical camera-URL + username helper): https://www.home-assistant.io/integrations/input_text/
- HA core `input_datetime` integration (the canonical session-expiry helper — not used here, but referenced for the pattern): https://www.home-assistant.io/integrations/input_datetime/
- HA core `input_button` integration (the canonical reset-now button helper): https://www.home-assistant.io/integrations/input_button/
- HA core `script:` integration (the canonical `record` wrapper): https://www.home-assistant.io/integrations/script/
- HA core `template:` integration (the canonical camera-online + camera-recording + last-motion + motion-mask + detection-count + storage-used + storage-free + retention-today-count derivation): https://www.home-assistant.io/integrations/template/
- HA core `logbook` integration (the canonical audit-log destination for the §8.1 + §8.2 + §8.3 + §8.4 + §8.5 guards): https://www.home-assistant.io/integrations/logbook/
- HACS prerequisites (the canonical install path for the HACS frigate add-on): https://hacs.xyz/docs/setup/prerequisites
- MQTT (the broker everything depends on — the upstream `frigate` integration's auto-discovery relies on the broker's `mqtt` integration for upstream discovery signals): `connections/mqtt/` (Wave 3 #34)
- Mode (the §8.3 per-camera motion-mask guard's mode-change cross-reference): `connections/mode/` (Wave 3 #61)
- Advanced-mode (the §8.5 records-on-motion guard's confirm-flag pattern): `connections/advanced-mode/` (Wave 3 #63)
- OpenClaw JSON API (the §8.1 per-camera offline guard's JSON payload cross-reference): `connections/openclaw-api/` (Wave 3 #64)
- Agent actions allowlist (the §8.5 records-on-motion guard's kill-switch cross-reference): `connections/agent-actions-allowlist/` (Wave 3 #65)
- Remote-access (the §8.5 records-on-motion guard's owner-identity check): `connections/remote-access/` (Wave 3 #58)
- DNS blocker (the §8.1 per-camera offline guard's network-reachability cross-reference): `connections/dns-blocker/` (Wave 3 #37)
- HVAC basics (the §8.4 storage-full guard's ventilation cross-reference): `connections/hvac-basics/` (Wave 3 #49)
- Fans (the §8.4 storage-full guard's cooling cross-reference): `connections/fans/` (Wave 3 #59)
- RoamCore entity naming: [`docs/reference/rc-entity-naming.md`](../../docs/reference/rc-entity-naming.md) (the `security` + `storage` subsystems were added by this slice)
