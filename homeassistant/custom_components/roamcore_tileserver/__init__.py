"""RoamCore Tile Server (offline).

Serves raster tiles from a local MBTiles file on the HA host so dashboards can
render maps fully offline without hitting public tile servers.

Endpoint (no HA auth, same-origin):
  /rc-tiles/{z}/{x}/{y}.png

MBTiles path:
  /config/roamcore/tiles.mbtiles

Notes:
- Uses XYZ requests from Leaflet; MBTiles stores TMS y so we flip y.
- If tiles are missing, returns a 1x1 transparent PNG (prevents ugly errors).
"""

from __future__ import annotations

import base64
import os
import sqlite3
from typing import Final

from aiohttp import web

from homeassistant.core import HomeAssistant

DOMAIN: Final = "roamcore_tileserver"
TILE_PREFIX: Final = "/rc-tiles"


def _transparent_png() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5p6X8AAAAASUVORK5CYII="
    )


def _mbtiles_path(hass: HomeAssistant) -> str:
    # Stored in HA config so it persists across upgrades.
    return hass.config.path("roamcore", "tiles.mbtiles")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    async def handle(request: web.Request) -> web.StreamResponse:
        z = int(request.match_info.get("z", "0"))
        x = int(request.match_info.get("x", "0"))
        y_raw = request.match_info.get("y", "0")
        y = int(str(y_raw).split(".")[0])

        path = _mbtiles_path(hass)
        if not os.path.exists(path):
            return web.Response(body=_transparent_png(), content_type="image/png")

        tms_y = (1 << z) - 1 - y
        try:
            conn = sqlite3.connect(path)
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=? LIMIT 1",
                    (z, x, tms_y),
                )
                row = cur.fetchone()
            finally:
                conn.close()
            if row and row[0]:
                return web.Response(body=row[0], content_type="image/png")
        except Exception:
            # best-effort: don't spam logs, just return transparent
            pass

        return web.Response(body=_transparent_png(), content_type="image/png")

    async def health(_: web.Request) -> web.StreamResponse:
        path = _mbtiles_path(hass)
        return web.json_response({"ok": os.path.exists(path), "mbtiles_path": path})

    hass.http.app.router.add_route("GET", TILE_PREFIX + "/health", health)
    hass.http.app.router.add_route("GET", TILE_PREFIX + "/{z:\\d+}/{x:\\d+}/{y}.png", handle)
    return True

