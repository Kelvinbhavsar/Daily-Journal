from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from wsgiref.simple_server import make_server

from core.journal import load_state, save_state, state_path
from core.state import FUNKY_ROUNDED_FONTS, MATERIAL_ACCENTS, iso_now, new_id
from core.storage import read_json
from ui.page import render_index


BASE_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 9000


STATIC_DIR = BASE_DIR / "static"


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
    return bytes_response("200 OK", body, ctype)


def select_defaults(state: dict[str, Any]) -> dict[str, Any]:
    cats = state.get("categories") or []
    topics = state.get("topics") or []
    if not cats:
        cat_id = new_id("cat")
        cats = [{"id": cat_id, "name": "General", "created_at": iso_now()}]
        state["categories"] = cats
    selected = state.get("selected") or {}
    if selected.get("category_id") not in {c.get("id") for c in cats}:
        selected["category_id"] = cats[0]["id"]
    cat_id = selected["category_id"]
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

        state["app_title"] = title
        if accent in MATERIAL_ACCENTS:
            state["accent"] = accent
        if font in {f["key"] for f in FUNKY_ROUNDED_FONTS}:
            state["font"] = font

        state = save_state(BASE_DIR, state)
        status, headers, body = json_response("200 OK", state)
        start_response(status, headers)
        return body

    if method == "POST" and path == "/api/categories":
        payload = parse_json(environ)
        name = str(payload.get("name") or "").strip()
        if not name:
            status, headers, body = json_response("400 Bad Request", {"error": "Category name required"})
            start_response(status, headers)
            return body

        state = select_defaults(load_state(BASE_DIR))
        cat_id = new_id("cat")
        state["categories"].append({"id": cat_id, "name": name, "created_at": iso_now()})
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

    if path.startswith("/api/topics/"):
        topic_id = path.removeprefix("/api/topics/").strip("/")
        state = select_defaults(load_state(BASE_DIR))
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
            deleted = topics.pop(idx)
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

    if method == "POST" and path == "/api/select":
        payload = parse_json(environ)
        state = select_defaults(load_state(BASE_DIR))
        sel = state.get("selected") or {}

        if "category_id" in payload:
            category_id = str(payload.get("category_id") or "").strip()
            if category_id and category_id in {c.get("id") for c in state.get("categories", [])}:
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
