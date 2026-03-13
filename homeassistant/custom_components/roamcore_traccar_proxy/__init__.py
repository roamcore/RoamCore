"""RoamCore Traccar Proxy.

Provides a same-origin reverse proxy for the Traccar add-on web UI, so it can be
embedded in the Home Assistant mobile app without triggering local-network iframe
blocking.

Endpoint:
  /api/roamcore/traccar/<path>
"""

from __future__ import annotations

import asyncio
from typing import Final

from aiohttp import ClientError, ClientSession, web

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

DOMAIN: Final = "roamcore_traccar_proxy"

DEFAULT_UPSTREAM: Final = "http://127.0.0.1:8082"
PROXY_PREFIX: Final = "/api/roamcore/traccar"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the proxy."""

    session = async_get_clientsession(hass)

    async def handle(request: web.Request) -> web.StreamResponse:
        path = request.match_info.get("path", "")
        # Preserve trailing slash behavior
        upstream_url = f"{DEFAULT_UPSTREAM.rstrip('/')}/{path}" if path else f"{DEFAULT_UPSTREAM.rstrip('/')}/"
        if request.query_string:
            upstream_url = f"{upstream_url}?{request.query_string}"

        # Forward headers (drop hop-by-hop + host)
        headers = {k: v for k, v in request.headers.items() if k.lower() not in {
            "host",
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
        }}

        data = await request.read() if request.can_read_body else None

        try:
            async with session.request(
                request.method,
                upstream_url,
                headers=headers,
                data=data,
                allow_redirects=False,
            ) as resp:
                # Stream response back
                out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in {
                    "content-length",
                    "transfer-encoding",
                    "connection",
                }}

                body = await resp.read()
                return web.Response(status=resp.status, headers=out_headers, body=body)
        except (ClientError, asyncio.TimeoutError) as err:
            return web.Response(status=502, text=f"Traccar proxy error: {err}")

    # Register route
    hass.http.app.router.add_route("*", PROXY_PREFIX + "/{path:.*}", handle)
    hass.http.app.router.add_route("*", PROXY_PREFIX, handle)
    return True

