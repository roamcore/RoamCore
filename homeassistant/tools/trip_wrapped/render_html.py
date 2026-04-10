import json
import os


ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
ASSET_CLASSIC = os.path.join(ASSET_DIR, "trip_wrapped.min.html")
ASSET_STORY = os.path.join(ASSET_DIR, "trip_wrapped_story.html")


def render_html(wrapped: dict, template: str = "classic") -> str:
    template = (template or "classic").strip().lower()
    path = ASSET_CLASSIC
    if template in ("story", "stories", "deck"):
        path = ASSET_STORY
    with open(path, "r", encoding="utf-8") as f:
        tpl = f.read()
    # Safe JSON embedding: prevent closing the <script> tag if data contains "</script>".
    # (Also helps avoid accidental HTML parsing issues.)
    data = json.dumps(wrapped, ensure_ascii=False).replace("<", "\\u003c")
    return tpl.replace("/*__TRIP_WRAPPED_DATA__*/", f"window.TRIP_WRAPPED_DATA = {data};")
