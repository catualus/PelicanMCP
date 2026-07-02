# Route tables for the Pelican Panel API (https://pelican.dev).
#
# These are transcribed 1:1 from the panel's own route definitions
# (pelican-dev/panel: routes/api-application.php and routes/api-client.php) so that
# every mapped tool corresponds to a real endpoint. Pelican is a fork of Pterodactyl
# but its API has diverged in several important ways — the biggest ones:
#
#   * Nests were removed. Eggs are now top-level at /api/application/eggs.
#   * Locations were removed from the Application API entirely.
#   * New Application groups: roles, plugins, mounts, database-hosts, server transfer.
#   * Client API {server} path param is the server's full UUID (36 chars), NOT the
#     short identifier (the short id is exposed as the "identifier"/"uuid_short" field).
#   * New Client groups: account username/email/password, api-keys, ssh-keys, backup
#     rename, settings/description.

# Pelican *Application* API (/api/application/...). Admin endpoints. Uses a papp_ key.
APPLICATION_ROUTES: list[dict[str, str]] = [
    # Users
    {"method": "GET", "path": "/api/application/users"},
    {"method": "GET", "path": "/api/application/users/external/{external_id}"},
    {"method": "GET", "path": "/api/application/users/{user}"},
    {"method": "POST", "path": "/api/application/users"},
    {"method": "PATCH", "path": "/api/application/users/{user}"},
    {"method": "PATCH", "path": "/api/application/users/{user}/roles/assign"},
    {"method": "PATCH", "path": "/api/application/users/{user}/roles/remove"},
    {"method": "DELETE", "path": "/api/application/users/{user}"},
    # Nodes
    {"method": "GET", "path": "/api/application/nodes"},
    {"method": "GET", "path": "/api/application/nodes/deployable"},
    {"method": "GET", "path": "/api/application/nodes/{node}"},
    {"method": "GET", "path": "/api/application/nodes/{node}/configuration"},
    {"method": "POST", "path": "/api/application/nodes"},
    {"method": "PATCH", "path": "/api/application/nodes/{node}"},
    {"method": "DELETE", "path": "/api/application/nodes/{node}"},
    {"method": "GET", "path": "/api/application/nodes/{node}/allocations"},
    {"method": "POST", "path": "/api/application/nodes/{node}/allocations"},
    {"method": "DELETE", "path": "/api/application/nodes/{node}/allocations/{allocation}"},
    # Servers
    {"method": "GET", "path": "/api/application/servers"},
    {"method": "GET", "path": "/api/application/servers/external/{external_id}"},
    {"method": "GET", "path": "/api/application/servers/{server}"},
    {"method": "POST", "path": "/api/application/servers"},
    {"method": "PATCH", "path": "/api/application/servers/{server}/details"},
    {"method": "PATCH", "path": "/api/application/servers/{server}/build"},
    {"method": "PATCH", "path": "/api/application/servers/{server}/startup"},
    {"method": "POST", "path": "/api/application/servers/{server}/suspend"},
    {"method": "POST", "path": "/api/application/servers/{server}/unsuspend"},
    {"method": "POST", "path": "/api/application/servers/{server}/reinstall"},
    {"method": "POST", "path": "/api/application/servers/{server}/transfer"},
    {"method": "POST", "path": "/api/application/servers/{server}/transfer/cancel"},
    {"method": "DELETE", "path": "/api/application/servers/{server}"},
    {"method": "DELETE", "path": "/api/application/servers/{server}/{force}"},
    # Server databases
    {"method": "GET", "path": "/api/application/servers/{server}/databases"},
    {"method": "GET", "path": "/api/application/servers/{server}/databases/{database}"},
    {"method": "POST", "path": "/api/application/servers/{server}/databases"},
    {"method": "POST", "path": "/api/application/servers/{server}/databases/{database}/reset-password"},
    {"method": "DELETE", "path": "/api/application/servers/{server}/databases/{database}"},
    # Eggs (top-level — Pelican removed nests)
    {"method": "GET", "path": "/api/application/eggs"},
    {"method": "GET", "path": "/api/application/eggs/{egg}"},
    {"method": "GET", "path": "/api/application/eggs/{egg}/export"},
    {"method": "POST", "path": "/api/application/eggs/import"},
    {"method": "DELETE", "path": "/api/application/eggs/{egg}"},
    {"method": "DELETE", "path": "/api/application/eggs/uuid/{egg}"},
    # Database hosts
    {"method": "GET", "path": "/api/application/database-hosts"},
    {"method": "GET", "path": "/api/application/database-hosts/{database_host}"},
    {"method": "POST", "path": "/api/application/database-hosts"},
    {"method": "PATCH", "path": "/api/application/database-hosts/{database_host}"},
    {"method": "DELETE", "path": "/api/application/database-hosts/{database_host}"},
    # Mounts
    {"method": "GET", "path": "/api/application/mounts"},
    {"method": "GET", "path": "/api/application/mounts/{mount}"},
    {"method": "GET", "path": "/api/application/mounts/{mount}/eggs"},
    {"method": "GET", "path": "/api/application/mounts/{mount}/nodes"},
    {"method": "GET", "path": "/api/application/mounts/{mount}/servers"},
    {"method": "POST", "path": "/api/application/mounts"},
    {"method": "POST", "path": "/api/application/mounts/{mount}/eggs"},
    {"method": "POST", "path": "/api/application/mounts/{mount}/nodes"},
    {"method": "POST", "path": "/api/application/mounts/{mount}/servers"},
    {"method": "PATCH", "path": "/api/application/mounts/{mount}"},
    {"method": "DELETE", "path": "/api/application/mounts/{mount}"},
    {"method": "DELETE", "path": "/api/application/mounts/{mount}/eggs/{egg_id}"},
    {"method": "DELETE", "path": "/api/application/mounts/{mount}/nodes/{node_id}"},
    {"method": "DELETE", "path": "/api/application/mounts/{mount}/servers/{server_id}"},
    # Roles (RBAC)
    {"method": "GET", "path": "/api/application/roles"},
    {"method": "GET", "path": "/api/application/roles/{role}"},
    {"method": "POST", "path": "/api/application/roles"},
    {"method": "PATCH", "path": "/api/application/roles/{role}"},
    {"method": "DELETE", "path": "/api/application/roles/{role}"},
    # Plugins
    {"method": "GET", "path": "/api/application/plugins"},
    {"method": "GET", "path": "/api/application/plugins/{plugin}"},
    {"method": "POST", "path": "/api/application/plugins/import/file"},
    {"method": "POST", "path": "/api/application/plugins/import/url"},
    {"method": "POST", "path": "/api/application/plugins/{plugin}/install"},
    {"method": "POST", "path": "/api/application/plugins/{plugin}/update"},
    {"method": "POST", "path": "/api/application/plugins/{plugin}/uninstall"},
    {"method": "POST", "path": "/api/application/plugins/{plugin}/enable"},
    {"method": "POST", "path": "/api/application/plugins/{plugin}/disable"},
]

# Pelican *Client* (Account) API (/api/client/...). Uses a pacc_ key. The {server} path
# param is the server's full UUID (e.g. "9a1d... 36 chars"), not the short identifier.
# Sourced from the panel's routes/api-client.php route definitions.
CLIENT_ROUTES: list[dict[str, str]] = [
    # Account / meta
    {"method": "GET", "path": "/api/client"},
    {"method": "GET", "path": "/api/client/permissions"},
    {"method": "GET", "path": "/api/client/account"},
    {"method": "PUT", "path": "/api/client/account/username"},
    {"method": "PUT", "path": "/api/client/account/email"},
    {"method": "PUT", "path": "/api/client/account/password"},
    {"method": "GET", "path": "/api/client/account/activity"},
    {"method": "GET", "path": "/api/client/account/api-keys"},
    {"method": "POST", "path": "/api/client/account/api-keys"},
    {"method": "DELETE", "path": "/api/client/account/api-keys/{identifier}"},
    {"method": "GET", "path": "/api/client/account/ssh-keys"},
    {"method": "POST", "path": "/api/client/account/ssh-keys"},
    {"method": "DELETE", "path": "/api/client/account/ssh-keys/{fingerprint}"},
    # Server core (power / console / status are the headline endpoints)
    {"method": "GET", "path": "/api/client/servers/{server}"},
    {"method": "GET", "path": "/api/client/servers/{server}/websocket"},
    {"method": "GET", "path": "/api/client/servers/{server}/resources"},
    {"method": "GET", "path": "/api/client/servers/{server}/activity"},
    {"method": "POST", "path": "/api/client/servers/{server}/command"},
    {"method": "POST", "path": "/api/client/servers/{server}/power"},
    # Databases
    {"method": "GET", "path": "/api/client/servers/{server}/databases"},
    {"method": "POST", "path": "/api/client/servers/{server}/databases"},
    {"method": "POST", "path": "/api/client/servers/{server}/databases/{database}/rotate-password"},
    {"method": "DELETE", "path": "/api/client/servers/{server}/databases/{database}"},
    # Files
    {"method": "GET", "path": "/api/client/servers/{server}/files/list"},
    {"method": "GET", "path": "/api/client/servers/{server}/files/contents"},
    {"method": "GET", "path": "/api/client/servers/{server}/files/download"},
    {"method": "PUT", "path": "/api/client/servers/{server}/files/rename"},
    {"method": "POST", "path": "/api/client/servers/{server}/files/copy"},
    {"method": "POST", "path": "/api/client/servers/{server}/files/write"},
    {"method": "POST", "path": "/api/client/servers/{server}/files/compress"},
    {"method": "POST", "path": "/api/client/servers/{server}/files/decompress"},
    {"method": "POST", "path": "/api/client/servers/{server}/files/delete"},
    {"method": "POST", "path": "/api/client/servers/{server}/files/create-folder"},
    {"method": "POST", "path": "/api/client/servers/{server}/files/chmod"},
    {"method": "POST", "path": "/api/client/servers/{server}/files/pull"},
    {"method": "GET", "path": "/api/client/servers/{server}/files/upload"},
    # Schedules
    {"method": "GET", "path": "/api/client/servers/{server}/schedules"},
    {"method": "POST", "path": "/api/client/servers/{server}/schedules"},
    {"method": "GET", "path": "/api/client/servers/{server}/schedules/{schedule}"},
    {"method": "POST", "path": "/api/client/servers/{server}/schedules/{schedule}"},
    {"method": "POST", "path": "/api/client/servers/{server}/schedules/{schedule}/execute"},
    {"method": "DELETE", "path": "/api/client/servers/{server}/schedules/{schedule}"},
    {"method": "POST", "path": "/api/client/servers/{server}/schedules/{schedule}/tasks"},
    {"method": "POST", "path": "/api/client/servers/{server}/schedules/{schedule}/tasks/{task}"},
    {"method": "DELETE", "path": "/api/client/servers/{server}/schedules/{schedule}/tasks/{task}"},
    # Network allocations
    {"method": "GET", "path": "/api/client/servers/{server}/network/allocations"},
    {"method": "POST", "path": "/api/client/servers/{server}/network/allocations"},
    {"method": "POST", "path": "/api/client/servers/{server}/network/allocations/{allocation}"},
    {"method": "POST", "path": "/api/client/servers/{server}/network/allocations/{allocation}/primary"},
    {"method": "DELETE", "path": "/api/client/servers/{server}/network/allocations/{allocation}"},
    # Subusers
    {"method": "GET", "path": "/api/client/servers/{server}/users"},
    {"method": "POST", "path": "/api/client/servers/{server}/users"},
    {"method": "GET", "path": "/api/client/servers/{server}/users/{user}"},
    {"method": "POST", "path": "/api/client/servers/{server}/users/{user}"},
    {"method": "DELETE", "path": "/api/client/servers/{server}/users/{user}"},
    # Backups
    {"method": "GET", "path": "/api/client/servers/{server}/backups"},
    {"method": "POST", "path": "/api/client/servers/{server}/backups"},
    {"method": "GET", "path": "/api/client/servers/{server}/backups/{backup}"},
    {"method": "GET", "path": "/api/client/servers/{server}/backups/{backup}/download"},
    {"method": "PUT", "path": "/api/client/servers/{server}/backups/{backup}/rename"},
    {"method": "POST", "path": "/api/client/servers/{server}/backups/{backup}/lock"},
    {"method": "POST", "path": "/api/client/servers/{server}/backups/{backup}/restore"},
    {"method": "DELETE", "path": "/api/client/servers/{server}/backups/{backup}"},
    # Startup
    {"method": "GET", "path": "/api/client/servers/{server}/startup"},
    {"method": "PUT", "path": "/api/client/servers/{server}/startup/variable"},
    # Settings
    {"method": "POST", "path": "/api/client/servers/{server}/settings/rename"},
    {"method": "POST", "path": "/api/client/servers/{server}/settings/description"},
    {"method": "POST", "path": "/api/client/servers/{server}/settings/reinstall"},
    {"method": "PUT", "path": "/api/client/servers/{server}/settings/docker-image"},
]
