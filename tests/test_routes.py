from pelican_mcp.routes import APPLICATION_ROUTES, CLIENT_ROUTES
from pelican_mcp.server import _tool_name


def test_routes_have_required_keys():
    for route in APPLICATION_ROUTES:
        assert set(route.keys()) >= {"method", "path"}
        assert route["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        assert route["path"].startswith("/api/application/")


def test_client_routes_have_required_keys():
    for route in CLIENT_ROUTES:
        assert set(route.keys()) >= {"method", "path"}
        assert route["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        assert route["path"].startswith("/api/client")


def _app_name(route):
    return _tool_name(route["method"], route["path"])


def _client_name(route):
    return _tool_name(route["method"], route["path"], prefix="/api/client", name_prefix="pelican_client")


def test_no_duplicate_tool_names():
    names = [_app_name(r) for r in APPLICATION_ROUTES]
    assert len(names) == len(set(names)), "Duplicate generated application tool names"


def test_no_duplicate_client_tool_names():
    names = [_client_name(r) for r in CLIENT_ROUTES]
    assert len(names) == len(set(names)), "Duplicate generated client tool names"


def test_no_duplicate_names_across_tables():
    names = [_app_name(r) for r in APPLICATION_ROUTES] + [_client_name(r) for r in CLIENT_ROUTES]
    assert len(names) == len(set(names)), "Duplicate generated tool names across both tables"


def test_tool_name_format():
    assert _tool_name("GET", "/api/application/users") == "pelican_app_get_users"
    assert _tool_name("GET", "/api/application/users/{user}") == "pelican_app_get_users_user"
    assert (
        _tool_name("DELETE", "/api/application/nodes/{node}/allocations/{allocation}")
        == "pelican_app_delete_nodes_node_allocations_allocation"
    )
    # Pelican-specific: eggs are top-level, roles/assign, plugins.
    assert _tool_name("GET", "/api/application/eggs") == "pelican_app_get_eggs"
    assert (
        _tool_name("PATCH", "/api/application/users/{user}/roles/assign")
        == "pelican_app_patch_users_user_roles_assign"
    )
    assert (
        _tool_name("POST", "/api/application/plugins/{plugin}/install")
        == "pelican_app_post_plugins_plugin_install"
    )


def test_client_tool_name_format():
    kw = {"prefix": "/api/client", "name_prefix": "pelican_client"}
    assert _tool_name("GET", "/api/client", **kw) == "pelican_client_get"
    assert _tool_name("GET", "/api/client/permissions", **kw) == "pelican_client_get_permissions"
    assert (
        _tool_name("GET", "/api/client/servers/{server}/resources", **kw)
        == "pelican_client_get_servers_server_resources"
    )
    assert (
        _tool_name("POST", "/api/client/servers/{server}/power", **kw)
        == "pelican_client_post_servers_server_power"
    )
    assert (
        _tool_name("POST", "/api/client/servers/{server}/files/create-folder", **kw)
        == "pelican_client_post_servers_server_files_create_folder"
    )


def test_pelican_specific_endpoints_present():
    app_paths = {r["path"] for r in APPLICATION_ROUTES}
    # Nests and locations were removed in Pelican.
    assert not any("/nests" in p for p in app_paths)
    assert not any("/locations" in p for p in app_paths)
    # New Pelican application groups.
    assert "/api/application/eggs" in app_paths
    assert "/api/application/roles" in app_paths
    assert "/api/application/plugins" in app_paths
    assert "/api/application/mounts" in app_paths
    assert "/api/application/database-hosts" in app_paths
    assert "/api/application/servers/{server}/transfer" in app_paths

    client_paths = {r["path"] for r in CLIENT_ROUTES}
    assert "/api/client/account/ssh-keys" in client_paths
    assert "/api/client/servers/{server}/backups/{backup}/rename" in client_paths
    assert "/api/client/servers/{server}/settings/description" in client_paths
