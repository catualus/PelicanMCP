# PelicanMCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Model Context Protocol (MCP) server for the **[Pelican Panel](https://pelican.dev) Application API** (admin endpoints) **and Client API** (live server control — power, console, status, files, backups), built with FastMCP.

Pelican is a modern fork of Pterodactyl. Its API is close but has diverged, and this server targets Pelican's actual routes. It's itself a fork of [PterodactylMCP](https://github.com/TomDotBat/PterodactylMCP) adapted for those differences — see [Differences from Pterodactyl](#differences-from-pterodactyl).

## Quick install

**uvx (recommended, no checkout needed):**

```bash
uvx pelican-mcp
```

**pip:**

```bash
pip install pelican-mcp
pelican-mcp
```

**Docker:**

```bash
docker build -t pelican-mcp .
docker run --rm -i \
  -e PELICAN_URL=https://panel.example.com \
  -e PELICAN_TOKEN=papp_REPLACE_ME \
  pelican-mcp
```

**Smithery:** a ready-to-use `smithery.yaml` ships at the repo root.
**Claude Desktop one-click (DXT):** see [Building a DXT bundle](#building-a-dxt-bundle).

## Capabilities

| Kind | Count | Highlights |
| --- | --- | --- |
| Tools | 165 | Every Application API route (users, servers, nodes, eggs, roles, plugins, mounts, database-hosts, server databases) **and** every Client API route (power, console, resources/status, files, backups, schedules, startup, network, subusers, account/ssh-keys) plus AI-friendly helpers and per-API raw-request escape hatches. |
| Prompts | 2 | `troubleshoot_server`, `provision_user_and_server` |
| Resources | 2 | `pelican://panel/overview`, `pelican://servers/{server_id}/summary` |

## Two APIs, two keys

Pelican exposes two separate APIs, and a single key belongs to exactly one of them:

| API | Path prefix | Key prefix | Tools | Token env var |
| --- | --- | --- | --- | --- |
| Application | `/api/application/...` | `papp_` | `pelican_app_*`, `pelican_ai_*` | `PELICAN_TOKEN` |
| Client (Account) | `/api/client/...` | `pacc_` | `pelican_client_*` | `PELICAN_CLIENT_TOKEN` |

You may set either key, or both. **At least one is required.** Back-compat shim: if
`PELICAN_CLIENT_TOKEN` is unset but `PELICAN_TOKEN` is a `pacc_` key, it is reused for the
client tools automatically. The generic `PANEL_*` names are also accepted as fallbacks, so
an existing Pterodactyl-MCP-style config keeps working (just swap in Pelican keys).

Create keys in the panel under **Account → API Credentials** (`pacc_`, client scope) or, as
an admin, the **Application API Keys** page (`papp_`, admin scope).

## Required configuration

| Env var | Required | Description |
| --- | --- | --- |
| `PELICAN_URL` | yes | Base URL of your Pelican panel (e.g. `https://panel.example.com`). |
| `PELICAN_TOKEN` | one of* | Application API key (`papp_`). Backs `pelican_app_*` / `pelican_ai_*`. |
| `PELICAN_CLIENT_TOKEN` | one of* | Client/Account API key (`pacc_`). Backs `pelican_client_*`. |
| `PELICAN_TIMEOUT` | no | HTTP timeout in seconds (default `30`). |
| `PELICAN_VERIFY_SSL` | no | `true`/`false` (default `true`). |
| `PELICAN_USER_AGENT` | no | Custom User-Agent. |

\* At least one of `PELICAN_TOKEN` / `PELICAN_CLIENT_TOKEN` is required.

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

From a local checkout, point the client at `python` with arg
`C:\path\to\PelicanMCP\run_server.py` (or run `python -m pelican_mcp`).

## Supported endpoints (Application API)

One MCP tool per route in Pelican's `routes/api-application.php`, including:

- **Users**: list/get/create/update/delete, lookup by `external_id`, **assign/remove roles**
- **Servers**: list/get/create/delete (+ force), lookup by `external_id`, update details/build/startup, suspend/unsuspend, reinstall, **transfer / cancel-transfer**
- **Nodes**: list/get/create/update/delete, list deployable, get configuration, manage allocations
- **Eggs** (top-level — Pelican has no nests): list/get, export, import, delete (by id or uuid)
- **Roles**: list/get/create/update/delete (Pelican RBAC)
- **Plugins**: list/get, import by file/url, install/update/uninstall, enable/disable
- **Mounts**: list/get/create/update/delete, attach/detach eggs, nodes and servers
- **Database hosts**: list/get/create/update/delete
- **Server databases**: list/get/create/delete, reset password

## Supported endpoints (Client API)

One MCP tool per route in Pelican's `routes/api-client.php`, including:

- **Account**: profile, update username/email/password, activity log, **API keys**, **SSH keys**
- **Power / console**: `power` (start/stop/restart/kill), `command` (send console command)
- **Status**: `resources` (current state + cpu/mem/disk), server details, `websocket` token, `activity`
- **Files**: list, contents, download, write, rename, copy, compress, decompress, delete, create-folder, chmod, pull, upload
- **Backups**: list/create/view/download/**rename**/lock/restore/delete
- **Startup / settings**: startup vars, rename, **description**, reinstall, docker-image
- **Schedules, network allocations, subusers, databases**

> **Notes:**
> - The `command` endpoint returns `204` with **no console output**. Read output back with
>   `pelican_client_console_tail`, which opens the console websocket (the same source as the
>   panel's console tab).
> - The Client API `{server}` parameter is the server's **full UUID** (36 chars, the `uuid`
>   field), *not* the short identifier. `pelican_client_list_servers` surfaces both.

## AI-friendly tools (recommended)

Designed to keep responses small and LLM-friendly:

Application API (`pelican_ai_*`):

- `pelican_ai_search_users` / `pelican_ai_search_servers` — top-N fuzzy search
- `pelican_ai_list_users` / `pelican_ai_list_servers` / `pelican_ai_list_eggs` — compact lists
- `pelican_ai_get_user_summary` / `pelican_ai_get_server_summary` — compact single-resource views
- `pelican_ai_panel_totals` — counts (users/servers/nodes/eggs/roles)

Client API:

- `pelican_client_power(server, signal)` — start/stop/restart/kill
- `pelican_client_send_command(server, command)` — send a console command (no output returned)
- `pelican_client_console_tail(server, seconds=8, lines=80)` — read recent console output over the websocket
- `pelican_client_server_status(server)` — compact `current_state` + cpu/memory/disk/uptime
- `pelican_client_list_servers()` — compact list of servers this key can access (with UUIDs)

Bulk file management (Client API): `pelican_client_upload_dir`, `pelican_client_download_dir`,
`pelican_client_delete_files` — move whole folders to/from a server with `include`/`exclude`
glob filters and `dry_run` previews (delete defaults to `dry_run=True`). Guard rails
(overridable): `max_files=500`, `max_file_bytes=25 MiB`, `max_total_bytes=250 MiB`.

## Differences from Pterodactyl

Pelican is API-compatible in spirit but not identical. The notable changes this server accounts for:

- **Token prefixes**: `papp_` (Application) / `pacc_` (Account) instead of `ptla_` / `ptlc_`.
- **Auth**: Laravel Sanctum bearer tokens with a plain `Accept: application/json` header (no `vnd.pterodactyl` media type).
- **Nests removed**: eggs are top-level at `/api/application/eggs`.
- **Locations removed** from the Application API.
- **New Application groups**: roles, plugins, mounts, database-hosts, and server transfer.
- **New Client capabilities**: account username/email/password updates, API keys, SSH keys, backup rename, settings/description.
- **Client `{server}` is the full UUID**, not the short identifier.

## Transports

- `stdio` (default) — for desktop MCP clients (Claude Desktop, etc.).
- `sse` / `streamable-http` — `pelican-mcp --transport sse --host 127.0.0.1 --port 8000 --path /mcp`.

## Tool naming

Route tools are generated as:

- Application API: `pelican_app_{method}_{path}` (with `/api/application/` removed)
- Client API: `pelican_client_{method}_{path}` (with `/api/client/` removed)

`/` → `_`, `-` → `_`, `{param}` → `param`. Discover the full list with
`pelican_app_list_endpoints` / `pelican_client_list_endpoints`. Anything not mapped can be
reached with the raw `pelican_app_request` / `pelican_client_request` tools.

## Building a DXT bundle

```bash
npm install -g @anthropic-ai/dxt
dxt pack
```

The resulting `.dxt` prompts the user for the panel URL and API keys on install.

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

## Links

- Pelican Panel: https://pelican.dev
- Pelican source (route definitions): https://github.com/pelican-dev/panel
- FastMCP: https://gofastmcp.com

## License

[MIT](LICENSE) — fork of [PterodactylMCP](https://github.com/TomDotBat/PterodactylMCP).
