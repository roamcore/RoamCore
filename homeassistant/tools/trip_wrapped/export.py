#!/usr/bin/env python3

import argparse
import json
import os
from datetime import datetime, timezone

from build_wrapped import build_wrapped
from render_html import render_html
from traccar_client import TraccarClient


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    # Optional: if omitted (or passed as unknown/unavailable from HA templates),
    # we will fall back to /config/secrets.yaml (keys: roamcore_traccar_admin_email/password)
    p.add_argument("--username")
    p.add_argument("--password")
    p.add_argument("--device-id", type=int, required=True)
    p.add_argument("--from", dest="from_ts", required=True)
    p.add_argument("--to", dest="to_ts", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-html", required=True)
    p.add_argument("--title", default="Trip Wrapped")
    return p.parse_args()


def _load_secrets() -> dict[str, str]:
    try:
        p = "/config/secrets.yaml"
        if not os.path.exists(p):
            return {}
        with open(p, "r", encoding="utf-8") as f:
            text = f.read()
        import re

        out: dict[str, str] = {}
        for key in (
            "roamcore_traccar_admin_email",
            "roamcore_traccar_admin_password",
            "roamcore_traccar_user_token",
        ):
            m = re.search(rf"^{key}:\s*\"?([^\"\n]+)\"?$", text, re.M)
            if m:
                out[key] = m.group(1).strip()
        return out
    except Exception:
        return {}


def _norm(v: str | None) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in ("unknown", "unavailable", "None"):
        return None
    return s


def main():
    a = parse_args()

    user = _norm(a.username)
    pw = _norm(a.password)

    # Preferred (for RoamCore): use the Traccar user token (works even when the
    # email/password session endpoint is broken) so we don't need to store creds.
    trips = None
    pref_err = None
    try:
        sec = _load_secrets()
        tok = sec.get("roamcore_traccar_user_token")
        if tok:
            tok_client = TraccarClient.direct_user_token(base_url=a.base_url, user_token=tok)
            trips = tok_client.get_trips(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
    except Exception as e:
        pref_err = e

    # Secondary preference: HA proxy (no direct token required)
    ha_client = None
    if trips is None:
        try:
            ha_client = TraccarClient.ha_supervisor_proxy(base_url="http://supervisor/core")
            trips = ha_client.get_trips(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
        except Exception as e:
            pref_err = e

    if trips is None:
        # Fallback: direct Traccar Basic Auth using args or secrets.yaml
        if not (user and pw):
            sec = _load_secrets()
            user = user or sec.get("roamcore_traccar_admin_email")
            pw = pw or sec.get("roamcore_traccar_admin_password")
        if not (user and pw):
            raise SystemExit(
                "Trip Wrapped export failed. Preferred token/proxy methods were unavailable and Traccar credentials are missing. "
                "Provide --username/--password or set roamcore_traccar_admin_email/password in /config/secrets.yaml. "
                f"Last error: {pref_err}"
            )
        client = TraccarClient.direct_basic(base_url=a.base_url, username=user, password=pw)
        trips = client.get_trips(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)

    # Best-effort: pull a full-journey route polyline (hero map) plus a top-trip
    # route (optional secondary).
    journey_route = None
    top_trip_route = None
    try:
        # Prefer HA proxy client if available (no creds), otherwise fall back to direct.
        try:
            if "tok_client" in locals() and tok_client:
                journey_route = tok_client.get_route(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
            elif ha_client:
                journey_route = ha_client.get_route(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
            elif "client" in locals() and client:
                journey_route = client.get_route(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)
        except Exception:
            journey_route = None

        if trips:
            top_trip = max(trips, key=lambda t: (t.get("distance") or 0, t.get("duration") or 0))
            if top_trip and top_trip.get("startTime") and top_trip.get("endTime"):
                try:
                    if "tok_client" in locals() and tok_client:
                        top_trip_route = tok_client.get_route(device_id=a.device_id, from_ts=top_trip.get("startTime"), to_ts=top_trip.get("endTime"))
                    elif ha_client:
                        top_trip_route = ha_client.get_route(device_id=a.device_id, from_ts=top_trip.get("startTime"), to_ts=top_trip.get("endTime"))
                except Exception:
                    if "client" in locals() and client:
                        top_trip_route = client.get_route(
                            device_id=a.device_id,
                            from_ts=top_trip.get("startTime"),
                            to_ts=top_trip.get("endTime"),
                        )
    except Exception:
        journey_route = None
        top_trip_route = None

    wrapped = build_wrapped(
        title=a.title,
        device_id=a.device_id,
        from_ts=a.from_ts,
        to_ts=a.to_ts,
        trips=trips,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        journey_route=journey_route,
        top_trip_route=top_trip_route,
    )

    os.makedirs(os.path.dirname(a.out_json), exist_ok=True)
    with open(a.out_json, "w", encoding="utf-8") as f:
        json.dump(wrapped, f, ensure_ascii=False, indent=2)

    os.makedirs(os.path.dirname(a.out_html), exist_ok=True)
    with open(a.out_html, "w", encoding="utf-8") as f:
        f.write(render_html(wrapped))


if __name__ == "__main__":
    main()
