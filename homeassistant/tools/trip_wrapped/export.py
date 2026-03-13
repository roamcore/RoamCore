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
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--device-id", type=int, required=True)
    p.add_argument("--from", dest="from_ts", required=True)
    p.add_argument("--to", dest="to_ts", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-html", required=True)
    p.add_argument("--title", default="Trip Wrapped")
    return p.parse_args()


def main():
    a = parse_args()

    client = TraccarClient(base_url=a.base_url, username=a.username, password=a.password)
    trips = client.get_trips(device_id=a.device_id, from_ts=a.from_ts, to_ts=a.to_ts)

    wrapped = build_wrapped(
        title=a.title,
        device_id=a.device_id,
        from_ts=a.from_ts,
        to_ts=a.to_ts,
        trips=trips,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )

    os.makedirs(os.path.dirname(a.out_json), exist_ok=True)
    with open(a.out_json, "w", encoding="utf-8") as f:
        json.dump(wrapped, f, ensure_ascii=False, indent=2)

    os.makedirs(os.path.dirname(a.out_html), exist_ok=True)
    with open(a.out_html, "w", encoding="utf-8") as f:
        f.write(render_html(wrapped))


if __name__ == "__main__":
    main()

