# PelicanMCP

MCP server for the **Pelican Panel Application API and Client API** ([pelican.dev](https://pelican.dev)). Provides admin-level control over users, servers, nodes, eggs, roles, plugins, mounts, database hosts, and server databases (Application API), plus live control of running servers — power signals, console commands, status, files, and backups (Client API) — via the Model Context Protocol.

Pelican is a fork of Pterodactyl; this server targets Pelican's actual routes (eggs are top-level, no nests/locations, new roles/plugins/mounts groups, `papp_`/`pacc_` keys, full-UUID client server ids).

## Install

```bash
uvx pelican-mcp
# or
pip install pelican-mcp && pelican-mcp
```

## Required configuration

| Env var | Required | Description |
| --- | --- | --- |
| `PELICAN_URL` | yes | Base URL of your Pelican panel (e.g. `https://panel.example.com`). |
| `PELICAN_TOKEN` | one of* | Application API key (usually starts with `papp_`). Backs `pelican_app_*` / `pelican_ai_*`. |
| `PELICAN_CLIENT_TOKEN` | one of* | Client/Account API key (usually starts with `pacc_`). Backs `pelican_client_*`. |
| `PELICAN_TIMEOUT` | no | HTTP timeout in seconds (default `30`). |
| `PELICAN_VERIFY_SSL` | no | `true`/`false` (default `true`). |
| `PELICAN_USER_AGENT` | no | Custom User-Agent. |

\* At least one of `PELICAN_TOKEN` / `PELICAN_CLIENT_TOKEN` is required. If only a `pacc_` key is
set as `PELICAN_TOKEN`, it is reused for the client tools automatically (back-compat shim). The
generic `PANEL_*` names are accepted as fallbacks.

## MCP client configuration

```json
{
  "mcpServers": {
    "pelican": {
      "command": "uvx",
      "args": ["pelican-mcp"],
      "env": {
        "PELICAN_URL": "https://panel.example.com",
        "PELICAN_TOKEN": "papp_REPLACE_ME",
        "PELICAN_CLIENT_TOKEN": "pacc_REPLACE_ME"
      }
    }
  }
}
```

## Capabilities

- **Tools (165)** — one per Application **and** Client API route plus AI-friendly helpers and per-API raw-request escape hatches.
  - Application groups (`pelican_app_*`): Users, Servers, Nodes, Eggs, Roles, Plugins, Mounts, Database Hosts, Server Databases.
  - Client groups (`pelican_client_*`): power, console command, resources/status, files, backups, schedules, startup, network, subusers, account/api-keys/ssh-keys.
  - AI helpers — Application (`pelican_ai_*`): fuzzy search, compact list, egg list, summary, panel totals.
  - AI helpers — Client (`pelican_client_power`, `pelican_client_send_command`, `pelican_client_console_tail`, `pelican_client_server_status`, `pelican_client_list_servers`).
  - Bulk files — Client (`pelican_client_upload_dir`, `pelican_client_download_dir`, `pelican_client_delete_files`): move whole folders to/from a server with `include`/`exclude` glob filters; support `dry_run` (delete defaults to it). Guarded by `max_files`/`max_file_bytes`/`max_total_bytes`.
  - Note: `pelican_client_send_command` returns `204` with no console output; read output back with `pelican_client_console_tail` (opens the console websocket). The `{server}` arg is the full server UUID.
- **Prompts (2)**
  - `troubleshoot_server` — guided diagnostic walkthrough for a server.
  - `provision_user_and_server` — guided create-user-then-server workflow.
- **Resources (2)**
  - `pelican://panel/overview` — counts of users/servers/nodes/eggs/roles.
  - `pelican://servers/{server_id}/summary` — compact server summary.

## Transports

- `stdio` (default) — for desktop MCP clients (Claude Desktop, etc.).
- `sse` / `streamable-http` — `pelican-mcp --transport sse --host 127.0.0.1 --port 8000 --path /mcp`.

## Links

- Pelican Panel: https://pelican.dev
- Pelican source (routes): https://github.com/pelican-dev/panel
