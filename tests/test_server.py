import asyncio
import re

from pelican_mcp.server import mcp


def test_server_registers_expected_tools():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}

    assert "pelican_ai_search_users" in names
    assert "pelican_ai_search_servers" in names
    assert "pelican_ai_list_eggs" in names
    assert "pelican_ai_panel_totals" in names

    assert "pelican_app_get_users" in names
    assert "pelican_app_get_servers_server" in names
    assert "pelican_app_delete_nodes_node_allocations_allocation" in names

    # Pelican-specific application tools
    assert "pelican_app_get_eggs" in names
    assert "pelican_app_get_roles" in names
    assert "pelican_app_get_plugins" in names
    assert "pelican_app_post_servers_server_transfer" in names

    assert "pelican_app_list_endpoints" in names
    assert "pelican_app_request" in names

    # Nests and locations were removed in Pelican — no tools should reference them.
    # (Careful: "allocation" contains the substring "location", so match whole segments.)
    assert not any("nest" in n for n in names)
    assert "pelican_app_get_locations" not in names
    assert not any(re.search(r"_locations?(_|$)", n) for n in names)


def test_server_registers_client_tools():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}

    # priority-tier client routes
    assert "pelican_client_get" in names
    assert "pelican_client_get_servers_server" in names
    assert "pelican_client_get_servers_server_resources" in names
    assert "pelican_client_post_servers_server_power" in names
    assert "pelican_client_post_servers_server_command" in names

    # Pelican-specific client routes
    assert "pelican_client_get_account_ssh_keys" in names
    assert "pelican_client_put_servers_server_backups_backup_rename" in names
    assert "pelican_client_post_servers_server_settings_description" in names

    # ergonomic client AI tools
    assert "pelican_client_power" in names
    assert "pelican_client_send_command" in names
    assert "pelican_client_server_status" in names
    assert "pelican_client_console_tail" in names
    assert "pelican_client_list_servers" in names

    # client meta tools
    assert "pelican_client_list_endpoints" in names
    assert "pelican_client_request" in names


def test_server_registers_prompts():
    prompts = asyncio.run(mcp.list_prompts())
    names = {p.name for p in prompts}
    assert "troubleshoot_server" in names
    assert "provision_user_and_server" in names


def test_server_registers_resources():
    resources = asyncio.run(mcp.list_resources())
    templates = asyncio.run(mcp.list_resource_templates())
    static_uris = {str(r.uri) for r in resources}
    template_uris = {str(t.uri_template) for t in templates}
    all_uris = static_uris | template_uris
    assert any("pelican://panel/overview" in u for u in all_uris)
    assert any("pelican://servers/" in u and "summary" in u for u in all_uris)


class TestRawBodyRouting:
    """files/write must not be sent as JSON.

    Routing it through json= quotes the payload and escapes newlines, so the
    daemon writes a corrupt file and still returns 204. The failure only
    surfaces later, when whatever reads the file tries to parse it.
    """

    def test_files_write_matches(self):
        from pelican_mcp.server import RAW_BODY_PATH_RE

        assert RAW_BODY_PATH_RE.search("/api/client/servers/{server}/files/write")

    def test_other_paths_do_not_match(self):
        from pelican_mcp.server import RAW_BODY_PATH_RE

        for path in (
            "/api/client/servers/{server}/files/rename",
            "/api/client/servers/{server}/files/list",
            "/api/client/servers/{server}/files/write/extra",
            "/api/application/servers/{server}/databases",
        ):
            assert not RAW_BODY_PATH_RE.search(path), path

    def test_write_tool_uses_send_raw(self, monkeypatch):
        """The generated tool must call send_raw, not request."""
        import pelican_mcp.server as srv

        calls = {}

        class FakeClient:
            def send_raw(self, method, path, *, query=None, content, content_type="text/plain"):
                calls["send_raw"] = {"method": method, "path": path, "content": content}
                return {"status": 204}

            def request(self, *a, **kw):
                calls["request"] = True
                return {}

        registered = {}
        monkeypatch.setattr(
            srv.mcp, "tool", lambda **kw: (lambda fn: registered.setdefault(kw["name"], fn))
        )
        srv._register_route_tools(
            [{"method": "POST", "path": "/api/client/servers/{server}/files/write"}],
            client_factory=FakeClient,
            prefix="/api/client",
            name_prefix="pelican_client",
        )

        tool = next(iter(registered.values()))
        tool(server="abc", query={"file": "/x.lua"}, body="-- lua\nreturn true\n")

        assert "request" not in calls, "must not go through the JSON path"
        assert calls["send_raw"]["content"] == "-- lua\nreturn true\n"
