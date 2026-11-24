"""Shared helpers: credential loading and a minimal Confluence Cloud REST client.

Credentials are read from ~/.config/confluence-poc/.env; environment variables
take precedence over that file. Secret values are never printed or logged.
"""

import base64
import http.client
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

DEFAULT_ENV_FILE = Path.home() / ".config" / "confluence-poc" / ".env"
REQUIRED_VARS = ("CONFLUENCE_URL", "CONFLUENCE_USER", "CONFLUENCE_API_TOKEN", "CONFLUENCE_SPACE_KEY")
DEFAULT_ROOT_PAGE_TITLE = "Engineering Handbook"


def load_settings(env_file: Path = DEFAULT_ENV_FILE) -> dict:
    """Return the required settings, merging the env file with the process environment.

    CONFLUENCE_ROOT_PAGE_TITLE is optional and defaults to the seeded handbook root.
    """
    values: dict = {}
    if env_file.exists():
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    for key in (*REQUIRED_VARS, "CONFLUENCE_ROOT_PAGE_TITLE"):
        if os.environ.get(key):
            values[key] = os.environ[key]
    missing = [key for key in REQUIRED_VARS if not values.get(key)]
    if missing:
        raise SystemExit(f"Missing settings: {', '.join(missing)} (set them in {env_file} or the environment)")
    values["CONFLUENCE_URL"] = values["CONFLUENCE_URL"].rstrip("/")
    values["CONFLUENCE_ROOT_PAGE_TITLE"] = values.get("CONFLUENCE_ROOT_PAGE_TITLE") or DEFAULT_ROOT_PAGE_TITLE
    return values


class ConfluenceError(RuntimeError):
    """Raised when the Confluence REST API returns an error response."""


class ConfluenceClient:
    """Small wrapper around the Confluence Cloud REST API v1 (basic auth)."""

    def __init__(self, base_url: str, user: str, api_token: str):
        self.api = f"{base_url.rstrip('/')}/wiki/rest/api"
        credentials = base64.b64encode(f"{user}:{api_token}".encode()).decode()
        self._auth_header = f"Basic {credentials}"

    @classmethod
    def from_settings(cls, settings: dict) -> "ConfluenceClient":
        return cls(settings["CONFLUENCE_URL"], settings["CONFLUENCE_USER"], settings["CONFLUENCE_API_TOKEN"])

    def request(self, method: str, path: str, params: dict | None = None, payload=None,
                data: bytes | None = None, headers: dict | None = None):
        url = f"{self.api}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        request_headers = {"Authorization": self._auth_header, "Accept": "application/json"}
        body = data
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request_headers.update(headers or {})
        req = urllib.request.Request(url, data=body, method=method, headers=request_headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ConfluenceError(f"{method} {path} failed with HTTP {exc.code}: {detail}") from exc
        except (OSError, http.client.HTTPException) as exc:
            raise ConfluenceError(f"{method} {path} failed: {exc}") from exc
        try:
            return json.loads(raw) if raw else None
        except ValueError as exc:
            raise ConfluenceError(f"{method} {path} returned invalid JSON: {exc}") from exc

    def get_all(self, path: str, params: dict | None = None, page_size: int = 50) -> list:
        """Follow start/limit pagination for list endpoints."""
        results: list = []
        start = 0
        while True:
            page = self.request("GET", path, params={**(params or {}), "start": start, "limit": page_size})
            results.extend(page.get("results", []))
            if not page.get("_links", {}).get("next"):
                break
            start += page_size
        return results

    def upload_attachment(self, page_id: str, filename: str, content: bytes, mime_type: str,
                          existing_id: str | None = None) -> dict:
        """Create or replace an attachment on a page using multipart/form-data."""
        boundary = uuid.uuid4().hex
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
        path = f"/content/{page_id}/child/attachment"
        if existing_id:
            path += f"/{existing_id}/data"
        return self.request(
            "POST", path, data=body,
            headers={
                "X-Atlassian-Token": "nocheck",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
