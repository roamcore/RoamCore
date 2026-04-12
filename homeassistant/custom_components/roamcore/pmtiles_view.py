from __future__ import annotations

import os

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant


class RoamcorePmtilesView(HomeAssistantView):
    """Serve PMTiles archives from /config/www/roamcore/pmtiles with Range support.

    Why this exists:
    - The frontend MapLibre style uses pmtiles:// URLs which rely on HTTP range requests.
    - Some HA deployments/proxies can behave oddly with large static files under /local.
    - Serving via an authenticated HA view keeps behavior consistent.
    """

    name = "api:roamcore:pmtiles"
    url = "/api/roamcore/pmtiles/{filename}"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request):
        # Defensive: only allow .pmtiles under the expected directory.
        fn = str(request.match_info.get("filename") or "").strip()
        if not fn.endswith(".pmtiles"):
            raise web.HTTPNotFound()
        if "/" in fn or "\\" in fn or ".." in fn:
            raise web.HTTPNotFound()

        path = self.hass.config.path("www", "roamcore", "pmtiles", fn)
        if not os.path.exists(path) or not os.path.isfile(path):
            raise web.HTTPNotFound()

        # aiohttp's FileResponse supports Range requests.
        return web.FileResponse(path)
