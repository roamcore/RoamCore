import base64
import json
import urllib.parse
import urllib.request


class TraccarClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = (base_url or "").rstrip("/")
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        self._auth_header = f"Basic {token}"

    def _get_json(self, path: str, query: dict | None = None):
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": self._auth_header,
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_trips(self, device_id: int, from_ts: str, to_ts: str):
        return self._get_json(
            "/api/reports/trips",
            {
                "deviceId": device_id,
                "from": from_ts,
                "to": to_ts,
            },
        )

