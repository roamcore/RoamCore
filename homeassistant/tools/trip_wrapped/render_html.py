import json
import os


ASSET_PATH = os.path.join(os.path.dirname(__file__), "assets", "trip_wrapped.min.html")


def render_html(wrapped: dict) -> str:
    with open(ASSET_PATH, "r", encoding="utf-8") as f:
        tpl = f.read()
    data = json.dumps(wrapped, ensure_ascii=False)
    return tpl.replace("/*__TRIP_WRAPPED_DATA__*/", f"window.TRIP_WRAPPED_DATA = {data};")

