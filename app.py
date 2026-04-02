from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from wsgiref.simple_server import make_server

from core.journal import load_state, save_state, state_path
from core.state import DEFAULT_SEGMENT_KEY, FUNKY_ROUNDED_FONTS, MATERIAL_ACCENTS, STATIC_SEGMENTS, iso_now, new_id
from core.storage import read_json
from ui.page import render_index


BASE_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 9000


STATIC_DIR = BASE_DIR / "static"


def ensure_trash(state: dict[str, Any]) -> dict[str, Any]:
    trash = state.get("trash")
    if not isinstance(trash, dict):
        trash = {}
    if not isinstance(trash.get("categories"), list):
        trash["categories"] = []
    if not isinstance(trash.get("topics"), list):
        trash["topics"] = []
    state["trash"] = trash
    return state


def json_response(status: str, payload: dict[str, Any]) -> list[bytes]:
    body = json.dumps(payload).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ]
    return status, headers, [body]


def bytes_response(
    status: str, body: bytes, content_type: str, extra_headers: list[tuple[str, str]] | None = None
) -> list[bytes]:
    headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(body))),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    return status, headers, [body]


def read_body(environ: dict[str, Any]) -> bytes:
    size = int(environ.get("CONTENT_LENGTH") or 0)
    if size <= 0:
        return b""
    return environ["wsgi.input"].read(size)


def parse_json(environ: dict[str, Any]) -> dict[str, Any]:
    raw = read_body(environ)
    if not raw:
        return {}
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def serve_static(path: str) -> list[bytes] | None:
    # path is already stripped to "/static/..."
    rel = path.removeprefix("/static/").lstrip("/")
    if not rel or ".." in rel or rel.startswith("/"):
        return None
    target = (STATIC_DIR / rel).resolve()
    if STATIC_DIR not in target.parents:
        return None
    try:
        body = target.read_bytes()
    except FileNotFoundError:
        return None
    ctype = "application/octet-stream"
    if rel.endswith(".css"):
        ctype = "text/css; charset=utf-8"
    elif rel.endswith(".js"):
        ctype = "text/javascript; charset=utf-8"
    elif rel.endswith(".png"):
        ctype = "image/png"
    elif rel.endswith(".jpg") or rel.endswith(".jpeg"):
        ctype = "image/jpeg"
    elif rel.endswith(".svg"):
        ctype = "image/svg+xml"
    return bytes_response("200 OK", body, ctype)


def select_defaults(state: dict[str, Any]) -> dict[str, Any]:
    state = ensure_trash(state)
    cats = state.get("categories") or []
    topics = state.get("topics") or []
    valid_segments = {segment["key"] for segment in STATIC_SEGMENTS}
    selected = state.get("selected") or {}
    segment_key = str(selected.get("segment_key") or DEFAULT_SEGMENT_KEY)
    if segment_key not in valid_segments:
        segment_key = DEFAULT_SEGMENT_KEY

    if not cats:
        selected["segment_key"] = segment_key
        selected["category_id"] = None
        selected["topic_id"] = None
        state["selected"] = selected
        return state

    segment_cats = [c for c in cats if c.get("segment_key") == segment_key]
    if not segment_cats:
        selected["segment_key"] = segment_key
        selected["category_id"] = None
        selected["topic_id"] = None
        state["selected"] = selected
        return state

    if selected.get("category_id") not in {c.get("id") for c in segment_cats}:
        selected["category_id"] = segment_cats[0]["id"]

    cat_id = selected["category_id"]
    cat = next((entry for entry in cats if entry.get("id") == cat_id), segment_cats[0])
    segment_key = str(cat.get("segment_key") or segment_key)
    cat_topics = [t for t in topics if t.get("category_id") == cat_id]
    if not cat_topics:
        topic_id = new_id("topic")
        topics.append(
            {
                "id": topic_id,
                "category_id": cat_id,
                "title": "New note",
                "content": "",
                "created_at": iso_now(),
                "updated_at": iso_now(),
            }
        )
        state["topics"] = topics
        selected["topic_id"] = topic_id
    elif selected.get("topic_id") not in {t.get("id") for t in cat_topics}:
        selected["topic_id"] = cat_topics[0]["id"]
    selected["segment_key"] = segment_key
    state["selected"] = selected
    return state


def app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
    method = environ["REQUEST_METHOD"]
    path = environ.get("PATH_INFO", "/")

    if method == "GET" and path == "/":
        state = select_defaults(load_state(BASE_DIR))
        save_state(BASE_DIR, state)
        body = render_index(state)
        status, headers, out = bytes_response("200 OK", body, "text/html; charset=utf-8")
        start_response(status, headers)
        return out

    if method == "GET" and path.startswith("/static/"):
        out = serve_static(path)
        if out is not None:
            status, headers, body = out
            start_response(status, headers)
            return body

    if method == "GET" and path == "/api/state":
        state = select_defaults(load_state(BASE_DIR))
        save_state(BASE_DIR, state)
        status, headers, body = json_response("200 OK", state)
        start_response(status, headers)
        return body

    if method == "POST" and path == "/api/settings":
        payload = parse_json(environ)
        state = select_defaults(load_state(BASE_DIR))

        title = str(payload.get("app_title") or "").strip() or "Trading journal"
        accent = payload.get("accent")
        font = payload.get("font")
        theme = payload.get("theme")

        state["app_title"] = title
        if accent in MATERIAL_ACCENTS:
            state["accent"] = accent
        if font in {f["key"] for f in FUNKY_ROUNDED_FONTS}:
            state["font"] = font
        if theme in {"light", "dark"}:
            state["theme"] = theme

        state = save_state(BASE_DIR, state)
        status, headers, body = json_response("200 OK", state)
        start_response(status, headers)
        return body

    if method == "POST" and path == "/api/categories":
        payload = parse_json(environ)
        name = str(payload.get("name") or "").strip()
        segment_key = str(payload.get("segment_key") or "").strip() or DEFAULT_SEGMENT_KEY
        valid_segments = {segment["key"] for segment in STATIC_SEGMENTS}
        if not name:
            status, headers, body = json_response("400 Bad Request", {"error": "Category name required"})
            start_response(status, headers)
            return body
        if segment_key not in valid_segments:
            status, headers, body = json_response("400 Bad Request", {"error": "Invalid segment_key"})
            start_response(status, headers)
            return body

        state = select_defaults(load_state(BASE_DIR))
        cat_id = new_id("cat")
        state["categories"].append({"id": cat_id, "name": name, "segment_key": segment_key, "created_at": iso_now()})
        state["selected"]["segment_key"] = segment_key
        state["selected"]["category_id"] = cat_id
        state["selected"]["topic_id"] = None
        state = select_defaults(state)
        state = save_state(BASE_DIR, state)
        status, headers, body = json_response("200 OK", state)
        start_response(status, headers)
        return body

    if method == "POST" and path == "/api/topics":
        payload = parse_json(environ)
        category_id = str(payload.get("category_id") or "").strip()
        title = str(payload.get("title") or "").strip() or "Untitled"
        state = select_defaults(load_state(BASE_DIR))

        if category_id not in {c.get("id") for c in state.get("categories", [])}:
            status, headers, body = json_response("400 Bad Request", {"error": "Invalid category_id"})
            start_response(status, headers)
            return body

        topic_id = new_id("topic")
        state["topics"].append(
            {
                "id": topic_id,
                "category_id": category_id,
                "title": title,
                "content": "",
                "created_at": iso_now(),
                "updated_at": iso_now(),
            }
        )
        state["selected"]["category_id"] = category_id
        state["selected"]["topic_id"] = topic_id
        state = save_state(BASE_DIR, state)
        status, headers, body = json_response("200 OK", state)
        start_response(status, headers)
        return body

    if path.startswith("/api/categories/"):
        category_id = path.removeprefix("/api/categories/").strip("/")
        state = ensure_trash(select_defaults(load_state(BASE_DIR)))
        categories = state.get("categories", [])
        idx = next((i for i, c in enumerate(categories) if c.get("id") == category_id), None)
        if idx is None:
            status, headers, body = json_response("404 Not Found", {"error": "Category not found"})
            start_response(status, headers)
            return body

        if method == "DELETE":
            deleted_category = dict(categories.pop(idx))
            deleted_category["deleted_at"] = iso_now()
            state["trash"]["categories"].append(deleted_category)

            kept_topics = []
            for topic in state.get("topics", []):
                if topic.get("category_id") == category_id:
                    trashed_topic = dict(topic)
                    trashed_topic["deleted_at"] = iso_now()
                    trashed_topic["deleted_with_category_id"] = category_id
                    state["trash"]["topics"].append(trashed_topic)
                else:
                    kept_topics.append(topic)
            state["categories"] = categories
            state["topics"] = kept_topics

            sel = state.get("selected") or {}
            if sel.get("category_id") == category_id:
                sel["category_id"] = None
                sel["topic_id"] = None
                state["selected"] = sel
            state = select_defaults(state)
            state = save_state(BASE_DIR, state)
            status, headers, body = json_response("200 OK", state)
            start_response(status, headers)
            return body

    if path.startswith("/api/topics/"):
        topic_id = path.removeprefix("/api/topics/").strip("/")
        state = ensure_trash(select_defaults(load_state(BASE_DIR)))
        topics = state.get("topics", [])
        idx = next((i for i, t in enumerate(topics) if t.get("id") == topic_id), None)
        if idx is None:
            status, headers, body = json_response("404 Not Found", {"error": "Topic not found"})
            start_response(status, headers)
            return body

        if method == "PUT":
            payload = parse_json(environ)
            title = str(payload.get("title") or "").strip() or "Untitled"
            content = str(payload.get("content") or "")
            topics[idx]["title"] = title
            topics[idx]["content"] = content
            topics[idx]["updated_at"] = iso_now()
            state["topics"] = topics
            state = save_state(BASE_DIR, state)
            status, headers, body = json_response("200 OK", state)
            start_response(status, headers)
            return body

        if method == "DELETE":
            deleted = dict(topics.pop(idx))
            deleted["deleted_at"] = iso_now()
            deleted["deleted_with_category_id"] = None
            state["trash"]["topics"].append(deleted)
            state["topics"] = topics
            # keep selection sane
            sel = state.get("selected") or {}
            if sel.get("topic_id") == deleted.get("id"):
                sel["topic_id"] = None
                state["selected"] = sel
                state = select_defaults(state)
            state = save_state(BASE_DIR, state)
            status, headers, body = json_response("200 OK", state)
            start_response(status, headers)
            return body

    if method == "POST" and path == "/api/trash/restore":
        payload = parse_json(environ)
        kind = str(payload.get("kind") or "").strip()
        item_id = str(payload.get("id") or "").strip()
        state = ensure_trash(select_defaults(load_state(BASE_DIR)))

        if kind == "category":
            trash_categories = state["trash"]["categories"]
            idx = next((i for i, c in enumerate(trash_categories) if c.get("id") == item_id), None)
            if idx is None:
                status, headers, body = json_response("404 Not Found", {"error": "Category not found in trash"})
                start_response(status, headers)
                return body

            restored = dict(trash_categories.pop(idx))
            restored.pop("deleted_at", None)
            state["categories"].append(restored)

            kept_trashed_topics = []
            restored_topics = []
            for topic in state["trash"]["topics"]:
                if topic.get("deleted_with_category_id") == item_id:
                    restored_topic = dict(topic)
                    restored_topic.pop("deleted_at", None)
                    restored_topic.pop("deleted_with_category_id", None)
                    restored_topics.append(restored_topic)
                else:
                    kept_trashed_topics.append(topic)
            state["trash"]["topics"] = kept_trashed_topics
            state["topics"].extend(restored_topics)
            state["selected"]["segment_key"] = restored.get("segment_key") or DEFAULT_SEGMENT_KEY
            state["selected"]["category_id"] = restored["id"]
            state["selected"]["topic_id"] = restored_topics[0]["id"] if restored_topics else None
            state = select_defaults(state)
            state = save_state(BASE_DIR, state)
            status, headers, body = json_response("200 OK", state)
            start_response(status, headers)
            return body

        if kind == "topic":
            trash_topics = state["trash"]["topics"]
            idx = next((i for i, t in enumerate(trash_topics) if t.get("id") == item_id), None)
            if idx is None:
                status, headers, body = json_response("404 Not Found", {"error": "Topic not found in trash"})
                start_response(status, headers)
                return body

            restored = dict(trash_topics[idx])
            category_id = restored.get("category_id")
            if category_id not in {c.get("id") for c in state.get("categories", [])}:
                status, headers, body = json_response("400 Bad Request", {"error": "Restore the parent category first"})
                start_response(status, headers)
                return body

            trash_topics.pop(idx)
            restored.pop("deleted_at", None)
            restored.pop("deleted_with_category_id", None)
            state["topics"].append(restored)
            state["selected"]["category_id"] = category_id
            state["selected"]["topic_id"] = restored["id"]
            category = next((c for c in state["categories"] if c["id"] == category_id), None)
            state["selected"]["segment_key"] = (category or {}).get("segment_key") or DEFAULT_SEGMENT_KEY
            state = save_state(BASE_DIR, state)
            status, headers, body = json_response("200 OK", state)
            start_response(status, headers)
            return body

        status, headers, body = json_response("400 Bad Request", {"error": "Invalid restore kind"})
        start_response(status, headers)
        return body

    if method == "POST" and path == "/api/trash/empty":
        state = ensure_trash(select_defaults(load_state(BASE_DIR)))
        state["trash"]["categories"] = []
        state["trash"]["topics"] = []
        state = save_state(BASE_DIR, state)
        status, headers, body = json_response("200 OK", state)
        start_response(status, headers)
        return body

    if method == "POST" and path == "/api/select":
        payload = parse_json(environ)
        state = select_defaults(load_state(BASE_DIR))
        sel = state.get("selected") or {}
        valid_segments = {segment["key"] for segment in STATIC_SEGMENTS}

        if "segment_key" in payload:
            segment_key = str(payload.get("segment_key") or "").strip()
            if segment_key in valid_segments:
                sel["segment_key"] = segment_key
                sel["category_id"] = None
                sel["topic_id"] = None
                state["selected"] = sel
                state = select_defaults(state)

        if "category_id" in payload:
            category_id = str(payload.get("category_id") or "").strip()
            if category_id and category_id in {c.get("id") for c in state.get("categories", [])}:
                category = next(c for c in state["categories"] if c["id"] == category_id)
                sel["segment_key"] = category.get("segment_key") or DEFAULT_SEGMENT_KEY
                sel["category_id"] = category_id
                sel["topic_id"] = None
                state["selected"] = sel
                state = select_defaults(state)

        if "topic_id" in payload:
            topic_id = str(payload.get("topic_id") or "").strip()
            if topic_id and topic_id in {t.get("id") for t in state.get("topics", [])}:
                sel["topic_id"] = topic_id
                # align category selection with the topic
                topic = next(t for t in state["topics"] if t["id"] == topic_id)
                sel["category_id"] = topic["category_id"]
                category = next((c for c in state["categories"] if c["id"] == topic["category_id"]), None)
                sel["segment_key"] = (category or {}).get("segment_key") or DEFAULT_SEGMENT_KEY
                state["selected"] = sel

        state = save_state(BASE_DIR, state)
        status, headers, body = json_response("200 OK", state)
        start_response(status, headers)
        return body

    # legacy compatibility: show state file for debugging
    if method == "GET" and path == "/api/debug/state-path":
        status, headers, body = json_response("200 OK", {"path": str(state_path(BASE_DIR))})
        start_response(status, headers)
        return body

    status, headers, body = json_response("404 Not Found", {"error": "Not found"})
    start_response(status, headers)
    return body


if __name__ == "__main__":
    # Allow overriding the port, e.g. PORT=9010 python3 app.py
    port = int(os.environ.get("PORT") or PORT)

    # If port is busy, automatically try the next few ports.
    last_error: OSError | None = None
    for attempt in range(10):
        try:
            with make_server(HOST, port, app) as server:
                print(f"Trading Journal running at http://{HOST}:{port}")
                server.serve_forever()
            last_error = None
            break
        except OSError as exc:
            last_error = exc
            if getattr(exc, "errno", None) != 48:
                raise
            port += 1

    if last_error is not None:
        raise last_error
