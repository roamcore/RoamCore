import json
import urllib.parse
import urllib.request
import urllib.error
import os
import base64
from http.cookies import SimpleCookie


class TraccarError(RuntimeError):
    """Raised when Traccar API calls fail with actionable context."""



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
        if not (user_token and str(user_token).strip()):
            raise TraccarError("Traccar user token was empty")

        u = (base_url or "").rstrip("/") + "/api/session?" + urllib.parse.urlencode({"token": user_token})
        req = urllib.request.Request(u, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                # Traccar sets JSESSIONID as a cookie.
                # Prefer robust parsing via SimpleCookie, and handle multiple Set-Cookie headers.
                set_cookies = []
                try:
                    set_cookies = resp.headers.get_all("Set-Cookie") or []
                except Exception:
                    sc = resp.headers.get("Set-Cookie")
                    if sc:
                        set_cookies = [sc]
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = (e.read() or b"").decode("utf-8", errors="replace")
            except Exception:
                body = ""
            raise TraccarError(f"Traccar token session failed ({e.code} {e.reason}). {body}".strip())

        jsid = cls._extract_jsessionid(set_cookies)
        if not jsid:
            raise TraccarError("Traccar token session did not return JSESSIONID")
        return cls(base_url=base_url, auth_header=f"JSESSIONID={jsid}", auth_header_name="Cookie")

    @staticmethod
    def _extract_jsessionid(set_cookie_headers: list[str]) -> str | None:
        """Extract JSESSIONID from Set-Cookie headers."""
        cookie = SimpleCookie()
        for sc in set_cookie_headers or []:
            try:
                cookie.load(sc)
            except Exception:
                continue
        if "JSESSIONID" in cookie:
            try:
                return cookie["JSESSIONID"].value
            except Exception:
                return None
        return None

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
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = (e.read() or b"").decode("utf-8", errors="replace")
            except Exception:
                body = ""
            raise TraccarError(f"Traccar API request failed: GET {url} -> {e.code} {e.reason}. {body}".strip())
        except Exception as e:
            raise TraccarError(f"Traccar API request failed: GET {url}. {e}")

        try:
            return json.loads(raw)
        except Exception as e:
            raise TraccarError(f"Traccar API returned invalid JSON for {url}. {e}")

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

    def get_stops(self, device_id: int, from_ts: str, to_ts: str):
        """Fetch stop report rows for a device over a time range."""
        return self._get_json(
            "/reports/stops" if self.path_prefix else "/api/reports/stops",
            {
                "deviceId": device_id,
                "from": from_ts,
                "to": to_ts,
            },
        )
