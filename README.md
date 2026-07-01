# PterodactylMCP

[![MCP Badge](https://lobehub.com/badge/mcp/pixlflip-enterprises-pterodactylmcp)](https://lobehub.com/mcp/pixlflip-enterprises-pterodactylmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Model Context Protocol (MCP) server for the **Pterodactyl Panel Application API** (admin endpoints) **and Client API** (live server control — power, console, status, files, backups), built with FastMCP.

## Quick install

Pick whichever path matches your client.

**uvx (recommended, no checkout needed):**

```bash
uvx pterodactyl-mcp
```

**pip:**

```bash
pip install pterodactyl-mcp
pterodactyl-mcp
```

**Docker:**

```bash
docker build -t pterodactyl-mcp .
docker run --rm -i \
  -e PANEL_URL=https://panel.example.com \
  -e PANEL_TOKEN=ptla_REPLACE_ME \
  pterodactyl-mcp
```

**Claude Desktop one-click (DXT):** see [Building a DXT bundle](#building-a-dxt-bundle) below.

**Smithery:** a ready-to-use `smithery.yaml` ships at the repo root.

## Capabilities

| Kind | Count | Highlights |
| --- | --- | --- |
| Tools | 113 | All Application API routes (users, servers, nodes, locations, nests/eggs, databases) **and Client API routes** (power, console command, resources/status, files, backups, schedules, startup) plus AI-friendly helpers and per-API raw-request escape hatches. |
| Prompts | 2 | `troubleshoot_server`, `provision_user_and_server` |
| Resources | 2 | `pterodactyl://panel/overview`, `pterodactyl://servers/{server_id}/summary` |

## Two APIs, two keys

Pterodactyl exposes two separate APIs and a single key belongs to exactly one of them:

| API | Path prefix | Key prefix | Tools | Token env var |
| --- | --- | --- | --- | --- |
| Application | `/api/application/...` | `ptla_` | `ptero_app_*`, `ptero_ai_*` | `PANEL_TOKEN` |
| Client | `/api/client/...` | `ptlc_` | `ptero_client_*` | `PANEL_CLIENT_TOKEN` |

You may set either key, or both. **At least one is required.** Back-compat shim: if
`PANEL_CLIENT_TOKEN` is unset but `PANEL_TOKEN` is a `ptlc_` key, it is reused for the
client tools automatically — so an existing client-key config lights up `ptero_client_*`
with no changes.

## What this provides

- MCP tools that map to Pterodactyl **Application API** routes (users, servers, nodes, locations, nests/eggs, server databases).
- A generic `ptero_app_request` tool for calling any `/api/application/...` endpoint not yet mapped.
- AI-friendly, token-efficient tools (search, compact lists, summaries).

## Supported endpoints (Application API)

This server exposes one MCP tool per route from the NETVPX Application API docs, including:

- **Users**: list/get/create/update/delete, lookup by `external_id`
- **Servers**: list/get/create/delete, lookup by `external_id`, update details/build/startup, suspend/unsuspend, reinstall
- **Nodes**: list/get/create/update/delete, list deployable nodes, get config, manage allocations
- **Locations**: list/get/create/update/delete
- **Nests/Eggs**: list nests, get nest, list eggs, get egg
- **Server databases**: list/get/create/delete, reset database password

## Supported endpoints (Client API)

One MCP tool per route from the panel's `routes/api-client.php`, including:

- **Power / console**: `power` (start/stop/restart/kill), `command` (send console command)
- **Status**: `resources` (current state + cpu/mem/disk), server details, `websocket` token, `activity`
- **Files**: list, contents, download, write, rename, copy, compress, decompress, delete, create-folder, chmod, pull
- **Backups**: list/create/view/download/lock/restore/delete
- **Startup / settings**: startup vars, rename, reinstall, docker-image
- **Schedules, network allocations, subusers, databases**

> **Note:** the `command` endpoint returns `204` with **no console output** — Pterodactyl does
> not return output from it. Live console output requires the websocket (out of scope for now).
> The Client API `{server}` parameter is the **short identifier** (e.g. `95415e3b`), not the
> numeric Application id.

## AI-friendly tools (recommended)

These tools are designed to keep responses small and “LLM-friendly”:

Application API:

- `ptero_ai_search_users` (top-N fuzzy search across username/email/name/external_id/uuid)
- `ptero_ai_search_servers` (top-N fuzzy search across name/identifier/uuid/external_id)
- `ptero_ai_list_users` / `ptero_ai_list_servers` (compact, safe defaults)
- `ptero_ai_get_user_summary` / `ptero_ai_get_server_summary` (compact single-resource views)
- `ptero_ai_panel_totals` (counts for common resources)

Client API:

- `ptero_client_power(server, signal)` — start/stop/restart/kill
- `ptero_client_send_command(server, command)` — send a console command (no output returned)
- `ptero_client_console_tail(server, seconds=8, lines=80)` — read recent console output over the
  console websocket (the panel's console source); pairs with `send_command` to confirm execution
- `ptero_client_server_status(server)` — compact `current_state` + cpu/memory/disk/uptime
- `ptero_client_list_servers()` — compact list of servers this client key can access

Bulk file management (Client API):

- `ptero_client_upload_dir(server, local_dir, remote_dir="/", include=None, exclude=None, recursive=True, dry_run=False)`
  — upload every file under a local folder to a server directory. Filter with `include`/`exclude`
  glob lists (e.g. `include=["*.yml","config/*"]`, `exclude=["*.log","node_modules/*"]`): a file is
  uploaded when it matches any include (or include is empty) **and** no exclude. Globs match both the
  path relative to `local_dir` and the bare filename; `*` spans directories. Wings creates missing
  parent folders. Use `dry_run=True` to preview.
- `ptero_client_delete_files(server, remote_dir="/", include=None, exclude=None, recursive=True, dry_run=True)`
  — bulk-delete server files matching the same glob filters. Defaults to `dry_run=True` since deletion
  is irreversible; review the matched list, then re-run with `dry_run=False`.
- `ptero_client_download_dir(server, local_dir, remote_dir="/", include=None, exclude=None, recursive=True, dry_run=False)`
  — the inverse of upload: pull matching server files down into a local folder.

Guard rails on the bulk tools (all overridable): `max_files=500`, `max_file_bytes=25 MiB`,
`max_total_bytes=250 MiB`. Anything over a limit is reported under `skipped` rather than transferred.

## References

- FastMCP Quickstart: https://gofastmcp.com/getting-started/quickstart
- NETVPX Pterodactyl Application API docs: https://pterodactyl-api-docs.netvpx.com/docs/api/application
- NETVPX Authentication docs: https://pterodactyl-api-docs.netvpx.com/docs/authentication

## Requirements

- Python 3.10+
- A Pterodactyl **Application API** key (`ptla_...`) with appropriate permissions

## Getting an Application API key

You need an **Application** token (usually `ptla_...`), not a Client token (`ptlc_...`).

Typical flow in the panel:

1) Sign in with an admin account
2) Open your account’s API credentials page
3) Create an **Application API** key and copy it

If your panel UI differs, follow the Authentication reference link below.

## Setup

1) Create a virtual environment (recommended):

- Windows (PowerShell): `python -m venv .venv; .\\.venv\\Scripts\\Activate.ps1`
- macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`

2) Install dependencies:

`pip install -r requirements.txt`

3) Configure environment variables:

- Copy `.env.example` to `.env`
- Set:
  - `PANEL_URL` (e.g. `https://panel.example.com`)
  - `PANEL_TOKEN` (your **Application** API key, usually starts with `ptla_`) — for `ptero_app_*`
  - `PANEL_CLIENT_TOKEN` (your **Client** API key, usually starts with `ptlc_`) — for `ptero_client_*`
  - At least one of the two tokens is required; set both to use both API trees.

Optional env vars:

- `PANEL_TIMEOUT` (seconds, default `30`)
- `PANEL_VERIFY_SSL` (`true`/`false`, default `true`)
- `PANEL_USER_AGENT` (default `PterodactylMCP/0.1`)

## Run the MCP server

### STDIO transport (recommended for desktop MCP clients)

From the repo root:

`python run_server.py`

Alternatively:

`python -m pterodactyl_mcp`

### HTTP transport (optional)

`python -m pterodactyl_mcp --transport sse --host 127.0.0.1 --port 8000 --path /mcp`

## Connecting from an MCP client

Most MCP desktop clients launch the server as a subprocess. Point them at:

- Command: `python`
- Args: `C:\\path\\to\\PterodactylMCP\\run_server.py` (recommended)

If your client does not run with this repo as the working directory, prefer setting `PANEL_URL` and `PANEL_TOKEN` in the client config environment instead of relying on `.env` discovery.

### Claude Desktop example (uvx — works on Windows/macOS/Linux)

Edit your `claude_desktop_config.json` and add:

```json
{
  "mcpServers": {
    "pterodactyl": {
      "command": "uvx",
      "args": ["pterodactyl-mcp"],
      "env": {
        "PANEL_URL": "https://panel.example.com",
        "PANEL_TOKEN": "ptla_REPLACE_ME"
      }
    }
  }
}
```

### Claude Desktop (from a local checkout, Windows)

```json
{
  "mcpServers": {
    "pterodactyl": {
      "command": "python",
      "args": ["C:\\\\path\\\\to\\\\PterodactylMCP\\\\run_server.py"],
      "env": {
        "PANEL_URL": "https://panel.example.com",
        "PANEL_TOKEN": "ptla_REPLACE_ME"
      }
    }
  }
}
```

## Building a DXT bundle

This repo ships a `manifest.json` so you can build a one-click `.dxt` for Claude Desktop:

```bash
npm install -g @anthropic-ai/dxt
dxt pack
```

The resulting `.dxt` file can be dropped into Claude Desktop — it prompts the user for `PANEL_URL` and `PANEL_TOKEN` on install.

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

## License

[MIT](LICENSE)

## Tool naming

Route tools are generated using the pattern:

- Application API: `ptero_app_{method}_{path}` (with `/api/application/` removed)
- Client API: `ptero_client_{method}_{path}` (with `/api/client/` removed)

In both cases `/` → `_`, `-` → `_`, and `{param}` → `param`. Discover the full list with
`ptero_app_list_endpoints` / `ptero_client_list_endpoints`.

## Calling tools

- Each route tool takes the route path params as normal arguments (e.g. `server`, `user`, `node`), plus optional `query` and `body`.
- Use `query` for query-string parameters (pagination, filters, includes), and `body` for JSON request payloads.
- To discover all tool names and their routes, call `ptero_app_list_endpoints`.
- For token efficiency, prefer the `ptero_ai_*` tools for discovery (search/list/summary), then call the raw `ptero_app_*` route tool once you have the exact ID.

Example query params (brackets are valid dict keys):

- `{"filter[email]": "admin@example.com", "include": "servers"}`

Example workflow:

1) Find the user you mean (compact results):

- Call `ptero_ai_search_users` with `query="pixel flip"`

2) Then fetch the full object only for the selected match:

- Call `ptero_app_get_users_user` with `user=<id>`

To list all exposed tools and their routes, call:

- `ptero_app_list_endpoints`
