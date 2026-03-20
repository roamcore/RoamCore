import base64
import os
import sqlite3
from aiohttp import web


def _transparent_png_bytes() -> bytes:
    # 1x1 transparent PNG
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5p6X8AAAAASUVORK5CYII="
    )


async def handle_tile(request: web.Request) -> web.Response:
    z = int(request.match_info["z"])
    x = int(request.match_info["x"])
    y = int(request.match_info["y"].split(".")[0])

    mbtiles = request.app["mbtiles_path"]
    default_tile = request.app["default_tile"]

    # MBTiles stores TMS y, so flip from XYZ
    tms_y = (1 << z) - 1 - y

    try:
        conn = sqlite3.connect(mbtiles)
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
        pass

    if default_tile == "transparent":
        return web.Response(body=_transparent_png_bytes(), content_type="image/png")
    raise web.HTTPNotFound()


async def handle_health(request: web.Request) -> web.Response:
    mbtiles = request.app["mbtiles_path"]
    ok = os.path.exists(mbtiles)
    return web.json_response({"ok": ok, "mbtiles_path": mbtiles})


def main():
    mbtiles_path = os.environ.get("MBTILES_PATH", "/config/roamcore/tiles.mbtiles")
    default_tile = os.environ.get("DEFAULT_TILE", "transparent")

    app = web.Application()
    app["mbtiles_path"] = mbtiles_path
    app["default_tile"] = default_tile

    app.router.add_get("/health", handle_health)
    app.router.add_get("/{z:\\d+}/{x:\\d+}/{y}.png", handle_tile)

    web.run_app(app, port=8000)


if __name__ == "__main__":
    main()

