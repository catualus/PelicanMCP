from __future__ import annotations

import fnmatch
import posixpath
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from .client import PterodactylClient

# Safety rails so a stray glob can't try to move gigabytes or thousands of files
# in a single tool call. All are overridable per call.
_DEFAULT_MAX_FILES = 500
_DEFAULT_MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MiB per file
_DEFAULT_MAX_TOTAL_BYTES = 250 * 1024 * 1024  # 250 MiB per call
_MAX_REMOTE_DEPTH = 25  # guard against symlink loops when walking remote dirs


def register_file_ai_tools(mcp: FastMCP, client_factory: Callable[[], PterodactylClient]) -> None:
    @mcp.tool(
        description=(
            "Bulk-upload every file under a local folder to a server directory. "
            "`server` is the short identifier; `local_dir` is a path on THIS machine; "
            "`remote_dir` is the destination on the server (default '/'). "
            "Filter with `include`/`exclude` glob lists (e.g. include=['*.yml','config/*'], "
            "exclude=['*.log','node_modules/*']): a file is uploaded when it matches any "
            "include (or include is empty) AND no exclude. Globs are matched against both "
            "the path relative to `local_dir` (posix '/') and the bare filename; '*' spans "
            "directories. `recursive` walks sub-folders (default True). Set `dry_run` True "
            "to preview the plan without uploading. Wings creates missing parent folders. "
            "Returns per-file results plus counts."
        )
    )
    def ptero_client_upload_dir(
        server: str,
        local_dir: str,
        remote_dir: str = "/",
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        recursive: bool = True,
        dry_run: bool = False,
        max_files: int = _DEFAULT_MAX_FILES,
        max_file_bytes: int = _DEFAULT_MAX_FILE_BYTES,
        max_total_bytes: int = _DEFAULT_MAX_TOTAL_BYTES,
    ) -> dict[str, Any]:
        return upload_dir(
            client_factory(),
            server,
            local_dir=local_dir,
            remote_dir=remote_dir,
            include=include,
            exclude=exclude,
            recursive=recursive,
            dry_run=dry_run,
            max_files=max_files,
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_total_bytes,
        )

    @mcp.tool(
        description=(
            "Bulk-delete files/folders on a server that match glob filters. `server` is the "
            "short identifier; `remote_dir` is the directory to scan (default '/'). Same "
            "include/exclude semantics as ptero_client_upload_dir. `recursive` descends into "
            "sub-folders (default True). ALWAYS run with `dry_run` True first to review what "
            "would be removed — deletion is irreversible. Returns the matched paths and, when "
            "not a dry run, the delete result."
        )
    )
    def ptero_client_delete_files(
        server: str,
        remote_dir: str = "/",
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        recursive: bool = True,
        dry_run: bool = True,
        max_files: int = _DEFAULT_MAX_FILES,
    ) -> dict[str, Any]:
        return delete_files(
            client_factory(),
            server,
            remote_dir=remote_dir,
            include=include,
            exclude=exclude,
            recursive=recursive,
            dry_run=dry_run,
            max_files=max_files,
        )

    @mcp.tool(
        description=(
            "Bulk-download files from a server directory to a local folder, filtered by globs. "
            "`server` is the short identifier; `remote_dir` is the source on the server "
            "(default '/'); `local_dir` is the destination on THIS machine (created if needed). "
            "Same include/exclude semantics as ptero_client_upload_dir. `recursive` walks "
            "sub-folders (default True). Set `dry_run` True to preview. Returns per-file results "
            "plus counts."
        )
    )
    def ptero_client_download_dir(
        server: str,
        local_dir: str,
        remote_dir: str = "/",
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        recursive: bool = True,
        dry_run: bool = False,
        max_files: int = _DEFAULT_MAX_FILES,
        max_file_bytes: int = _DEFAULT_MAX_FILE_BYTES,
        max_total_bytes: int = _DEFAULT_MAX_TOTAL_BYTES,
    ) -> dict[str, Any]:
        return download_dir(
            client_factory(),
            server,
            local_dir=local_dir,
            remote_dir=remote_dir,
            include=include,
            exclude=exclude,
            recursive=recursive,
            dry_run=dry_run,
            max_files=max_files,
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_total_bytes,
        )


# --------------------------------------------------------------------------- #
# Glob filtering
# --------------------------------------------------------------------------- #

def _matches_any(rel_path: str, patterns: list[str]) -> bool:
    """True if rel_path (posix) or its basename matches any glob pattern.

    fnmatch's '*' spans '/', so '*.log' also matches 'logs/app.log'. Matching the
    basename too lets a plain '*.log' behave intuitively regardless of depth.
    """
    name = rel_path.rsplit("/", 1)[-1]
    for pattern in patterns:
        pat = pattern.strip()
        if not pat:
            continue
        # Normalise a trailing '/' (directory-style pattern) to match contents.
        if pat.endswith("/"):
            pat = pat + "*"
        if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(name, pat):
            return True
    return False


def _wanted(rel_path: str, include: list[str] | None, exclude: list[str] | None) -> bool:
    if exclude and _matches_any(rel_path, exclude):
        return False
    if include:
        return _matches_any(rel_path, include)
    return True


def _norm_remote_dir(remote_dir: str) -> str:
    """Normalise a remote directory to a leading-slash, no-trailing-slash posix path."""
    cleaned = "/" + (remote_dir or "/").strip().strip("/")
    return cleaned.rstrip("/") or "/"


def _join_remote(remote_dir: str, rel_path: str) -> str:
    base = _norm_remote_dir(remote_dir)
    joined = posixpath.normpath(posixpath.join(base, rel_path))
    if not joined.startswith("/"):
        joined = "/" + joined
    return joined


# --------------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------------- #

def upload_dir(
    client: PterodactylClient,
    server: str,
    *,
    local_dir: str,
    remote_dir: str = "/",
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    recursive: bool = True,
    dry_run: bool = False,
    max_files: int = _DEFAULT_MAX_FILES,
    max_file_bytes: int = _DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = _DEFAULT_MAX_TOTAL_BYTES,
) -> dict[str, Any]:
    root = Path(local_dir).expanduser()
    if not root.exists():
        raise ValueError(f"local_dir does not exist: {local_dir}")
    if not root.is_dir():
        raise ValueError(f"local_dir is not a directory: {local_dir}")

    iterator = root.rglob("*") if recursive else root.glob("*")
    planned: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    total_bytes = 0

    for path in sorted(p for p in iterator if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if not _wanted(rel, include, exclude):
            continue

        size = path.stat().st_size
        remote_path = _join_remote(remote_dir, rel)

        if size > max_file_bytes:
            skipped.append({"file": rel, "remote": remote_path, "reason": f"exceeds max_file_bytes ({size} > {max_file_bytes})"})
            continue
        if total_bytes + size > max_total_bytes:
            skipped.append({"file": rel, "remote": remote_path, "reason": "would exceed max_total_bytes"})
            continue
        if len(planned) >= max_files:
            skipped.append({"file": rel, "remote": remote_path, "reason": f"exceeds max_files ({max_files})"})
            continue

        total_bytes += size
        planned.append({"file": rel, "remote": remote_path, "bytes": size, "path": str(path)})

    uploaded: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    if not dry_run:
        for item in planned:
            try:
                content = Path(item["path"]).read_bytes()
                client.send_raw(
                    "POST",
                    f"/api/client/servers/{server}/files/write",
                    query={"file": item["remote"]},
                    content=content,
                    content_type="application/octet-stream",
                )
                uploaded.append({"file": item["file"], "remote": item["remote"], "bytes": item["bytes"]})
            except Exception as exc:  # surface per-file failures without aborting the batch
                errors.append({"file": item["file"], "remote": item["remote"], "error": str(exc)})

    plan_view = [{"file": p["file"], "remote": p["remote"], "bytes": p["bytes"]} for p in planned]
    return {
        "server": server,
        "local_dir": str(root),
        "remote_dir": _norm_remote_dir(remote_dir),
        "dry_run": dry_run,
        "planned": plan_view,
        "uploaded": uploaded,
        "skipped": skipped,
        "errors": errors,
        "counts": {
            "matched": len(planned),
            "uploaded": len(uploaded),
            "skipped": len(skipped),
            "errors": len(errors),
            "total_bytes": total_bytes,
        },
    }


# --------------------------------------------------------------------------- #
# Remote walk (shared by delete + download)
# --------------------------------------------------------------------------- #

def _list_remote(client: PterodactylClient, server: str, directory: str) -> list[dict[str, Any]]:
    payload = client.request(
        "GET",
        f"/api/client/servers/{server}/files/list",
        query={"directory": directory},
    )
    data = payload.get("data") if isinstance(payload, dict) else None
    out: list[dict[str, Any]] = []
    if isinstance(data, list):
        for entry in data:
            attrs = entry.get("attributes") if isinstance(entry, dict) else None
            if isinstance(attrs, dict):
                out.append(attrs)
    return out


def _walk_remote(
    client: PterodactylClient,
    server: str,
    remote_dir: str,
    *,
    recursive: bool,
    max_files: int,
) -> tuple[list[dict[str, Any]], bool]:
    """Return (files, truncated). Each file: {rel, remote, bytes}. rel is posix, relative to remote_dir."""
    base = _norm_remote_dir(remote_dir)
    files: list[dict[str, Any]] = []
    truncated = False
    stack: list[tuple[str, int]] = [(base, 0)]

    while stack:
        current, depth = stack.pop()
        for attrs in _list_remote(client, server, current):
            name = attrs.get("name")
            if not name:
                continue
            full = _join_remote(current, name)
            rel = full[len(base):].lstrip("/") if full.startswith(base) else name
            is_file = attrs.get("is_file", True)
            if is_file:
                if len(files) >= max_files:
                    truncated = True
                    continue
                files.append({"rel": rel, "remote": full, "bytes": attrs.get("size")})
            elif recursive and depth < _MAX_REMOTE_DEPTH:
                stack.append((full, depth + 1))

    files.sort(key=lambda f: f["rel"])
    return files, truncated


# --------------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------------- #

def delete_files(
    client: PterodactylClient,
    server: str,
    *,
    remote_dir: str = "/",
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    recursive: bool = True,
    dry_run: bool = True,
    max_files: int = _DEFAULT_MAX_FILES,
) -> dict[str, Any]:
    files, truncated = _walk_remote(client, server, remote_dir, recursive=recursive, max_files=max_files)
    matched = [f for f in files if _wanted(f["rel"], include, exclude)]

    result: dict[str, Any] = {
        "server": server,
        "remote_dir": _norm_remote_dir(remote_dir),
        "dry_run": dry_run,
        "matched": [{"file": f["rel"], "remote": f["remote"], "bytes": f["bytes"]} for f in matched],
        "counts": {"matched": len(matched), "scanned": len(files)},
        "truncated": truncated,
    }

    if not dry_run and matched:
        deleted = client.request(
            "POST",
            f"/api/client/servers/{server}/files/delete",
            body={"root": "/", "files": [f["remote"] for f in matched]},
        )
        result["deleted"] = deleted
        result["counts"]["deleted"] = len(matched)

    return result


# --------------------------------------------------------------------------- #
# Download
# --------------------------------------------------------------------------- #

def download_dir(
    client: PterodactylClient,
    server: str,
    *,
    local_dir: str,
    remote_dir: str = "/",
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    recursive: bool = True,
    dry_run: bool = False,
    max_files: int = _DEFAULT_MAX_FILES,
    max_file_bytes: int = _DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = _DEFAULT_MAX_TOTAL_BYTES,
) -> dict[str, Any]:
    dest_root = Path(local_dir).expanduser()
    files, truncated = _walk_remote(client, server, remote_dir, recursive=recursive, max_files=max_files)

    planned: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    total_bytes = 0
    for f in files:
        if not _wanted(f["rel"], include, exclude):
            continue
        size = f.get("bytes") or 0
        if isinstance(size, int) and size > max_file_bytes:
            skipped.append({"file": f["rel"], "reason": f"exceeds max_file_bytes ({size} > {max_file_bytes})"})
            continue
        if isinstance(size, int) and total_bytes + size > max_total_bytes:
            skipped.append({"file": f["rel"], "reason": "would exceed max_total_bytes"})
            continue
        if isinstance(size, int):
            total_bytes += size
        planned.append(f)

    downloaded: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    if not dry_run:
        for f in planned:
            try:
                content = client.fetch_bytes(
                    f"/api/client/servers/{server}/files/contents",
                    query={"file": f["remote"]},
                )
                target = dest_root / Path(f["rel"])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                downloaded.append({"file": f["rel"], "local": str(target), "bytes": len(content)})
            except Exception as exc:
                errors.append({"file": f["rel"], "error": str(exc)})

    return {
        "server": server,
        "remote_dir": _norm_remote_dir(remote_dir),
        "local_dir": str(dest_root),
        "dry_run": dry_run,
        "planned": [{"file": f["rel"], "remote": f["remote"], "bytes": f.get("bytes")} for f in planned],
        "downloaded": downloaded,
        "skipped": skipped,
        "errors": errors,
        "truncated": truncated,
        "counts": {
            "matched": len(planned),
            "downloaded": len(downloaded),
            "skipped": len(skipped),
            "errors": len(errors),
        },
    }
