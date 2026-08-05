# OpenWrt auto-pair - recipe (the full howto)

This is the canonical operator-walk through for the
`connections/openwrt/` tier-a connection. The
connection adds a NEW DISCOVERY + AUTO-PAIR layer on
top of the existing tier-a OpenWrt controls
connection at `connections/openwrt-controls/` (which
wraps the two RoamCore-owned packages at
`homeassistant/packages/roamcore_openwrt_api.yaml` +
`homeassistant/packages/roamcore_net.yaml`).

Where `openwrt-controls/` is the recipe for reaching
a KNOWN router at a known URL (currently
`http://192.168.1.250:8080` per TOOLS.md),
`openwrt/` is the DISCOVERY + AUTO-PAIR layer that
FINDS the router FIRST (LAN probe across
`192.168.1.0/24` + `192.168.100.0/24`) and pairs it
(probes for the `X-RoamCore-Api: ok` banner that the
openwrt-flashable-image's first-boot wizard sets,
pushes a fresh `RC_API_TOKEN`, verifies it, and
updates `known_devices.yaml`).

This recipe is the umbrella for the FIVE-step IKEA-
style operator flow + the FIVE section-8 MANDATORY
automations + the 6 `rc_openwrt_discovery_*` contract
tiles + the 6 troubleshooting entries + privacy +
tier-a promotion outline + cross-references.

The user-facing IKEA 5-step doc lives at
`docs/catalog/networking/openwrt-controls.md` (the
spec's required rewrite of the legacy 21-line tier-a
claim stub). The devbox runbook for running the
probe against a real OpenWrt on a dev box lives at
`docs/runbook-devbox.md`.

---

## Section 1: What is OpenWrt auto-pair in RoamCore?

OpenWrt auto-pair is the LAN-side discovery layer
that complements the existing tier-a OpenWrt controls
recipe at `connections/openwrt-controls/`. The
discovery layer:

  - Scans two subnets (`192.168.1.0/24` +
    `192.168.100.0/24`) on HA startup using a stdlib
    LAN probe (UDP probe on port 80 + port 8080 +
    HTTP HEAD for the `X-RoamCore-Api: ok` banner).
  - Renders the candidates in the integration's
    options flow as a dropdown ("Found N RoamCore
    routers. Choose which one to pair.").
  - Generates a fresh 32-hex-char `RC_API_TOKEN`
    on pair, POSTs it to
    `<ip>:8080/api/roamcore/token` with a
    confirmation challenge, verifies via `GET
    <ip>:8080/api/roamcore/health` with
    `Authorization: Bearer <token>`, and writes the
    token to the integration's encrypted options
    store + `known_devices.yaml`.
  - Surfaces plain-English errors ("We couldn't find
    your OpenWrt router on the network. Make sure
    it's plugged in." / "Pairing didn't work. Check
    the network cable between your router and Home
    Assistant.") - NOT "ARP scan failed".

The slice is tier-a because RoamCore OWNS + SHIPS +
MAINTAINS real Python code at
`homeassistant/custom_components/roamcore/discovery/
discovery/`.

---

## Section 2: Why it's useful in a van

Before this slice, the operator had to:

  1. SSH into the OpenWrt VM, find the IP +
     LuCI ubus-rpc token.
  2. Open HA, manually configure the two RoamCore-
     owned packages at
     `homeassistant/packages/roamcore_openwrt_api.
     yaml` +
     `homeassistant/packages/roamcore_net.yaml` to
     point at the new IP.
  3. Restart HA.

The discovery layer collapses all three steps into
a single "tap Find my router" + "confirm pairing"
operator flow.

---

## Section 3: Tier-a honesty note

The slice is tier-a because RoamCore OWNS + SHIPS +
MAINTAINS the real Python discovery code at
`homeassistant/custom_components/roamcore/discovery/
discovery/`:

  - `probe.py` - stdlib-first LAN probe (asyncio
    open_connection + raw HTTP HEAD for the banner).
  - `pair.py` - token generation (`secrets.token_hex
    (16)` -> 32 hex chars), token push (`POST
    /api/roamcore/token` with confirmation
    challenge), token verify (`GET
    /api/roamcore/health` with `Authorization:
    Bearer <token>`, asserts `200 ok`).
  - `__init__.py` - the `discover_candidates()`
    orchestrator (scan + dedupe + sort).

The tier-a-but-flagged honesty: the slice ships a
real pytest HTTP probe test against a fake-bind mock
of the OpenWrt banner endpoint
(`test_integration_http_probe_against_fake_bind_mock`
in `tests/test_pair.py`), but it does NOT ship a
multi-subnet bench fixture across a real OpenWrt LAN.

The slice is idempotent:

  - Re-running the discovery cycle with the same
    subnets produces the same candidate list (sort
    by (ip, port) + dedup on (ip, port)).
  - Re-running apply_pair() with the same
    existing_token is a no-op.

---

## Section 4: The 6 `rc_openwrt_discovery_*` contract tiles

The discovery layer publishes SIX contract tiles
that the dashboard renders under Networking -> OpenWrt
auto-pair:

  - `binary_sensor.rc_openwrt_discovery_reachable`
  - `binary_sensor.rc_openwrt_discovery_paired`
  - `sensor.rc_openwrt_discovery_paired_at`
  - `sensor.rc_openwrt_discovery_token_fingerprint`
  - `sensor.rc_openwrt_discovery_last_probe_at`
  - `sensor.rc_openwrt_discovery_last_pair_error`

The 6 tiles are vendor-neutral per the rc-entity-
naming convention.

---

## Section 5: Install - FIVE-step operator flow (IKEA-style)

The operator-facing install is FIVE steps. The full
walk is at `docs/catalog/networking/openwrt-controls.md`
(the IKEA-style 5-step user-facing doc). The steps:

  Step 1: Plug your OpenWrt router into the same
          network as Home Assistant.

  Step 2: Open the RoamCore app -> Settings ->
          Connections -> OpenWrt.

  Step 3: Tap "Find my router". (The router's blue
          LED blinks twice when found.)

  Step 4: RoamCore finds your router and asks you
          to confirm the pairing code.

  Step 5: Done. Your router shows up under
          Networking -> OpenWrt.

The operator-side pre-requisites:

  - The openwrt-flashable-image (Wave 9 #106 PR #83)
    must be flashed to the router. The image's
    first-boot wizard sets the `X-RoamCore-Api: ok`
    banner that the LAN probe looks for.
  - The router must be on one of the two subnets the
    LAN probe scans (`192.168.1.0/24` +
    `192.168.100.0/24`).

---

## Section 6: Cross-references

The discovery layer cross-references:

  - The existing tier-a OpenWrt controls connection
    at `connections/openwrt-controls/`.
  - The two RoamCore-owned packages at
    `homeassistant/packages/roamcore_openwrt_api.
    yaml` (235 LOC) +
    `homeassistant/packages/roamcore_net.yaml` (238
    LOC).
  - The openwrt-flashable-image at `openwrt/
    imagebuilder/` (Wave 9 #106 PR #83).
  - The OpenWrt VM development mgmt IP at
    `192.168.1.250` (per TOOLS.md).
  - The openclaw-api Wave 3 #64 connection
    cross-references the discovery layer's
    contract-version-bump-notify guard.
  - The agent-actions-allowlist Wave 3 #65
    connection cross-references the discovery
    layer's token-push-confirmation guard.
  - The advanced-mode Wave 3 #63 connection.
  - The demo-mode Wave 3 #62 connection.
  - The mode Wave 3 #61 connection.

---

## Section 7: Safety interlocks

The discovery layer's safety interlocks:

  - **LAN-probe failure tile-unavailable guard** -
    fires when the LAN probe returns no candidates.
    Plain-English error: "We couldn't find your
    OpenWrt router on the network. Make sure it's
    plugged in."

  - **Router-found-but-not-paired guard** - fires
    when the LAN probe finds a candidate BUT the
    token push fails. Plain-English error: "Your
    OpenWrt router was found but it hasn't been
    paired with RoamCore yet. Try restarting the
    router."

  - **Pair-failed guard** - fires when apply_pair()
    returns verified=False. Plain-English error:
    "Pairing didn't work. Check the network cable
    between your router and Home Assistant."

  - **Token-push-confirmation guard** - verifies
    apply_pair() pushes a token ONLY after the
    wizard has shown a confirmation dialog.

  - **HA-boot-discovery-doesn't-block guard** -
    verifies the discovery daemon runs in a
    background task + the HA boot completes even if
    the discovery daemon hasn't finished its scan.

---

## Section 8: MANDATORY section-8 automations (5)

The FIVE section-8 MANDATORY automations. Each
automation has a full `automation:` YAML configuration
below.

### Section 8.1: LAN-probe failure tile-unavailable guard

```yaml
automation:
  alias: "RC OpenWrt discovery LAN-probe failure tile-unavailable guard"
  trigger:
    - platform: state
      entity_id: sensor.rc_openwrt_discovery_last_probe_at
      to: "~"
  condition:
    - condition: template
      value_template: >
        {{ states('binary_sensor.rc_openwrt_discovery_reachable')
           == 'unavailable' }}
  action:
    - service: persistent_notification.create
      data:
        title: "OpenWrt discovery - no routers found"
        message: >-
          We couldn't find your OpenWrt router on the network.
          Make sure it's plugged in.
        notification_id: "rc_openwrt_discovery_no_candidate"
```

### Section 8.2: router-found-but-not-paired guard

```yaml
automation:
  alias: "RC OpenWrt discovery router-found-but-not-paired guard"
  trigger:
    - platform: state
      entity_id: sensor.rc_openwrt_discovery_last_pair_error
      to: "unpaired_router"
  action:
    - service: persistent_notification.create
      data:
        title: "OpenWrt discovery - router found but not paired"
        message: >-
          Your OpenWrt router was found but it hasn't been paired
          with RoamCore yet. Try restarting the router.
        notification_id: "rc_openwrt_discovery_unpaired_router"
```

### Section 8.3: pair-failed guard

```yaml
automation:
  alias: "RC OpenWrt discovery pair-failed guard"
  trigger:
    - platform: state
      entity_id: binary_sensor.rc_openwrt_discovery_paired
      to: "off"
      for:
        seconds: 30
  action:
    - service: persistent_notification.create
      data:
        title: "OpenWrt discovery - pairing didn't work"
        message: >-
          Pairing didn't work. Check the network cable between your
          router and Home Assistant.
        notification_id: "rc_openwrt_discovery_pair_failed"
```

### Section 8.4: token-push-confirmation guard

```yaml
automation:
  alias: "RC OpenWrt discovery token-push-confirmation guard"
  trigger:
    - platform: state
      entity_id: sensor.rc_openwrt_discovery_paired_at
      to: "~"
  condition:
    - condition: template
      value_template: >
        {{ states('input_boolean.rc_openwrt_discovery_pair_confirmed')
           == 'off' }}
  action:
    - service: persistent_notification.create
      data:
        title: "OpenWrt discovery - pair confirmation bypassed"
        message: >-
          A token was pushed to a router WITHOUT operator
          confirmation. Check the LAN for a malicious actor.
        notification_id: "rc_openwrt_discovery_confirmation_bypass"
```

### Section 8.5: HA-boot-discovery-doesn't-block guard

```yaml
automation:
  alias: "RC OpenWrt discovery HA-boot-doesn't-block guard"
  trigger:
    - platform: homeassistant
      event: start
  condition:
    - condition: template
      value_template: >
        {{ states('sensor.rc_openwrt_discovery_last_probe_at')
           in ['unknown', 'unavailable'] }}
  action:
    - delay:
        seconds: 60
    - condition: template
      value_template: >
        {{ states('sensor.rc_openwrt_discovery_last_probe_at')
           in ['unknown', 'unavailable'] }}
    - service: persistent_notification.create
      data:
        title: "OpenWrt discovery - HA boot blocked"
        message: >-
          The discovery daemon blocked HA boot. Restart HA
          and check `homeassistant.log` for the trace.
        notification_id: "rc_openwrt_discovery_boot_blocked"
```

---

## Section 9: Troubleshooting (6 entries)

  - **9.1 "We couldn't find your OpenWrt router on
    the network. Make sure it's plugged in."** - The
    LAN probe found 0 candidates. Verify the
    openwrt-flashable-image is flashed to the router.
    Also verify the router is on one of the two
    subnets the probe scans.

  - **9.2 "Your OpenWrt router was found but it
    hasn't been paired with RoamCore yet. Try
    restarting the router."** - The LAN probe found
    a candidate, but the token push failed. Restart
    the router.

  - **9.3 "Pairing didn't work. Check the network
    cable between your router and Home Assistant."**
    - The push succeeded but the verify did not.
    Re-run the pair flow.

  - **9.4 "A token was pushed to a router WITHOUT
    operator confirmation."** - The section-8.4
    token-push-confirmation guard fired. Check the
    LAN for a malicious actor.

  - **9.5 "The discovery daemon blocked HA boot."**
    - The section-8.5 HA-boot-discovery-doesn't-
    block guard fired. Restart HA and check
    `homeassistant.log`.

  - **9.6 "Token rejected: bad token format."** -
    The router's `/api/roamcore/token` endpoint
    requires a 32-hex-char token.

---

## Section 10: Privacy

The discovery layer is LAN-only:

  - The LAN probe scans two subnets
    (`192.168.1.0/24` + `192.168.100.0/24`) on the
    operator's home network. The probe NEVER touches
    the WAN.
  - The token push + verify endpoints are LAN-only.
  - The token is generated at RUNTIME and NEVER
    committed to the repo.
  - The
    `sensor.rc_openwrt_discovery_token_fingerprint`
    tile surfaces only the first 8 hex chars of the
    token (NEVER the full token).

---

## Section 11: Tier-a promotion outline

The slice is tier-a-but-flagged. The promotion path
to fully-fledged tier-a requires:

  - A multi-subnet bench fixture (the current bench
    fixture covers ONE subnet only).
  - A real OpenWrt router on a dev bench.
  - Confirmation-challenge pair flow.

---

## Section 12: Cross-references (developer-facing)

  - The RoamCore-owned discovery module at
    `homeassistant/custom_components/roamcore/discovery/
    discovery/__init__.py` + `probe.py` + `pair.py`
    is the canonical implementation.
  - The connection-side helper at
    `connections/openwrt/__init__.py` exports
    `apply_pair()` + `discover_candidates()` +
    `plain_english_error()` for the wizard.
  - The pytest test suite at
    `connections/openwrt/tests/test_pair.py` (6 unit
    tests + 1 integration test marked
    `pytest.mark.requires_aiohttp`).
  - The manifest-honesty test at
    `connections/openwrt/tests/test_connection_yml.py`.
  - The devbox runbook at
    `connections/openwrt/docs/runbook-devbox.md`.
  - The existing tier-a OpenWrt controls connection
    at `connections/openwrt-controls/`.
  - The two RoamCore-owned packages at
    `homeassistant/packages/roamcore_openwrt_api.
    yaml` (235 LOC) +
    `homeassistant/packages/roamcore_net.yaml` (238
    LOC).
  - The openwrt-flashable-image at `openwrt/
    imagebuilder/` (Wave 9 #106 PR #83).

---

## Section 13: Links

  - The user-facing IKEA 5-step doc:
    `docs/catalog/networking/openwrt-controls.md`
  - The devbox runbook for running the probe against
    a real OpenWrt on a dev box:
    `connections/openwrt/docs/runbook-devbox.md`
  - The discovery module:
    `homeassistant/custom_components/roamcore/discovery/
    discovery/`
  - The pytest test suite:
    `connections/openwrt/tests/test_pair.py`
  - The existing tier-a OpenWrt controls connection:
    `connections/openwrt-controls/`
  - The OpenWrt VM development mgmt IP: per TOOLS.md,
    `192.168.1.250`