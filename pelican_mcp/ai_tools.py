from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from difflib import SequenceMatcher
from typing import Any

from fastmcp import FastMCP

from .client import PelicanClient


def register_ai_tools(mcp: FastMCP, client_factory: Callable[[], PelicanClient]) -> None:
    @mcp.tool(description="Fuzzy search users by username/email/name/external_id/uuid; returns compact top matches.")
    def pelican_ai_search_users(
        query: str,
        limit: int = 10,
        max_pages: int = 5,
        per_page: int = 100,
        min_score: float = 55.0,
    ) -> dict[str, Any]:
        return _fuzzy_search(
            client_factory(),
            "/api/application/users",
            query=query,
            limit=limit,
            max_pages=max_pages,
            per_page=per_page,
            min_score=min_score,
            kind="user",
        )

    @mcp.tool(description="Fuzzy search servers by name/identifier/uuid/external_id; returns compact top matches.")
    def pelican_ai_search_servers(
        query: str,
        limit: int = 10,
        max_pages: int = 5,
        per_page: int = 100,
        min_score: float = 55.0,
    ) -> dict[str, Any]:
        return _fuzzy_search(
            client_factory(),
            "/api/application/servers",
            query=query,
            limit=limit,
            max_pages=max_pages,
            per_page=per_page,
            min_score=min_score,
            kind="server",
        )

    @mcp.tool(description="List users (compact) with safe defaults to avoid huge responses.")
    def pelican_ai_list_users(page: int = 1, per_page: int = 10) -> dict[str, Any]:
        return _compact_list(client_factory(), "/api/application/users", page=page, per_page=per_page, kind="user")

    @mcp.tool(description="List servers (compact) with safe defaults to avoid huge responses.")
    def pelican_ai_list_servers(page: int = 1, per_page: int = 10) -> dict[str, Any]:
        return _compact_list(
            client_factory(), "/api/application/servers", page=page, per_page=per_page, kind="server"
        )

    @mcp.tool(
        description=(
            "List eggs (compact). In Pelican eggs are top-level (there are no nests), so this "
            "is the quick way to discover egg ids for provisioning servers."
        )
    )
    def pelican_ai_list_eggs(page: int = 1, per_page: int = 50) -> dict[str, Any]:
        return _compact_list(client_factory(), "/api/application/eggs", page=page, per_page=per_page, kind="egg")

    @mcp.tool(description="Get a compact user summary (token-efficient).")
    def pelican_ai_get_user_summary(user: str | int) -> dict[str, Any]:
        payload = client_factory().request("GET", f"/api/application/users/{user}")
        attributes = _extract_attributes(payload)
        return _compact_user(attributes)

    @mcp.tool(description="Get a compact server summary (token-efficient).")
    def pelican_ai_get_server_summary(server: str | int) -> dict[str, Any]:
        return get_server_summary(client_factory(), server)

    @mcp.tool(description="Return counts (totals) for common Application API resources (token-efficient).")
    def pelican_ai_panel_totals() -> dict[str, int]:
        return get_panel_totals(client_factory())


def get_panel_totals(client: PelicanClient) -> dict[str, int]:
    # Pelican removed locations and nests; eggs and roles are the meaningful admin
    # collections to surface instead.
    return {
        "users": _get_total(client, "/api/application/users"),
        "servers": _get_total(client, "/api/application/servers"),
        "nodes": _get_total(client, "/api/application/nodes"),
        "eggs": _get_total(client, "/api/application/eggs"),
        "roles": _get_total(client, "/api/application/roles"),
    }


def get_server_summary(client: PelicanClient, server: str | int) -> dict[str, Any]:
    payload = client.request("GET", f"/api/application/servers/{server}")
    attributes = _extract_attributes(payload)
    return _compact_server(attributes)


def get_user_summary(client: PelicanClient, user: str | int) -> dict[str, Any]:
    payload = client.request("GET", f"/api/application/users/{user}")
    attributes = _extract_attributes(payload)
    return _compact_user(attributes)


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    return _NON_ALNUM_RE.sub(" ", (text or "").lower()).strip()


def _compact(text: str) -> str:
    return _NON_ALNUM_RE.sub("", (text or "").lower())


def _token_match_score(query: str, candidate: str) -> float:
    q_tokens = _normalize(query).split()
    c_tokens = _normalize(candidate).split()
    if not q_tokens or not c_tokens:
        return 0.0

    hits = 0
    for qt in q_tokens:
        if any(ct.startswith(qt) or qt in ct for ct in c_tokens):
            hits += 1
    return (hits / len(q_tokens)) * 100.0


def _string_similarity_score(query: str, candidate: str) -> float:
    q_norm = _normalize(query)
    c_norm = _normalize(candidate)
    if not q_norm or not c_norm:
        return 0.0

    q_comp = _compact(query)
    c_comp = _compact(candidate)
    if q_norm == c_norm or (q_comp and q_comp == c_comp):
        return 100.0

    ratio_norm = SequenceMatcher(None, q_norm, c_norm).ratio()
    ratio_comp = SequenceMatcher(None, q_comp, c_comp).ratio() if q_comp and c_comp else 0.0
    ratio = max(ratio_norm, ratio_comp) * 100.0

    token_score = _token_match_score(query, candidate)

    bonus = 0.0
    if q_comp and c_comp:
        if c_comp.startswith(q_comp):
            bonus += 12.0
        elif q_comp in c_comp:
            bonus += 8.0
        elif q_comp.startswith(c_comp):
            bonus += 6.0

    score = (0.55 * ratio) + (0.45 * token_score) + bonus
    if score < 0:
        return 0.0
    if score > 100:
        return 100.0
    return score


def _truncate(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    value = str(value)
    if len(value) <= max_len:
        return value
    return value[: max_len - 1] + "…"


def _strip_nones(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None and v != ""}


def _extract_attributes(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        if isinstance(payload.get("attributes"), dict):
            return payload["attributes"]
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("attributes"), dict):
            return data["attributes"]
    return {}


def _extract_list_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, list):
        items: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                attrs = item.get("attributes")
                items.append(attrs if isinstance(attrs, dict) else item)
        return items
    return []


def _extract_pagination(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return {}
    pagination = meta.get("pagination")
    if not isinstance(pagination, dict):
        return {}
    return pagination


def _get_total(client: PelicanClient, path: str) -> int:
    payload = client.request("GET", path, query={"page": 1, "per_page": 1})
    pagination = _extract_pagination(payload)
    total = pagination.get("total")
    return int(total) if isinstance(total, (int, float, str)) and str(total).isdigit() else 0


def _iter_paginated(
    client: PelicanClient,
    path: str,
    *,
    per_page: int,
    max_pages: int,
    base_query: dict[str, Any] | None = None,
) -> Iterable[tuple[int, dict[str, Any]]]:
    per_page = max(1, min(int(per_page), 100))
    max_pages = max(1, int(max_pages))

    for page in range(1, max_pages + 1):
        query: dict[str, Any] = {"page": page, "per_page": per_page}
        if base_query:
            query.update(base_query)

        payload = client.request("GET", path, query=query)
        items = _extract_list_items(payload)
        for item in items:
            yield page, item

        pagination = _extract_pagination(payload)
        total_pages = pagination.get("total_pages")
        if isinstance(total_pages, int) and page >= total_pages:
            break
        if not items:
            break


def _compact_user(attributes: dict[str, Any], *, score: float | None = None, matched_on: str | None = None) -> dict[str, Any]:
    first = attributes.get("first_name")
    last = attributes.get("last_name")
    full_name = " ".join([p for p in [str(first).strip() if first else "", str(last).strip() if last else ""] if p])

    out: dict[str, Any] = {
        "score": round(score, 1) if score is not None else None,
        "matched_on": matched_on,
        "id": attributes.get("id"),
        "uuid": attributes.get("uuid"),
        "external_id": attributes.get("external_id"),
        "username": attributes.get("username"),
        "email": attributes.get("email"),
        "name": full_name or None,
    }
    return _strip_nones(out)


def _compact_server(attributes: dict[str, Any], *, score: float | None = None, matched_on: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "score": round(score, 1) if score is not None else None,
        "matched_on": matched_on,
        "id": attributes.get("id"),
        "identifier": attributes.get("identifier"),
        "uuid": attributes.get("uuid"),
        "external_id": attributes.get("external_id"),
        "name": attributes.get("name"),
        "description": _truncate(attributes.get("description"), 120) if isinstance(attributes.get("description"), str) else None,
        "suspended": attributes.get("suspended"),
    }
    return _strip_nones(out)


def _compact_egg(attributes: dict[str, Any], *, score: float | None = None, matched_on: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "score": round(score, 1) if score is not None else None,
        "matched_on": matched_on,
        "id": attributes.get("id"),
        "uuid": attributes.get("uuid"),
        "name": attributes.get("name"),
        "author": attributes.get("author"),
        "description": _truncate(attributes.get("description"), 120) if isinstance(attributes.get("description"), str) else None,
        "docker_image": attributes.get("docker_image"),
    }
    return _strip_nones(out)


def _fuzzy_search(
    client: PelicanClient,
    path: str,
    *,
    query: str,
    limit: int,
    max_pages: int,
    per_page: int,
    min_score: float,
    kind: str,
) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        raise ValueError("query must be a non-empty string")

    limit = max(1, min(int(limit), 50))
    min_score = float(min_score)

    candidates_scanned = 0
    pages_scanned: set[int] = set()
    scored: list[tuple[float, dict[str, Any], str | None]] = []

    def consider(score: float, attrs: dict[str, Any], matched_on: str | None) -> None:
        if score < min_score:
            return
        scored.append((score, attrs, matched_on))

    for page, attrs in _iter_paginated(client, path, per_page=per_page, max_pages=max_pages):
        pages_scanned.add(page)
        candidates_scanned += 1

        if kind == "user":
            username = attrs.get("username")
            email = attrs.get("email")
            first = attrs.get("first_name")
            last = attrs.get("last_name")
            full_name = " ".join([p for p in [str(first or "").strip(), str(last or "").strip()] if p]).strip()
            external_id = attrs.get("external_id")
            uuid = attrs.get("uuid")
            user_id = attrs.get("id")

            fields: list[tuple[str, str | None]] = [
                ("username", username),
                ("email", email),
                ("name", full_name or None),
                ("external_id", str(external_id) if external_id is not None else None),
                ("uuid", uuid),
                ("id", str(user_id) if user_id is not None else None),
            ]

            best_score = 0.0
            best_field: str | None = None
            for field_name, value in fields:
                if not value:
                    continue
                s = _string_similarity_score(query, str(value))
                if s > best_score:
                    best_score = s
                    best_field = field_name

            consider(best_score, attrs, best_field)

            if best_score >= 99.5 and len(scored) >= limit:
                break

        elif kind == "server":
            name = attrs.get("name")
            identifier = attrs.get("identifier")
            uuid = attrs.get("uuid")
            external_id = attrs.get("external_id")
            server_id = attrs.get("id")
            description = attrs.get("description")

            fields = [
                ("name", name),
                ("identifier", identifier),
                ("uuid", uuid),
                ("external_id", str(external_id) if external_id is not None else None),
                ("id", str(server_id) if server_id is not None else None),
                ("description", description),
            ]

            best_score = 0.0
            best_field: str | None = None
            for field_name, value in fields:
                if not value:
                    continue
                s = _string_similarity_score(query, str(value))
                if s > best_score:
                    best_score = s
                    best_field = field_name

            consider(best_score, attrs, best_field)

            if best_score >= 99.5 and len(scored) >= limit:
                break

    scored.sort(key=lambda t: t[0], reverse=True)
    matches = []
    for score, attrs, matched_on in scored[:limit]:
        if kind == "user":
            matches.append(_compact_user(attrs, score=score, matched_on=matched_on))
        else:
            matches.append(_compact_server(attrs, score=score, matched_on=matched_on))

    return _strip_nones(
        {
            "query": query,
            "matches": matches,
            "scanned": {"items": candidates_scanned, "pages": len(pages_scanned)},
        }
    )


def _compact_list(client: PelicanClient, path: str, *, page: int, per_page: int, kind: str) -> dict[str, Any]:
    per_page = max(1, min(int(per_page), 100))
    page = max(1, int(page))

    payload = client.request("GET", path, query={"page": page, "per_page": per_page})
    items = _extract_list_items(payload)
    pagination = _extract_pagination(payload)

    if kind == "user":
        compact_items = [_compact_user(item) for item in items]
        key = "users"
    elif kind == "egg":
        compact_items = [_compact_egg(item) for item in items]
        key = "eggs"
    else:
        compact_items = [_compact_server(item) for item in items]
        key = "servers"

    out: dict[str, Any] = {
        key: compact_items,
        "pagination": _strip_nones(
            {
                "current_page": pagination.get("current_page"),
                "per_page": pagination.get("per_page"),
                "total": pagination.get("total"),
                "total_pages": pagination.get("total_pages"),
            }
        ),
    }
    return _strip_nones(out)
