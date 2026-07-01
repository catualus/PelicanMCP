import asyncio

from pterodactyl_mcp.file_ai_tools import (
    _join_remote,
    _matches_any,
    _norm_remote_dir,
    _wanted,
    delete_files,
    download_dir,
    upload_dir,
)
from pterodactyl_mcp.server import mcp


class FakeClient:
    """Records requests and serves a canned remote file tree for list/contents."""

    def __init__(self, tree=None):
        # tree: {directory: [ {name, is_file, size} ]}
        self.tree = tree or {}
        self.raw_writes = []
        self.requests = []

    def send_raw(self, method, path, *, query=None, content, content_type="text/plain"):
        self.raw_writes.append({"path": path, "file": query.get("file"), "content": content})
        return {"object": "file_object", "attributes": {"success": True}}

    def fetch_bytes(self, path, *, query=None):
        return f"content-of:{query['file']}".encode()

    def request(self, method, path, *, query=None, body=None):
        self.requests.append({"method": method, "path": path, "query": query, "body": body})
        if path.endswith("/files/list"):
            directory = query["directory"]
            return {"data": [{"attributes": a} for a in self.tree.get(directory, [])]}
        if path.endswith("/files/delete"):
            return {"status": 204}
        return {}


# --------------------------------------------------------------------------- #
# Glob helpers
# --------------------------------------------------------------------------- #

def test_matches_any_basename_and_path():
    assert _matches_any("logs/app.log", ["*.log"])
    assert _matches_any("config/server.yml", ["config/*"])
    assert not _matches_any("config/server.yml", ["*.log"])


def test_matches_any_trailing_slash_dir_pattern():
    assert _matches_any("node_modules/x/y.js", ["node_modules/"])


def test_wanted_include_exclude_precedence():
    # exclude wins over include
    assert not _wanted("a.log", ["*"], ["*.log"])
    assert _wanted("a.yml", ["*.yml"], ["*.log"])
    # no include => everything not excluded
    assert _wanted("anything.txt", None, None)
    # include set but no match => excluded
    assert not _wanted("a.txt", ["*.yml"], None)


def test_norm_and_join_remote():
    assert _norm_remote_dir("/") == "/"
    assert _norm_remote_dir("plugins/") == "/plugins"
    assert _norm_remote_dir("/config/") == "/config"
    assert _join_remote("/", "a/b.txt") == "/a/b.txt"
    assert _join_remote("/plugins", "conf/x.yml") == "/plugins/conf/x.yml"


# --------------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------------- #

def _make_local_tree(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "server.yml").write_text("root")
    (tmp_path / "config" / "db.yml").write_text("db")
    (tmp_path / "logs" / "latest.log").write_text("noise")
    return tmp_path


def test_upload_dir_filters_and_uploads(tmp_path):
    _make_local_tree(tmp_path)
    client = FakeClient()
    result = upload_dir(
        client,
        "abc123",
        local_dir=str(tmp_path),
        remote_dir="/",
        exclude=["*.log"],
    )
    remotes = sorted(u["remote"] for u in result["uploaded"])
    assert remotes == ["/config/db.yml", "/server.yml"]
    assert result["counts"]["uploaded"] == 2
    # the .log file was filtered out entirely (not uploaded)
    assert all(".log" not in w["file"] for w in client.raw_writes)
    # raw bytes were sent, not JSON
    assert client.raw_writes[0]["content"] == b"root" or client.raw_writes[0]["content"] == b"db"


def test_upload_dir_include_only(tmp_path):
    _make_local_tree(tmp_path)
    client = FakeClient()
    result = upload_dir(
        client, "abc123", local_dir=str(tmp_path), include=["*.yml"], remote_dir="/data"
    )
    remotes = sorted(u["remote"] for u in result["uploaded"])
    assert remotes == ["/data/config/db.yml", "/data/server.yml"]


def test_upload_dir_dry_run_uploads_nothing(tmp_path):
    _make_local_tree(tmp_path)
    client = FakeClient()
    result = upload_dir(client, "abc123", local_dir=str(tmp_path), dry_run=True)
    assert result["dry_run"] is True
    assert result["uploaded"] == []
    assert client.raw_writes == []
    assert result["counts"]["matched"] == 3


def test_upload_dir_non_recursive(tmp_path):
    _make_local_tree(tmp_path)
    client = FakeClient()
    result = upload_dir(client, "abc123", local_dir=str(tmp_path), recursive=False)
    assert [u["remote"] for u in result["uploaded"]] == ["/server.yml"]


def test_upload_dir_max_file_bytes_skips(tmp_path):
    _make_local_tree(tmp_path)
    client = FakeClient()
    result = upload_dir(client, "abc123", local_dir=str(tmp_path), max_file_bytes=3)
    # "root"/"db" are >3? "root"=4 bytes, "db"=2, "noise"=5 → only db.yml fits
    uploaded = [u["remote"] for u in result["uploaded"]]
    assert "/config/db.yml" in uploaded
    assert any("exceeds max_file_bytes" in s["reason"] for s in result["skipped"])


# --------------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------------- #

def test_delete_files_dry_run(tmp_path):
    tree = {
        "/": [
            {"name": "server.yml", "is_file": True, "size": 4},
            {"name": "logs", "is_file": False, "size": 0},
        ],
        "/logs": [{"name": "a.log", "is_file": True, "size": 5}],
    }
    client = FakeClient(tree)
    result = delete_files(client, "abc123", include=["*.log"], dry_run=True)
    assert [m["remote"] for m in result["matched"]] == ["/logs/a.log"]
    # dry run => no delete request issued
    assert not any(r["path"].endswith("/files/delete") for r in client.requests)


def test_delete_files_executes(tmp_path):
    tree = {"/": [{"name": "a.log", "is_file": True, "size": 5}]}
    client = FakeClient(tree)
    result = delete_files(client, "abc123", include=["*.log"], dry_run=False)
    delete_req = [r for r in client.requests if r["path"].endswith("/files/delete")]
    assert len(delete_req) == 1
    assert delete_req[0]["body"] == {"root": "/", "files": ["/a.log"]}
    assert result["counts"]["deleted"] == 1


# --------------------------------------------------------------------------- #
# Download
# --------------------------------------------------------------------------- #

def test_download_dir(tmp_path):
    tree = {
        "/": [
            {"name": "server.yml", "is_file": True, "size": 4},
            {"name": "logs", "is_file": False, "size": 0},
        ],
        "/logs": [{"name": "a.log", "is_file": True, "size": 5}],
    }
    client = FakeClient(tree)
    dest = tmp_path / "out"
    result = download_dir(client, "abc123", local_dir=str(dest), exclude=["*.log"])
    assert result["counts"]["downloaded"] == 1
    written = (dest / "server.yml").read_bytes()
    assert written == b"content-of:/server.yml"
    # excluded log not written
    assert not (dest / "logs" / "a.log").exists()


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #

def test_server_registers_file_tools():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "ptero_client_upload_dir" in names
    assert "ptero_client_delete_files" in names
    assert "ptero_client_download_dir" in names
