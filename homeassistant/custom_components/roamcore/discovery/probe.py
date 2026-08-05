"""LAN probe - find RoamCore-flashed routers on the local network.

The probe module is stdlib-first: it uses asyncio
open_connection + raw HTTP HEAD to probe for the
banner.

Banner contract:

    HTTP/1.1 200 OK
    X-RoamCore-Api: ok

The `X-RoamCore-Api: ok` header is set by the
openwrt-flashable-image's first-boot wizard (Wave 9
#106 PR #83).
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

BANNER_HEADER = "X-RoamCore-Api"
BANNER_VALUE = "ok"

# Default ports to probe.
DEFAULT_PORTS: tuple[int, ...] = (80, 8080)

# Default per-IP timeout. 3 s is long enough for a
# slow router first-boot but short enough that a /24
# finishes well under 10 s.
DEFAULT_TIMEOUT_S = 3.0


@dataclass(frozen=True)
class Candidate:
    """A discovered router candidate."""

    ip: str
    port: int
    banner: str

    def to_dict(self) -> dict:
        return {"ip": self.ip, "port": self.port, "banner": self.banner}


async def probe_ip(
    ip: str,
    port: int,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> Candidate | None:
    """Probe a single (ip, port) and return a Candidate
    if the banner matches, else None.

    Never raises.
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout_s,
        )
    except (asyncio.TimeoutError, OSError):
        return None

    try:
        request = (
            f"HEAD / HTTP/1.1\r\n"
            f"Host: {ip}:{port}\r\n"
            f"User-Agent: RoamCore-Discovery/1.0\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )
        writer.write(request.encode("ascii"))
        await writer.drain()

        buf = bytearray()
        while len(buf) < 8192:
            chunk = await asyncio.wait_for(
                reader.read(512),
                timeout=timeout_s,
            )
            if not chunk:
                break
            buf.extend(chunk)
            if b"\r\n\r\n" in buf:
                break

        head = bytes(buf).decode("iso-8859-1", errors="replace")
        headers: dict[str, str] = {}
        for line in head.split("\r\n"):
            if not line or ":" not in line:
                continue
            name, _, value = line.partition(":")
            headers[name.strip().lower()] = value.strip()

        banner = headers.get(BANNER_HEADER.lower())
        if banner and banner.lower() == BANNER_VALUE.lower():
            return Candidate(ip=ip, port=port, banner=banner)
        return None
    except (asyncio.TimeoutError, OSError, ValueError):
        return None
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def scan_subnet(
    cidr: str,
    *,
    ports: tuple[int, ...] = DEFAULT_PORTS,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_concurrent: int = 32,
) -> list[Candidate]:
    """Scan every host in `cidr` and return a list of
    router candidates.

    `cidr` is an IPv4 network in CIDR notation, e.g.
    `"192.168.1.0/24"` or `"192.168.100.0/24"`.
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        _LOGGER.warning(
            "discovery: invalid CIDR %r; skipping subnet", cidr
        )
        return []

    hosts = list(network.hosts())
    if not hosts:
        return []

    sem = asyncio.Semaphore(max_concurrent)

    async def _probe_one(ip, port):
        async with sem:
            return await probe_ip(str(ip), port, timeout_s=timeout_s)

    tasks = [
        asyncio.create_task(_probe_one(ip, port))
        for ip in hosts
        for port in ports
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    out: list[Candidate] = []
    for r in results:
        if isinstance(r, Candidate):
            out.append(r)
    out.sort(key=lambda c: (c.ip, c.port))
    return out