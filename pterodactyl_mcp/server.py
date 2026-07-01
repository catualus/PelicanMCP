from __future__ import annotations

import argparse
import inspect
import os
import re
from collections.abc import Callable
from functools import lru_cache
from typing import Any, Literal
from urllib.parse import quote

from fastmcp import FastMCP

from .ai_tools import register_ai_tools
from .client import PterodactylClient, PterodactylConfig
from .client_ai_tools import register_client_ai_tools
from .file_ai_tools import register_file_ai_tools
from .prompts import register_prompts
from .resources import register_resources
from .routes import APPLICATION_ROUTES, CLIENT_ROUTES

PathParam = str | int

mcp = FastMCP("Pterodactyl Panel API (Application + Client)")


@lru_cache
def _client() -> PterodactylClient:
    """Application API client (ptla_ key). Backs ptero_app_* / ptero_ai_* tools."""
    config = PterodactylConfig.from_env()
    if config.panel_token and config.panel_token.startswith("ptlc_"):
        raise RuntimeError(
            "Application API tools require an Application key (ptla_), but PANEL_TOKEN "
            "looks like a Client key (ptlc_). Set PANEL_TOKEN to a ptla_ key, or use the "
            "ptero_client_* tools instead."
        )
    if not config.panel_token:
        raise RuntimeError("Application API tools require PANEL_TOKEN (a ptla_ key).")
    return PterodactylClient(config)


@lru_cache
def _client_api() -> PterodactylClient:
    """Client API client (ptlc_ key). Backs ptero_client_* tools.

    Uses PANEL_CLIENT_TOKEN if set; otherwise falls back to PANEL_TOKEN when it looks
    like a client key (back-compat shim so an existing ptlc_ PANEL_TOKEN just works).
    """
    config = PterodactylConfig.from_env()
    token = config.panel_client_token
    if not token and config.panel_token and config.panel_token.startswith("ptlc_"):
        token = config.panel_token
    if not token:
        raise RuntimeError(
            "Client API tools require PANEL_CLIENT_TOKEN (a ptlc_ key). Set it to a "
            "Pterodactyl Client API key, or set PANEL_TOKEN to a ptlc_ key."
        )
    return PterodactylClient(config, token=token)


def _tool_name(
    method: str,
    path: str,
    *,
    prefix: str = "/api/application",
    name_prefix: str = "ptero_app",
) -> str:
    suffix = path.removeprefix(prefix.rstrip("/")).strip("/")
    parts: list[str] = []
    for segment in suffix.split("/"):
        if not segment:
            continue
        if segment.startswith("{") and segment.endswith("}"):
            segment = segment[1:-1]
        parts.append(segment.replace("-", "_"))
    base = f"{name_prefix}_{method.lower()}"
    return base + ("_" + "_".join(parts) if parts else "")


def _register_route_tools(
    routes: list[dict[str, str]],
    *,
    client_factory: Callable[[], PterodactylClient],
    prefix: str,
    name_prefix: str,
    describe: Callable[[str, str], str] | None = None,
) -> None:
    path_param_re = re.compile(r"{([^}]+)}")

    for route in routes:
        method = route["method"]
        template_path = route["path"]
        name = _tool_name(method, template_path, prefix=prefix, name_prefix=name_prefix)
        path_params = path_param_re.findall(template_path)

        def _make_tool(
            *,
            method: str = method,
            template_path: str = template_path,
            path_params: list[str] = path_params,
            name: str = name,
            client_factory: Callable[[], PterodactylClient] = client_factory,
        ):
            def _tool(**kwargs: Any) -> Any:
                resolved_path = template_path
                for param in path_params:
                    if param not in kwargs:
                        raise ValueError(f"Missing required path parameter: {param}")
                    resolved_path = resolved_path.replace(
                        f"{{{param}}}", quote(str(kwargs.pop(param)), safe="")
                    )

                query = kwargs.pop("query", None)
                body = kwargs.pop("body", None)
                if kwargs:
                    extra = ", ".join(sorted(kwargs.keys()))
                    raise ValueError(f"Unexpected parameters: {extra}")

                return client_factory().request(method, resolved_path, query=query, body=body)

            _tool.__name__ = name
            _tool.__doc__ = f"{method} {template_path}"

            parameters: list[inspect.Parameter] = [
                inspect.Parameter(
                    p,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=PathParam,
                )
                for p in path_params
            ]
            parameters.append(
                inspect.Parameter(
                    "query",
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=None,
                    annotation=dict[str, Any] | None,
                )
            )
            parameters.append(
                inspect.Parameter(
                    "body",
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=None,
                    annotation=Any | None,
                )
            )
            _tool.__signature__ = inspect.Signature(parameters)
            _tool.__annotations__ = {
                **{p: PathParam for p in path_params},
                "query": dict[str, Any] | None,
                "body": Any | None,
                "return": Any,
            }

            description = describe(method, template_path) if describe else f"{method} {template_path}"
            mcp.tool(name=name, description=description)(_tool)

        _make_tool()


def _describe_application(method: str, template_path: str) -> str:
    description = f"{method} {template_path}"
    if method == "GET" and template_path == "/api/application/users":
        description += " (raw; can be large — prefer ptero_ai_list_users / ptero_ai_search_users)"
    elif method == "GET" and template_path == "/api/application/servers":
        description += " (raw; can be large — prefer ptero_ai_list_servers / ptero_ai_search_servers)"
    return description


def _describe_client(method: str, template_path: str) -> str:
    description = f"{method} {template_path}"
    if method == "POST" and template_path == "/api/client/servers/{server}/power":
        description += " (body {\"signal\": start|stop|restart|kill} — or use ptero_client_power)"
    elif method == "POST" and template_path == "/api/client/servers/{server}/command":
        description += " (body {\"command\": ...}; returns 204 with no output — or use ptero_client_send_command)"
    elif method == "GET" and template_path == "/api/client/servers/{server}/resources":
        description += " (current state + cpu/mem/disk — or use ptero_client_server_status)"
    return description


@mcp.tool(description="List all Application API endpoints exposed as tools.")
def ptero_app_list_endpoints() -> list[dict[str, str]]:
    return [
        {"tool": _tool_name(r["method"], r["path"]), "method": r["method"], "path": r["path"]}
        for r in APPLICATION_ROUTES
    ]


@mcp.tool(description="List all Client API endpoints exposed as tools.")
def ptero_client_list_endpoints() -> list[dict[str, str]]:
    return [
        {
            "tool": _tool_name(r["method"], r["path"], prefix="/api/client", name_prefix="ptero_client"),
            "method": r["method"],
            "path": r["path"],
        }
        for r in CLIENT_ROUTES
    ]


@mcp.tool(description="Make a raw Application API request (useful for endpoints not mapped as tools yet).")
def ptero_app_request(
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    query: dict[str, Any] | None = None,
    body: Any | None = None,
) -> Any:
    if not path.startswith("/api/application/"):
        raise ValueError("path must start with /api/application/")
    return _client().request(method, path, query=query, body=body)


@mcp.tool(description="Make a raw Client API request (useful for endpoints not mapped as tools yet).")
def ptero_client_request(
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    query: dict[str, Any] | None = None,
    body: Any | None = None,
) -> Any:
    if not path.startswith("/api/client"):
        raise ValueError("path must start with /api/client")
    return _client_api().request(method, path, query=query, body=body)


_register_route_tools(
    APPLICATION_ROUTES,
    client_factory=_client,
    prefix="/api/application",
    name_prefix="ptero_app",
    describe=_describe_application,
)
_register_route_tools(
    CLIENT_ROUTES,
    client_factory=_client_api,
    prefix="/api/client",
    name_prefix="ptero_client",
    describe=_describe_client,
)
register_ai_tools(mcp, _client)
register_client_ai_tools(mcp, _client_api)
register_file_ai_tools(mcp, _client_api)
register_prompts(mcp)
register_resources(mcp, _client)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Pterodactyl Application API MCP server (FastMCP).")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http", "http"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="MCP transport (default: stdio).",
    )
    parser.add_argument("--host", default=os.environ.get("MCP_HOST"), help="HTTP host (sse/http only).")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ["MCP_PORT"]) if os.environ.get("MCP_PORT") else None,
        help="HTTP port (sse/http only).",
    )
    parser.add_argument("--path", default=os.environ.get("MCP_PATH"), help="HTTP path (sse/http only).")
    parser.add_argument("--no-banner", action="store_true", help="Disable FastMCP banner.")
    args = parser.parse_args(argv)

    transport_kwargs: dict[str, Any] = {}
    if args.transport != "stdio":
        if args.host:
            transport_kwargs["host"] = args.host
        if args.port:
            transport_kwargs["port"] = args.port
        if args.path:
            transport_kwargs["path"] = args.path

    mcp.run(
        transport=args.transport,
        show_banner=not args.no_banner,
        **transport_kwargs,
    )


if __name__ == "__main__":
    main()
