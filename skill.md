# PterodactylMCP

MCP server for the **Pterodactyl Panel Application API and Client API**. Provides admin-level control over users, servers, nodes, locations, nests, eggs, and databases (Application API), plus live control of running servers — power signals, console commands, status, files, and backups (Client API) — via the Model Context Protocol.

## Install

```bash
uvx pterodactyl-mcp
# or
pip install pterodactyl-mcp && pterodactyl-mcp
```

## Required configuration

| Env var | Required | Description |
| --- | --- | --- |
| `PANEL_URL` | yes | Base URL of your Pterodactyl panel (e.g. `https://panel.example.com`). |
| `PANEL_TOKEN` | one of* | Application API key (usually starts with `ptla_`). Backs `ptero_app_*` / `ptero_ai_*`. |
| `PANEL_CLIENT_TOKEN` | one of* | Client API key (usually starts with `ptlc_`). Backs `ptero_client_*`. |
| `PANEL_TIMEOUT` | no | HTTP timeout in seconds (default `30`). |
| `PANEL_VERIFY_SSL` | no | `true`/`false` (default `true`). |
| `PANEL_USER_AGENT` | no | Custom User-Agent. |

\* At least one of `PANEL_TOKEN` / `PANEL_CLIENT_TOKEN` is required. If only a `ptlc_` key is
set as `PANEL_TOKEN`, it is reused for the client tools automatically (back-compat shim).

## MCP client configuration

```json
{
  "mcpServers": {
    "pterodactyl": {
      "command": "uvx",
      "args": ["pterodactyl-mcp"],
      "env": {
        "PANEL_URL": "https://panel.example.com",
        "PANEL_TOKEN": "ptla_REPLACE_ME",
        "PANEL_CLIENT_TOKEN": "ptlc_REPLACE_ME"
      }
    }
  }
}
```

## Capabilities

- **Tools (117)** — one per Application **and** Client API route plus AI-friendly helpers and per-API raw-request escape hatches.
  - Application groups (`ptero_app_*`): Users, Servers, Nodes, Locations, Nests/Eggs, Server Databases.
  - Client groups (`ptero_client_*`): power, console command, resources/status, files, backups, schedules, startup, network, subusers.
  - AI helpers — Application (`ptero_ai_*`): fuzzy search, compact list, summary, panel totals.
  - AI helpers — Client (`ptero_client_power`, `ptero_client_send_command`, `ptero_client_console_tail`, `ptero_client_server_status`, `ptero_client_list_servers`).
  - Bulk files — Client (`ptero_client_upload_dir`, `ptero_client_download_dir`, `ptero_client_delete_files`): move whole folders to/from a server with `include`/`exclude` glob filters; support `dry_run` (delete defaults to it). Guarded by `max_files`/`max_file_bytes`/`max_total_bytes`.
  - Note: `ptero_client_send_command` returns `204` with no console output; read output back with `ptero_client_console_tail` (opens the console websocket). The `{server}` arg is the short identifier (e.g. `95415e3b`).
- **Prompts (2)**
  - `troubleshoot_server` — guided diagnostic walkthrough for a server.
  - `provision_user_and_server` — guided create-user-then-server workflow.
- **Resources (2)**
  - `pterodactyl://panel/overview` — counts of users/servers/nodes/locations/nests.
  - `pterodactyl://servers/{server_id}/summary` — compact server summary.

## Transports

- `stdio` (default) — for desktop MCP clients (Claude Desktop, etc.).
- `sse` / `streamable-http` — `pterodactyl-mcp --transport sse --host 127.0.0.1 --port 8000 --path /mcp`.

## Links

- Source: https://github.com/PixlFlip-Enterprises/PterodactylMCP
- Pterodactyl Application API docs: https://pterodactyl-api-docs.netvpx.com/docs/api/application
