from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any, Literal
from urllib.parse import urlsplit

from fastmcp import FastMCP

from .client import PelicanClient

PowerSignal = Literal["start", "stop", "restart", "kill"]

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_MAX_TAIL_SECONDS = 60.0


def register_client_ai_tools(mcp: FastMCP, client_factory: Callable[[], PelicanClient]) -> None:
    @mcp.tool(
        description=(
            "Send a power signal to a server (start/stop/restart/kill). `server` is the "
            "full server UUID (36 chars, from the 'uuid' field — not the short identifier). "
            "Returns {\"status\": 204} on success."
        )
    )
    def pelican_client_power(server: str, signal: PowerSignal) -> Any:
        return client_factory().request(
            "POST", f"/api/client/servers/{server}/power", body={"signal": signal}
        )

    @mcp.tool(
        description=(
            "Send a console command to a running server. `server` is the full server UUID. "
            "Returns {\"status\": 204} on success — Pelican does NOT return console output "
            "from this endpoint. Read output back with pelican_client_console_tail."
        )
    )
    def pelican_client_send_command(server: str, command: str) -> Any:
        return client_factory().request(
            "POST", f"/api/client/servers/{server}/command", body={"command": command}
        )

    @mcp.tool(
        description=(
            "Get a compact server status: current_state plus cpu/memory/disk/network/uptime "
            "(token-efficient view of GET .../resources). `server` is the full server UUID."
        )
    )
    def pelican_client_server_status(server: str) -> dict[str, Any]:
        return get_server_status(client_factory(), server)

    @mcp.tool(
        description=(
            "List servers this Account API key can access (compact: uuid, identifier, name, "
            "node, status). Use the `uuid` value for the other pelican_client_* tools. "
            "Backed by GET /api/client."
        )
    )
    def pelican_client_list_servers() -> dict[str, Any]:
        return list_client_servers(client_factory())

    @mcp.tool(
        description=(
            "Read recent console output from a server. Opens the Pelican console websocket "
            "(the same source as the panel's console tab), requests the log backlog, and "
            "collects output for `seconds`. Use this to confirm a command sent via "
            "pelican_client_send_command actually ran, or to inspect boot/errors. `server` is "
            "the full server UUID. Returns the last `lines` de-ANSI'd lines."
        )
    )
    async def pelican_client_console_tail(
        server: str, seconds: float = 8.0, lines: int = 80
    ) -> dict[str, Any]:
        return await read_console(client_factory(), server, seconds=seconds, lines=lines)


def get_server_status(client: PelicanClient, server: str) -> dict[str, Any]:
    payload = client.request("GET", f"/api/client/servers/{server}/resources")
    attributes = payload.get("attributes") if isinstance(payload, dict) else None
    if not isinstance(attributes, dict):
        attributes = payload if isinstance(payload, dict) else {}

    resources = attributes.get("resources")
    resources = resources if isinstance(resources, dict) else {}

    out: dict[str, Any] = {
        "current_state": attributes.get("current_state"),
        "is_suspended": attributes.get("is_suspended"),
        "cpu_absolute": resources.get("cpu_absolute"),
        "memory_bytes": resources.get("memory_bytes"),
        "disk_bytes": resources.get("disk_bytes"),
        "network_rx_bytes": resources.get("network_rx_bytes"),
        "network_tx_bytes": resources.get("network_tx_bytes"),
        "uptime": resources.get("uptime"),
    }
    return {k: v for k, v in out.items() if v is not None}


async def read_console(
    client: PelicanClient, server: str, *, seconds: float = 8.0, lines: int = 80
) -> dict[str, Any]:
    """Connect to the Pelican console websocket and collect recent output.

    Flow mirrors the panel console: fetch a one-time JWT + daemon socket URL, send the
    ``auth`` event, request the log backlog with ``send logs``, then drain ``console
    output`` events until ``seconds`` elapses. ANSI colour codes are stripped. Pelican's
    daemon (pelican-dev/wings) uses the same websocket event names as Pterodactyl's.
    """
    try:
        import websockets
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise RuntimeError(
            "pelican_client_console_tail requires the 'websockets' package "
            "(pip install websockets)"
        ) from exc

    seconds = max(0.5, min(float(seconds), _MAX_TAIL_SECONDS))

    creds = client.request("GET", f"/api/client/servers/{server}/websocket")
    data = creds.get("data") if isinstance(creds, dict) else None
    data = data if isinstance(data, dict) else {}
    token = data.get("token")
    socket = data.get("socket")
    if not token or not socket:
        raise RuntimeError(f"Websocket endpoint returned no token/socket: {creds}")

    # The daemon validates the Origin against the panel's allowed origins (the panel URL).
    split = urlsplit(client.base_url)
    origin = f"{split.scheme}://{split.netloc}"

    collected: list[str] = []

    async def _drain(ws: Any) -> None:
        await ws.send(json.dumps({"event": "auth", "args": [token]}))
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except (ValueError, TypeError):
                continue
            event = msg.get("event")
            if event == "auth success":
                await ws.send(json.dumps({"event": "send logs", "args": [None]}))
            elif event in ("console output", "install output"):
                for arg in msg.get("args", []):
                    if isinstance(arg, str):
                        collected.append(_ANSI_RE.sub("", arg))
            elif event in ("jwt error", "token expiring", "token expired"):
                # Surface auth problems instead of silently timing out.
                if event == "jwt error":
                    raise RuntimeError(f"Console websocket auth failed: {msg.get('args')}")

    try:
        connect = websockets.connect(socket, origin=origin, max_size=None)
    except TypeError:  # older websockets: origin passed via extra_headers
        connect = websockets.connect(
            socket, extra_headers={"Origin": origin}, max_size=None
        )

    async with connect as ws:
        try:
            await asyncio.wait_for(_drain(ws), timeout=seconds)
        except asyncio.TimeoutError:
            pass

    tail = collected[-lines:] if lines and lines > 0 else collected
    return {"lines": tail, "line_count": len(tail), "total_captured": len(collected)}


def list_client_servers(client: PelicanClient) -> dict[str, Any]:
    payload = client.request("GET", "/api/client")
    data = payload.get("data") if isinstance(payload, dict) else None
    items: list[dict[str, Any]] = []
    if isinstance(data, list):
        for entry in data:
            attrs = entry.get("attributes") if isinstance(entry, dict) else None
            attrs = attrs if isinstance(attrs, dict) else (entry if isinstance(entry, dict) else {})
            compact = {
                "uuid": attrs.get("uuid"),
                "identifier": attrs.get("identifier"),
                "name": attrs.get("name"),
                "node": attrs.get("node"),
                "status": attrs.get("status"),
            }
            items.append({k: v for k, v in compact.items() if v is not None})
    return {"servers": items}
