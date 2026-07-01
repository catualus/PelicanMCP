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


@dataclass(frozen=True)
class PterodactylConfig:
    panel_url: str
    panel_token: str | None = None
    panel_client_token: str | None = None
    timeout: float = 30.0
    verify_ssl: bool = True
    user_agent: str = "PterodactylMCP/0.1"

    @classmethod
    def from_env(cls) -> PterodactylConfig:
        repo_root = Path(__file__).resolve().parents[1]
        load_dotenv(repo_root / ".env", override=False)

        panel_url = os.environ.get("PANEL_URL", "").strip()
        panel_token = os.environ.get("PANEL_TOKEN", "").strip() or None
        panel_client_token = os.environ.get("PANEL_CLIENT_TOKEN", "").strip() or None
        if not panel_url:
            raise ValueError("Missing required env var: PANEL_URL")
        if not panel_token and not panel_client_token:
            raise ValueError(
                "Missing required env var: set PANEL_TOKEN (Application API, ptla_) "
                "and/or PANEL_CLIENT_TOKEN (Client API, ptlc_)"
            )

        timeout_raw = os.environ.get("PANEL_TIMEOUT", "").strip()
        timeout = float(timeout_raw) if timeout_raw else 30.0
        verify_ssl = _parse_bool(os.environ.get("PANEL_VERIFY_SSL"), default=True)
        user_agent = os.environ.get("PANEL_USER_AGENT", "PterodactylMCP/0.1").strip() or "PterodactylMCP/0.1"

        return cls(
            panel_url=panel_url.rstrip("/"),
            panel_token=panel_token,
            panel_client_token=panel_client_token,
            timeout=timeout,
            verify_ssl=verify_ssl,
            user_agent=user_agent,
        )


class PterodactylClient:
    def __init__(self, config: PterodactylConfig, *, token: str | None = None) -> None:
        bearer = token or config.panel_token
        if not bearer:
            raise ValueError("PterodactylClient requires an API token")
        self._base_url = config.panel_url.rstrip("/")
        self._http = httpx.Client(
            base_url=config.panel_url,
            timeout=config.timeout,
            verify=config.verify_ssl,
            headers={
                "Authorization": f"Bearer {bearer}",
                "Accept": "Application/vnd.pterodactyl.v1+json",
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
            raise RuntimeError(f"Pterodactyl API error {resp.status_code}: {payload}")

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
            raise RuntimeError(f"Pterodactyl API error {resp.status_code}: {payload}")

        return payload

    def fetch_bytes(self, path: str, *, query: dict[str, Any] | None = None) -> bytes:
        """GET a path and return the raw response bytes (for file downloads)."""
        resp = self._http.request("GET", path, params=query)
        if resp.status_code >= 400:
            try:
                payload: Any = resp.json()
            except Exception:
                payload = resp.text
            raise RuntimeError(f"Pterodactyl API error {resp.status_code}: {payload}")
        return resp.content

