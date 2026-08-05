# OpenWrt auto-pair - devbox runbook

This runbook walks a developer through running the
OpenWrt auto-pair probe against a REAL OpenWrt
router on a dev box (NOT against the fake-bind mock
in the pytest integration test).

The pytest integration test
(`connections/openwrt/tests/test_pair.py::
test_integration_http_probe_against_fake_bind_mock`)
spins up an aiohttp test server on `127.0.0.1:18080`
returning the `X-RoamCore-Api: ok` banner. That test
exercises the discovery + pair flow against a fake-
bind mock. This runbook exercises the SAME flow
against a REAL OpenWrt router on the operator's dev
box.

---

## Section 1: Pre-requisites

  1. A real OpenWrt router on the dev box's LAN.
     The router must be flashed with the
     `openwrt-flashable-image` (Wave 9 #106 PR #83).
     The image's first-boot wizard sets the
     `X-RoamCore-Api: ok` banner that the LAN
     probe looks for.

  2. The router must be on one of the two subnets
     the LAN probe scans:
     - `192.168.1.0/24` (the home LAN - most
       common; the OpenWrt VM at `192.168.1.250`
       per TOOLS.md lives here).
     - `192.168.100.0/24` (the dev VLAN).

  3. The openwrt-flashable-image's first-boot wizard
     must have completed (about 30 s). Verify with:

         curl -v http://192.168.1.250:8080/

     The response headers must include
     `X-RoamCore-Api: ok`.

  4. The dev box must have Python 3.9+ + aiohttp
     installed.

         pip install aiohttp

---

## Section 2: Running the LAN probe from the dev box

The discovery module is a standalone Python module -
it does NOT require Home Assistant. Run the probe
from the dev box's shell:

```python
import asyncio
from homeassistant.custom_components.roamcore.discovery import discover_candidates

async def main():
    candidates = await discover_candidates(
        subnets=["192.168.1.0/24"],
        timeout_s=3.0,
    )
    for c in candidates:
        print(f"  {c.ip}:{c.port}  banner={c.banner!r}")

asyncio.run(main())
```

Expected output (when the OpenWrt router is at
`192.168.1.250:8080` and the first-boot wizard has
completed):

```
  192.168.1.250:8080  banner='ok'
```

If the output is empty, the router is NOT
responding with the banner. Verify with `curl -v
http://192.168.1.250:8080/` (the response headers
must include `X-RoamCore-Api: ok`).

The probe completes in <10 s for /24.

---

## Section 3: Running the pair flow from the dev box

The `apply_pair()` helper is the full pair flow:
generate a fresh token, POST it to
`/api/roamcore/token`, verify via
`/api/roamcore/health`, write the token to the
integration options + `known_devices.yaml`.

```python
import asyncio
from pathlib import Path
from connections.openwrt import apply_pair

async def main():
    result = await apply_pair(
        ip="192.168.1.250",
        port=8080,
        options={"url": "http://192.168.1.250:8080"},
        existing_token=None,
        known_devices_path=Path("/tmp/known_devices.yaml"),
    )
    print(f"  token={result.token!r}")
    print(f"  verified={result.verified}")
    print(f"  cached={result.cached}")

asyncio.run(main())
```

Expected output:

```
  token='a3f7b2c1...32 hex chars...'
  verified=True
  cached=False
```

---

## Section 4: Re-running with the same token (idempotency check)

```python
import asyncio
from connections.openwrt import apply_pair

async def main():
    result1 = await apply_pair(
        ip="192.168.1.250",
        port=8080,
        existing_token=None,
    )
    assert result1.verified is True
    assert result1.cached is False

    result2 = await apply_pair(
        ip="192.168.1.250",
        port=8080,
        existing_token=result1.token,
    )
    assert result2.verified is True
    assert result2.cached is True
    assert result2.token == result1.token

    print("Idempotency check passed.")

asyncio.run(main())
```

---

## Section 5: Running the pytest test suite

```bash
cd /home/bernard/clawd/RoamCore
python3 -m pytest connections/openwrt/tests/ -v
```

Expected output (with aiohttp installed):

```
connections/openwrt/tests/test_connection_yml.py ... 7 PASSED
connections/openwrt/tests/test_pair.py ... 7 PASSED
============================== 14 passed in 0.5s ===============================
```

The integration test
(`test_integration_http_probe_against_fake_bind_mock`)
spins up an aiohttp test server on `127.0.0.1:18080`
returning the `X-RoamCore-Api: ok` banner, configures
the discovery module to scan ONLY that IP, asserts
the candidate list contains it, and asserts
`apply_pair()` pushes a 32-hex-char token to
`/api/roamcore/token` + verifies via
`/api/roamcore/health`.

---

## Section 6: Running the check.sh chain

```bash
cd /home/bernard/clawd/RoamCore
bash scripts/check.sh --core-only
```

---

## Section 7: Troubleshooting

  - **Probe returns 0 candidates** - Verify the
    router is flashed with the openwrt-flashable-
    image. Verify the router is on one of the two
    subnets. Verify the first-boot wizard has
    completed (`curl -v http://<router-ip>:8080/`
    should return `X-RoamCore-Api: ok`).

  - **Token push fails** - Verify the router is
    accepting POSTs to `/api/roamcore/token`:

        curl -v -X POST http://192.168.1.250:8080/api/roamcore/token \
             -H "Content-Type: application/json" \
             -d '{"token": "<32-hex-char-token>"}'

  - **Verify fails** - Verify the router is
    accepting GETs to `/api/roamcore/health` with
    a Bearer token:

        curl -v -H "Authorization: Bearer <token>" \
             http://192.168.1.250:8080/api/roamcore/health

  - **Probe takes >10 s for /24** - Reduce the
    `timeout_s` parameter (default 3.0 s per IP).

  - **pytest integration test SKIPPED** - Install
    aiohttp: `pip install aiohttp`.

---

## Section 8: Cross-references

  - The discovery module:
    `homeassistant/custom_components/roamcore/
    discovery/__init__.py` + `probe.py` + `pair.py`
  - The connection-side helper:
    `connections/openwrt/__init__.py`
  - The pytest test suite:
    `connections/openwrt/tests/test_pair.py` +
    `tests/conftest.py` +
    `tests/test_connection_yml.py`
  - The recipe (the operator-facing howto):
    `connections/openwrt/docs/recipe.md`
  - The user-facing IKEA 5-step doc:
    `docs/catalog/networking/openwrt-controls.md`
  - The existing tier-a OpenWrt controls connection:
    `connections/openwrt-controls/`
  - The openwrt-flashable-image (Wave 9 #106):
    `openwrt/imagebuilder/`
  - The OpenWrt VM development mgmt IP: per TOOLS.md,
    `192.168.1.250`