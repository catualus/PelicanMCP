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
from .client import PelicanClient, PelicanConfig
from .client_ai_tools import register_client_ai_tools
from .file_ai_tools import register_file_ai_tools
from .prompts import register_prompts
from .resources import register_resources
from .routes import APPLICATION_ROUTES, CLIENT_ROUTES

PathParam = str | int

# Query parameters accept either a mapping or a JSON object string. The string form
# exists because the dynamically-generated route tools below publish an empty JSON
# schema, leaving clients nothing to serialise against; PelicanClient._coerce_query
# parses it back before the request goes out.
QueryParam = dict[str, Any] | str | None

mcp = FastMCP("Pelican Panel API (Application + Client)")


@lru_cache
def _client() -> PelicanClient:
    """Application API client (papp_ key). Backs pelican_app_* / pelican_ai_* tools."""
    config = PelicanConfig.from_env()
    if config.panel_token and config.panel_token.startswith("pacc_"):
        raise RuntimeError(
            "Application API tools require an Application key (papp_), but the configured "
            "token looks like an Account/Client key (pacc_). Set PELICAN_TOKEN to a papp_ "
            "key, or use the pelican_client_* tools instead."
        )
    if not config.panel_token:
        raise RuntimeError("Application API tools require PELICAN_TOKEN (a papp_ key).")
    return PelicanClient(config)


@lru_cache
def _client_api() -> PelicanClient:
    """Client/Account API client (pacc_ key). Backs pelican_client_* tools.

    Uses PELICAN_CLIENT_TOKEN if set; otherwise falls back to PELICAN_TOKEN when it looks
    like an account key (back-compat shim so a single pacc_ token just works).
    """
    config = PelicanConfig.from_env()
    token = config.panel_client_token
    if not token and config.panel_token and config.panel_token.startswith("pacc_"):
        token = config.panel_token
    if not token:
        raise RuntimeError(
            "Client API tools require PELICAN_CLIENT_TOKEN (a pacc_ key). Set it to a "
            "Pelican Account API key, or set PELICAN_TOKEN to a pacc_ key."
        )
    return PelicanClient(config, token=token)


def _tool_name(
    method: str,
    path: str,
    *,
    prefix: str = "/api/application",
    name_prefix: str = "pelican_app",
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
    client_factory: Callable[[], PelicanClient],
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
            client_factory: Callable[[], PelicanClient] = client_factory,
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
                    # `| str` because these dynamically-built tools expose an empty
                    # JSON schema, so a client has no type to serialise against and
                    # sends the object as a raw string. Rejecting it here would fail
                    # before _coerce_query ever gets to parse it.
                    annotation=QueryParam,
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
                "query": QueryParam,
                "body": Any | None,
                "return": Any,
            }

            description = describe(method, template_path) if describe else f"{method} {template_path}"
            mcp.tool(name=name, description=description)(_tool)

        _make_tool()


def _describe_application(method: str, template_path: str) -> str:
    description = f"{method} {template_path}"
    if method == "GET" and template_path == "/api/application/users":
        description += " (raw; can be large — prefer pelican_ai_list_users / pelican_ai_search_users)"
    elif method == "GET" and template_path == "/api/application/servers":
        description += " (raw; can be large — prefer pelican_ai_list_servers / pelican_ai_search_servers)"
    elif method == "GET" and template_path == "/api/application/eggs":
        description += " (Pelican eggs are top-level — there are no nests — prefer pelican_ai_list_eggs)"
    elif method == "DELETE" and template_path == "/api/application/servers/{server}/{force}":
        description += " (force-delete; pass force=true to skip the normal safety checks)"
    return description


def _describe_client(method: str, template_path: str) -> str:
    description = f"{method} {template_path}"
    if method == "POST" and template_path == "/api/client/servers/{server}/power":
        description += " (body {\"signal\": start|stop|restart|kill} — or use pelican_client_power)"
    elif method == "POST" and template_path == "/api/client/servers/{server}/command":
        description += " (body {\"command\": ...}; returns 204 with no output — or use pelican_client_send_command)"
    elif method == "GET" and template_path == "/api/client/servers/{server}/resources":
        description += " (current state + cpu/mem/disk — or use pelican_client_server_status)"
    if "{server}" in template_path:
        description += " [{server} is the full server UUID]"
    return description


@mcp.tool(description="List all Pelican Application API endpoints exposed as tools.")
def pelican_app_list_endpoints() -> list[dict[str, str]]:
    return [
        {"tool": _tool_name(r["method"], r["path"]), "method": r["method"], "path": r["path"]}
        for r in APPLICATION_ROUTES
    ]


@mcp.tool(description="List all Pelican Client API endpoints exposed as tools.")
def pelican_client_list_endpoints() -> list[dict[str, str]]:
    return [
        {
            "tool": _tool_name(r["method"], r["path"], prefix="/api/client", name_prefix="pelican_client"),
            "method": r["method"],
            "path": r["path"],
        }
        for r in CLIENT_ROUTES
    ]


@mcp.tool(description="Make a raw Pelican Application API request (for endpoints not mapped as tools yet).")
def pelican_app_request(
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    query: QueryParam = None,
    body: Any | None = None,
) -> Any:
    if not path.startswith("/api/application/"):
        raise ValueError("path must start with /api/application/")
    return _client().request(method, path, query=query, body=body)


@mcp.tool(description="Make a raw Pelican Client API request (for endpoints not mapped as tools yet).")
def pelican_client_request(
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    query: QueryParam = None,
    body: Any | None = None,
) -> Any:
    if not path.startswith("/api/client"):
        raise ValueError("path must start with /api/client")
    return _client_api().request(method, path, query=query, body=body)


_register_route_tools(
    APPLICATION_ROUTES,
    client_factory=_client,
    prefix="/api/application",
    name_prefix="pelican_app",
    describe=_describe_application,
)
_register_route_tools(
    CLIENT_ROUTES,
    client_factory=_client_api,
    prefix="/api/client",
    name_prefix="pelican_client",
    describe=_describe_client,
)
register_ai_tools(mcp, _client)
register_client_ai_tools(mcp, _client_api)
register_file_ai_tools(mcp, _client_api)
register_prompts(mcp)
register_resources(mcp, _client)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Pelican Panel API MCP server (FastMCP).")
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
