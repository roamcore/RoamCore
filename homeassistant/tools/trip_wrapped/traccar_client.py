import json
import urllib.parse
import urllib.request
import os
import base64


class TraccarClient:
    """Minimal Traccar API client.

    Supports:
    - Direct Traccar with Basic Auth (email/password)
    - Home Assistant proxy endpoint (/api/roamcore/traccar_api/...) with Bearer auth
      using the Supervisor token (available to HA Core at
      /run/s6/container_environment/SUPERVISOR_TOKEN).
    """

    def __init__(
        self,
        base_url: str,
        auth_header: str,
        auth_header_name: str = "Authorization",
        path_prefix: str = "",
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.path_prefix = (path_prefix or "").rstrip("/")
        self._auth_header = auth_header
        self._auth_header_name = auth_header_name

    @classmethod
    def direct_basic(cls, base_url: str, username: str, password: str):
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        return cls(base_url=base_url, auth_header=f"Basic {token}")

    @classmethod
    def direct_user_token(cls, base_url: str, user_token: str):
        """Create a client using a Traccar user token.

        Traccar supports creating a session via:
          GET /api/session?token=...

        We then use the returned JSESSIONID cookie for subsequent API calls.
        """
        u = (base_url or "").rstrip("/") + "/api/session?" + urllib.parse.urlencode({"token": user_token})
        req = urllib.request.Request(u, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            sc = resp.headers.get("Set-Cookie") or ""
        js = None
        try:
            # Example: JSESSIONID=...; Path=/
            for part in sc.split(","):
                p = part.strip()
                if p.startswith("JSESSIONID="):
                    js = p.split(";", 1)[0]
                    break
        except Exception:
            js = None
        if not js:
            raise RuntimeError("Traccar token session did not return JSESSIONID")
        return cls(base_url=base_url, auth_header=js, auth_header_name="Cookie")

    @classmethod
    def ha_supervisor_proxy(cls, base_url: str = "http://supervisor/core"):
        # In the Home Assistant Core container, Supervisor auth is exposed as
        # /run/s6/container_environment/HASSIO_TOKEN.
        # Older docs/examples sometimes reference SUPERVISOR_TOKEN.
        token_paths = [
            "/run/s6/container_environment/HASSIO_TOKEN",
            "/run/s6/container_environment/SUPERVISOR_TOKEN",
        ]
        token_path = next((p for p in token_paths if os.path.exists(p)), None)
        if not token_path:
            raise RuntimeError(f"Supervisor token not found (tried: {', '.join(token_paths)})")
        token = open(token_path, "r", encoding="utf-8").read().strip()
        if not token:
            raise RuntimeError("Supervisor token was empty")
        # Home Assistant endpoint (custom component) that proxies to Traccar.
        return cls(
            base_url=base_url,
            auth_header=f"Bearer {token}",
            path_prefix="/api/roamcore/traccar_api",
        )

    def _get_json(self, path: str, query: dict | None = None):
        url = self.base_url + self.path_prefix + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        try:
            if os.environ.get("RC_TRACCAR_DEBUG") == "1":
                print("TraccarClient GET", url)
        except Exception:
            pass
        req = urllib.request.Request(
            url,
            headers={
                self._auth_header_name: self._auth_header,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_trips(self, device_id: int, from_ts: str, to_ts: str):
        # Note: path differs between direct Traccar (/api/reports/...) vs HA proxy (/reports/...).
        # We normalize by setting a path_prefix for the HA proxy.
        return self._get_json(
            "/reports/trips" if self.path_prefix else "/api/reports/trips",
            {
                "deviceId": device_id,
                "from": from_ts,
                "to": to_ts,
            },
        )

    def get_route(self, device_id: int, from_ts: str, to_ts: str):
        """Fetch route (positions) for a device over a time range.

        Traccar returns a list of positions; each typically contains latitude/longitude,
        speed, deviceTime, etc.
        """
        return self._get_json(
            "/reports/route" if self.path_prefix else "/api/reports/route",
            {
                "deviceId": device_id,
                "from": from_ts,
                "to": to_ts,
            },
        )
