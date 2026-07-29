import json
import os


ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
ASSET_CLASSIC = os.path.join(ASSET_DIR, "trip_wrapped.min.html")
ASSET_STORY = os.path.join(ASSET_DIR, "trip_wrapped_story.html")

# Privacy banner injected into every Trip Wrapped header. Matches the
# privacy contract declared in docs/feature-checklist.md (slice #20):
# trip data stays on-device by default, and any outbound HTTP must be
# loopback / local-CIDR unless the operator explicitly opts in.
PRIVACY_BANNER_TEXT = "Generated locally · no data sent off-device"
PRIVACY_BANNER_HTML = (
    '<div id="rc-trip-privacy-banner" '
    'role="note" aria-label="Privacy notice" '
    'style="position:relative;z-index:9999;'
    'padding:10px 16px;margin:0;'
    'background:rgba(110,231,255,0.10);'
    'border-bottom:1px solid rgba(110,231,255,0.25);'
    'color:rgba(255,255,255,0.85);'
    'font:600 12px/1.4 ui-sans-serif,system-ui,-apple-system,'
    'Segoe UI,Roboto,Helvetica,Arial;'
    'text-align:center;letter-spacing:0.02em;">'
    f'\U0001F512&nbsp;{PRIVACY_BANNER_TEXT}</div>'
)


def render_html(wrapped: dict, template: str = "classic") -> str:
    template = (template or "classic").strip().lower()
    path = ASSET_CLASSIC
    if template in ("story", "stories", "deck"):
        path = ASSET_STORY
    with open(path, "r", encoding="utf-8") as f:
        tpl = f.read()
    # Inject the privacy banner immediately after <body ...> if present,
    # otherwise after <html ...>. This keeps the existing template style
    # (no template mutation) and is idempotent.
    body_open = tpl.find("<body")
    if body_open != -1:
        # Insert just after the closing '>' of the <body ...> tag.
        close = tpl.find(">", body_open)
        if close != -1:
            tpl = tpl[: close + 1] + PRIVACY_BANNER_HTML + tpl[close + 1 :]
    else:
        html_open = tpl.find("<html")
        if html_open != -1:
            close = tpl.find(">", html_open)
            if close != -1:
                tpl = tpl[: close + 1] + PRIVACY_BANNER_HTML + tpl[close + 1 :]
        else:
            # Last-resort fallback: prepend.
            tpl = PRIVACY_BANNER_HTML + tpl

    # Safe JSON embedding: prevent closing the <script> tag if data contains "</script>".
    # (Also helps avoid accidental HTML parsing issues.)
    data = json.dumps(wrapped, ensure_ascii=False)
    # Conservative escaping for HTML/script contexts.
    data = (
        data.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    return tpl.replace("/*__TRIP_WRAPPED_DATA__*/", f"window.TRIP_WRAPPED_DATA = {data};")
