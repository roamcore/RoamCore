"""Pair module - token generation + push + verify.

  1. Generate fresh RC_API_TOKEN (32 chars from secrets.token_hex)
  2. POST it to /api/roamcore/token
  3. Verify via GET /api/roamcore/health with Bearer token

Doctrine: never raise on network errors; plain-English errors instead.
"""

from __future__ import annotations

import asyncio
import logging
import secrets

_LOGGER = logging.getLogger(__name__)

# Token length. secrets.token_hex(16) yields 32 hex chars.
TOKEN_HEX_LENGTH = 32

# Routes on the RoamCore-flashed router.
TOKEN_PUSH_PATH = "/api/roamcore/token"
HEALTH_PATH = "/api/roamcore/health"

# Default timeout for token push + verify HTTP calls.
DEFAULT_TIMEOUT_S = 5.0


def generate_token() -> str:
    """Return a fresh 32-hex-char RC_API_TOKEN.

    Generated at RUNTIME, never committed to repo.
    """
    return secrets.token_hex(TOKEN_HEX_LENGTH // 2)


async def _http_post(
    ip: str,
    port: int,
    path: str,
    body: bytes,
    headers: dict[str, str] | None = None,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> tuple[int, bytes]:
    """Tiny HTTP/1.1 POST helper. Returns (status, body).

    Returns (-1, b"") on connection / timeout errors.
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout_s,
        )
    except (asyncio.TimeoutError, OSError):
        return (-1, b"")

    try:
        hdrs = {
            "Host": f"{ip}:{port}",
            "User-Agent": "RoamCore-Discovery/1.0",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Connection": "close",
        }
        if headers:
            hdrs.update(headers)
        request = (
            f"POST {path} HTTP/1.1\r\n"
            + "".join(f"{k}: {v}\r\n" for k, v in hdrs.items())
            + "\r\n"
        ).encode("ascii") + body
        writer.write(request)
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

        raw = bytes(buf).decode("iso-8859-1", errors="replace")
        status = _parse_status(raw)
        return (status, bytes(buf))
    except (asyncio.TimeoutError, OSError, ValueError):
        return (-1, b"")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def _http_get(
    ip: str,
    port: int,
    path: str,
    headers: dict[str, str] | None = None,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> tuple[int, bytes]:
    """Tiny HTTP/1.1 GET helper. Returns (status, body)."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout_s,
        )
    except (asyncio.TimeoutError, OSError):
        return (-1, b"")

    try:
        hdrs = {
            "Host": f"{ip}:{port}",
            "User-Agent": "RoamCore-Discovery/1.0",
            "Connection": "close",
        }
        if headers:
            hdrs.update(headers)
        request = (
            f"GET {path} HTTP/1.1\r\n"
            + "".join(f"{k}: {v}\r\n" for k, v in hdrs.items())
            + "\r\n"
        ).encode("ascii")
        writer.write(request)
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

        raw = bytes(buf).decode("iso-8859-1", errors="replace")
        status = _parse_status(raw)
        return (status, bytes(buf))
    except (asyncio.TimeoutError, OSError, ValueError):
        return (-1, b"")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


def _parse_status(head: str) -> int:
    """Parse HTTP/1.1 200 OK -> 200. Returns -1 on bad input."""
    first = head.split("\r\n", 1)[0]
    parts = first.split(" ", 2)
    if len(parts) < 2:
        return -1
    try:
        return int(parts[1])
    except ValueError:
        return -1


async def push_token(
    ip: str,
    port: int,
    token: str,
    *,
    challenge: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> bool:
    """POST the token to <ip>:<port>/api/roamcore/token.

    Returns True on HTTP 200 (push accepted) or 304
    (idempotent - token already in place).
    Returns False on any other status or network error.
    Never raises.
    """
    import json

    body_dict = {"token": token}
    if challenge is not None:
        body_dict["challenge"] = challenge
    body = json.dumps(body_dict).encode("utf-8")
    status, _ = await _http_post(
        ip, port, TOKEN_PUSH_PATH, body, timeout_s=timeout_s
    )
    return status in (200, 304)


async def verify_token(
    ip: str,
    port: int,
    token: str,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> bool:
    """Verify the token by GETting <ip>:<port>/api/roamcore/health.

    Status must be 200 AND body must contain "200 ok".
    Never raises.
    """
    status, body = await _http_get(
        ip,
        port,
        HEALTH_PATH,
        headers={"Authorization": f"Bearer {token}"},
        timeout_s=timeout_s,
    )
    if status != 200:
        return False
    return b"200 ok" in body