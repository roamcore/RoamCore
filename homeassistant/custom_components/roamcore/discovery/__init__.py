"""RoamCore LAN discovery - auto-pair helpers for RoamCore-flashed routers.

LAN-side companion to the existing RoamCore OpenWrt
packages at
`homeassistant/packages/roamcore_openwrt_api.yaml` +
`homeassistant/packages/roamcore_net.yaml`. Where
the two packages reach a KNOWN router at a known URL
(currently `http://192.168.1.250:8080` per TOOLS.md),
the discovery module finds the router FIRST and pairs
it (probes `192.168.1.0/24` + `192.168.100.0/24`,
identifies candidates that respond with the
`X-RoamCore-Api: ok` banner that the openwrt-
flashable-image's first-boot wizard sets, pushes a
fresh `RC_API_TOKEN`, verifies it, and returns the
candidate list to the wizard).

Sub-modules:
    probe - stdlib LAN probe (asyncio open_connection
            + raw HTTP HEAD for the banner).
    pair  - token generation (32 hex chars from
            secrets.token_hex) + token push (POST
            /api/roamcore/token) + token verification
            (GET /api/roamcore/health with
            Authorization: Bearer <token>).

Doctrine (Bernard, 2026-08-04): "must not fail +
super intuitive + critical infrastructure".
"""

from __future__ import annotations

import logging
from typing import Iterable

from .pair import (
    generate_token,
    push_token,
    verify_token,
)
from .probe import (
    BANNER_HEADER,
    BANNER_VALUE,
    DEFAULT_PORTS,
    DEFAULT_TIMEOUT_S,
    Candidate,
    probe_ip,
    scan_subnet,
)

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "BANNER_HEADER",
    "BANNER_VALUE",
    "DEFAULT_PORTS",
    "DEFAULT_TIMEOUT_S",
    "Candidate",
    "discover_candidates",
    "generate_token",
    "probe_ip",
    "push_token",
    "scan_subnet",
    "verify_token",
]


async def discover_candidates(
    subnets: Iterable[str],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    ports: tuple[int, ...] = DEFAULT_PORTS,
    max_concurrent: int = 32,
) -> list[Candidate]:
    """Scan every subnet in `subnets` and return a
    deduplicated list of router candidates.

    A candidate is any IP that responds on any of
    `ports` with the `X-RoamCore-Api: ok` banner
    within `timeout_s`. The candidates are deduplicated
    on the (ip, port) tuple and returned sorted by
    (ip, port) for stable ordering (idempotent).

    Plain-English error contract: this function NEVER
    raises on a missing router. If no candidate is
    found, it returns `[]` and the wizard surfaces
    the user-facing "We couldn't find your OpenWrt
    router on the network. Make sure it's plugged
    in." tile.
    """
    seen: set[tuple[str, int]] = set()
    out: list[Candidate] = []

    for cidr in subnets:
        try:
            found = await scan_subnet(
                cidr,
                ports=ports,
                timeout_s=timeout_s,
                max_concurrent=max_concurrent,
            )
        except Exception as exc:
            _LOGGER.warning(
                "discovery: subnet scan for %s failed (%s); "
                "skipping and continuing with remaining subnets",
                cidr,
                exc,
            )
            continue
        for cand in found:
            key = (cand.ip, cand.port)
            if key in seen:
                continue
            seen.add(key)
            out.append(cand)

    out.sort(key=lambda c: (c.ip, c.port))
    return out