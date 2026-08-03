"""
Authenticated, rate-limited Space-Track.org client.

Credentials are read from environment variables SPACETRACK_USER and
SPACETRACK_PASS -- never hardcode credentials in this file. In GitHub
Actions these are supplied as repository secrets.
"""
import os
import time
import requests

BASE_URL = "https://www.space-track.org"
LOGIN_URL = f"{BASE_URL}/ajaxauth/login"

MIN_REQUEST_INTERVAL_S = 1.5  # client-side throttling, well under Space-Track's rate limit
MAX_RETRIES = 4


class SpaceTrackClient:
    def __init__(self, username=None, password=None):
        self.username = username or os.environ.get("SPACETRACK_USER")
        self.password = password or os.environ.get("SPACETRACK_PASS")
        if not self.username or not self.password:
            raise RuntimeError(
                "Missing Space-Track credentials. Set SPACETRACK_USER and "
                "SPACETRACK_PASS as environment variables (GitHub Actions "
                "repo secrets in CI)."
            )
        self.session = requests.Session()
        self._last_request_ts = 0.0
        self._logged_in = False

    def login(self):
        resp = self.session.post(
            LOGIN_URL,
            data={"identity": self.username, "password": self.password},
            timeout=30,
        )
        if resp.status_code != 200 or "Login Failed" in resp.text:
            raise RuntimeError(f"Space-Track login failed (status {resp.status_code})")
        self._logged_in = True

    def _throttle(self):
        elapsed = time.time() - self._last_request_ts
        if elapsed < MIN_REQUEST_INTERVAL_S:
            time.sleep(MIN_REQUEST_INTERVAL_S - elapsed)

    def get(self, query_path):
        if not self._logged_in:
            self.login()

        for attempt in range(1, MAX_RETRIES + 1):
            self._throttle()
            self._last_request_ts = time.time()
            resp = self.session.get(f"{BASE_URL}{query_path}", timeout=60)

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 429 or resp.status_code >= 500:
                backoff = 2 ** attempt
                time.sleep(backoff)
                continue

            resp.raise_for_status()

        raise RuntimeError(f"Space-Track request failed after {MAX_RETRIES} retries: {query_path}")

    def gp_by_norad_ids(self, norad_ids):
        """Fetch current GP (TLE-equivalent) data for a list of NORAD catalog IDs."""
        ids = ",".join(str(i) for i in norad_ids)
        path = (
            f"/basicspacedata/query/class/gp/NORAD_CAT_ID/{ids}"
            "/orderby/NORAD_CAT_ID/format/json"
        )
        return self.get(path)

    def gp_by_altitude_band(self, perigee_min_km, perigee_max_km, limit=500):
        """Fetch current GP data for objects within a perigee altitude band."""
        path = (
            f"/basicspacedata/query/class/gp/PERIGEE/{perigee_min_km}--{perigee_max_km}"
            f"/orderby/NORAD_CAT_ID/limit/{limit}/format/json"
        )
        return self.get(path)

    def cdm_public_recent(self, days=2, limit=200):
        """Fetch recent public Conjunction Data Messages."""
        path = (
            f"/basicspacedata/query/class/cdm_public/CREATION_DATE/%3Enow-{days}"
            f"/orderby/CREATION_DATE%20desc/limit/{limit}/format/json"
        )
        return self.get(path)
