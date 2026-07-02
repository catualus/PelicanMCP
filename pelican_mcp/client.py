from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env(*names: str) -> str | None:
    """Return the first non-empty environment variable from ``names``.

    Lets the Pelican-native ``PELICAN_*`` names take precedence while still
    accepting the generic ``PANEL_*`` names (handy for anyone migrating a config
    from the Pterodactyl MCP).
    """
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


@dataclass(frozen=True)
class PelicanConfig:
    panel_url: str
    panel_token: str | None = None
    panel_client_token: str | None = None
    timeout: float = 30.0
    verify_ssl: bool = True
    user_agent: str = "PelicanMCP/0.1"

    @classmethod
    def from_env(cls) -> PelicanConfig:
        repo_root = Path(__file__).resolve().parents[1]
        load_dotenv(repo_root / ".env", override=False)

        panel_url = _env("PELICAN_URL", "PANEL_URL") or ""
        panel_token = _env("PELICAN_TOKEN", "PANEL_TOKEN")
        panel_client_token = _env("PELICAN_CLIENT_TOKEN", "PANEL_CLIENT_TOKEN")
        if not panel_url:
            raise ValueError("Missing required env var: PELICAN_URL (or PANEL_URL)")
        if not panel_token and not panel_client_token:
            raise ValueError(
                "Missing required env var: set PELICAN_TOKEN (Application API, papp_) "
                "and/or PELICAN_CLIENT_TOKEN (Client/Account API, pacc_)"
            )

        timeout_raw = _env("PELICAN_TIMEOUT", "PANEL_TIMEOUT")
        timeout = float(timeout_raw) if timeout_raw else 30.0
        verify_ssl = _parse_bool(
            os.environ.get("PELICAN_VERIFY_SSL", os.environ.get("PANEL_VERIFY_SSL")),
            default=True,
        )
        user_agent = _env("PELICAN_USER_AGENT", "PANEL_USER_AGENT") or "PelicanMCP/0.1"

        return cls(
            panel_url=panel_url.rstrip("/"),
            panel_token=panel_token,
            panel_client_token=panel_client_token,
            timeout=timeout,
            verify_ssl=verify_ssl,
            user_agent=user_agent,
        )


class PelicanClient:
    def __init__(self, config: PelicanConfig, *, token: str | None = None) -> None:
        bearer = token or config.panel_token
        if not bearer:
            raise ValueError("PelicanClient requires an API token")
        self._base_url = config.panel_url.rstrip("/")
        # Pelican authenticates the API with Laravel Sanctum bearer tokens and does not
        # use a custom vendor media type (unlike Pterodactyl's vnd.pterodactyl header).
        # Plain application/json is correct.
        self._http = httpx.Client(
            base_url=config.panel_url,
            timeout=config.timeout,
            verify=config.verify_ssl,
            headers={
                "Authorization": f"Bearer {bearer}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": config.user_agent,
            },
        )

    @property
    def base_url(self) -> str:
        """Panel base URL (no trailing slash), e.g. https://panel.example.com."""
        return self._base_url

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
    ) -> Any:
        resp = self._http.request(method, path, params=query, json=body)
        if resp.status_code == 204:
            return {"status": 204}

        try:
            payload: Any = resp.json()
        except Exception:
            payload = resp.text

        if resp.status_code >= 400:
            raise RuntimeError(f"Pelican API error {resp.status_code}: {payload}")

        return payload

    def send_raw(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        content: bytes | str,
        content_type: str = "text/plain",
    ) -> Any:
        """Send a request whose body is raw (non-JSON) content.

        Needed for endpoints like ``files/write`` that expect the literal file
        content as the request body rather than a JSON envelope.
        """
        resp = self._http.request(
            method,
            path,
            params=query,
            content=content,
            headers={"Content-Type": content_type},
        )
        if resp.status_code == 204:
            return {"status": 204}

        try:
            payload: Any = resp.json()
        except Exception:
            payload = resp.text

        if resp.status_code >= 400:
            raise RuntimeError(f"Pelican API error {resp.status_code}: {payload}")

        return payload

    def fetch_bytes(self, path: str, *, query: dict[str, Any] | None = None) -> bytes:
        """GET a path and return the raw response bytes (for file downloads)."""
        resp = self._http.request("GET", path, params=query)
        if resp.status_code >= 400:
            try:
                payload: Any = resp.json()
            except Exception:
                payload = resp.text
            raise RuntimeError(f"Pelican API error {resp.status_code}: {payload}")
        return resp.content
