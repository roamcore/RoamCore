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

from aiohttp import web
from aiohttp.client_exceptions import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

DOMAIN: Final = "roamcore_traccar_proxy"

DEFAULT_UPSTREAM: Final = "http://127.0.0.1:8082"
PROXY_PREFIX: Final = "/api/roamcore/traccar"

_cached_session_cookie: str | None = None
_cached_admin_email: str | None = None
_cached_admin_password: str | None = None


def _rewrite_text_payload(payload: bytes) -> bytes:
    """Rewrite absolute-root asset paths to stay inside the proxy prefix.

    Traccar serves many assets with absolute paths like `/modern/app.js`.
    When embedded via an HA route prefix, the browser would request
    `https://ha/modern/app.js` (wrong) instead of
    `https://ha/api/roamcore/traccar/modern/app.js` (correct).

    This is a best-effort string rewrite for HTML/CSS/JS responses.
    """

    try:
        s = payload.decode("utf-8", errors="ignore")
        # Common HTML attrs
        s = s.replace('="/', f'="{PROXY_PREFIX}/')
        s = s.replace("='/", f"='{PROXY_PREFIX}/")
        # CSS url(/...)
        s = s.replace("url(/", f"url({PROXY_PREFIX}/")
        return s.encode("utf-8")
    except Exception:
        return payload


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the proxy."""

    session = async_get_clientsession(hass)

    def _load_traccar_admin_secrets() -> None:
        """Load Traccar admin credentials from /config/secrets.yaml (best-effort)."""

        global _cached_admin_email, _cached_admin_password
        if _cached_admin_email and _cached_admin_password:
            return
        try:
            secrets_path = hass.config.path("secrets.yaml")
            text = ""
            with open(secrets_path, "r", encoding="utf-8") as f:
                text = f.read()
            import re

            m1 = re.search(r"^roamcore_traccar_admin_email:\s*\"?([^\"\n]+)\"?$", text, re.M)
            m2 = re.search(r"^roamcore_traccar_admin_password:\s*\"?([^\"\n]+)\"?$", text, re.M)
            if m1 and m2:
                _cached_admin_email = m1.group(1).strip()
                _cached_admin_password = m2.group(1).strip()
        except Exception:
            return

    async def _ensure_logged_in() -> str | None:
        """Ensure we have a Traccar JSESSIONID cookie.

        This makes the embedded UI effectively "auto-login" for HA users.
        """

        global _cached_session_cookie
        if _cached_session_cookie:
            return _cached_session_cookie

        _load_traccar_admin_secrets()
        if not (_cached_admin_email and _cached_admin_password):
            return None

        try:
            async with session.post(
                f"{DEFAULT_UPSTREAM.rstrip('/')}/api/session",
                data={"email": _cached_admin_email, "password": _cached_admin_password},
                allow_redirects=False,
            ) as resp:
                if resp.status != 200:
                    return None
                sc = resp.headers.getall("Set-Cookie", [])
                # Find JSESSIONID
                for v in sc:
                    if v.startswith("JSESSIONID="):
                        _cached_session_cookie = v
                        return _cached_session_cookie
        except Exception:
            return None
        return None

    async def _fetch_upstream(
        method: str,
        url: str,
        headers: dict,
        data: bytes | None,
    ):
        """Wrapper around aiohttp request to make retry logic clearer."""
        return session.request(
            method,
            url,
            headers=headers,
            data=data,
            allow_redirects=False,
        )

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
            # Never forward HA auth headers to Traccar.
            "authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
        }}

        # Best-effort auto-login / session refresh:
        # - If the browser doesn't have a session, establish one using stored admin creds.
        # - If the browser *does* have a session but Traccar rejects it (401/403),
        #   refresh the cached cookie and retry once.
        browser_cookie = request.headers.get("Cookie", "") or ""
        sent_cookie = None
        if "JSESSIONID=" not in browser_cookie:
            js = await _ensure_logged_in()
            if js:
                sent_cookie = js.split(";", 1)[0]
                headers["Cookie"] = sent_cookie

        data = await request.read() if request.can_read_body else None

        try:
            # First attempt
            async with await _fetch_upstream(request.method, upstream_url, headers, data) as resp:
                # Stream response back
                out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in {
                    "content-length",
                    "transfer-encoding",
                    "connection",
                    # aiohttp may transparently decompress; don't forward encoding.
                    "content-encoding",
                }}

                # If upstream says unauthorized, retry once by refreshing the cached cookie.
                if resp.status in (401, 403):
                    global _cached_session_cookie
                    _cached_session_cookie = None
                    js2 = await _ensure_logged_in()
                    if js2:
                        headers2 = dict(headers)
                        sent_cookie = js2.split(";", 1)[0]
                        headers2["Cookie"] = sent_cookie
                        async with await _fetch_upstream(request.method, upstream_url, headers2, data) as resp2:
                            out_headers = {k: v for k, v in resp2.headers.items() if k.lower() not in {
                                "content-length",
                                "transfer-encoding",
                                "connection",
                                "content-encoding",
                            }}
                            body = await resp2.read()

                            # Rewrite redirect locations back into the proxy prefix
                            loc = resp2.headers.get("Location")
                            if loc and loc.startswith("/"):
                                out_headers["Location"] = f"{PROXY_PREFIX}{loc}"

                            ctype = (resp2.headers.get("Content-Type") or "").lower()
                            if any(t in ctype for t in ("text/html", "text/css", "javascript")):
                                body = _rewrite_text_payload(body)

                            # If we established a session cookie, set it for the browser too.
                            if "JSESSIONID=" not in browser_cookie and _cached_session_cookie:
                                out_headers["Set-Cookie"] = _cached_session_cookie

                            return web.Response(status=resp2.status, headers=out_headers, body=body)

                # If we established a session cookie, set it for the browser too
                if "JSESSIONID=" not in browser_cookie:
                    if _cached_session_cookie:
                        out_headers["Set-Cookie"] = _cached_session_cookie

                body = await resp.read()

                # Rewrite redirect locations back into the proxy prefix
                loc = resp.headers.get("Location")
                if loc and loc.startswith("/"):
                    out_headers["Location"] = f"{PROXY_PREFIX}{loc}"

                ctype = (resp.headers.get("Content-Type") or "").lower()
                if any(t in ctype for t in ("text/html", "text/css", "javascript")):
                    body = _rewrite_text_payload(body)

                return web.Response(status=resp.status, headers=out_headers, body=body)
        except (ClientError, asyncio.TimeoutError) as err:
            return web.Response(status=502, text=f"Traccar proxy error: {err}")

    # Register route
    hass.http.app.router.add_route("*", PROXY_PREFIX + "/{path:.*}", handle)
    hass.http.app.router.add_route("*", PROXY_PREFIX, handle)
    return True
