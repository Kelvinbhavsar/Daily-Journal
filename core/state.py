from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


MATERIAL_ACCENTS: dict[str, str] = {
    "indigo": "#3F51B5",
    "blue": "#2196F3",
    "teal": "#009688",
    "green": "#4CAF50",
    "amber": "#FFC107",
    "orange": "#FF9800",
    "deepOrange": "#FF5722",
    "pink": "#E91E63",
    "purple": "#9C27B0",
}

FUNKY_ROUNDED_FONTS: list[dict[str, str]] = [
    {"key": "fredoka", "label": "Fredoka", "css": '"Fredoka", "Segoe UI", system-ui, -apple-system, sans-serif'},
    {"key": "nunito", "label": "Nunito", "css": '"Nunito", "Segoe UI", system-ui, -apple-system, sans-serif'},
    {"key": "rubik", "label": "Rubik", "css": '"Rubik", "Segoe UI", system-ui, -apple-system, sans-serif'},
    {"key": "quicksand", "label": "Quicksand", "css": '"Quicksand", "Segoe UI", system-ui, -apple-system, sans-serif'},
    {"key": "poppins", "label": "Poppins", "css": '"Poppins", "Segoe UI", system-ui, -apple-system, sans-serif'},
]

STATIC_SEGMENTS: list[dict[str, str]] = [
    {"key": "personal", "label": "Personal"},
    {"key": "professional", "label": "Professional"},
    {"key": "spiritual", "label": "Spiritual"},
    {"key": "financial", "label": "Financial"},
    {"key": "emotional", "label": "Emotional"},
]

DEFAULT_SEGMENT_KEY = "financial"


def static_segment_keys() -> set[str]:
    return {segment["key"] for segment in STATIC_SEGMENTS}


def default_state() -> dict[str, Any]:
    cat_id = new_id("cat")
    topic_id = new_id("topic")
    return {
        "version": 3,
        "app_title": "Trading journal",
        "accent": "indigo",
        "font": "fredoka",
        "selected": {"segment_key": DEFAULT_SEGMENT_KEY, "category_id": cat_id, "topic_id": topic_id},
        "categories": [
            {
                "id": cat_id,
                "name": "General",
                "segment_key": DEFAULT_SEGMENT_KEY,
                "created_at": iso_now(),
            }
        ],
        "topics": [
            {
                "id": topic_id,
                "category_id": cat_id,
                "title": "Welcome",
                "content": "Start writing your notes here.\n\nCreate categories on the left, then add sub-topics in the middle column.",
                "created_at": iso_now(),
                "updated_at": iso_now(),
            }
        ],
        "trash": {"categories": [], "topics": []},
        "updated_at": iso_now(),
    }


def coerce_state(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return default_state()

    state = default_state()
    state.update({k: raw.get(k) for k in ("version", "app_title", "accent", "font", "categories", "topics", "trash", "selected", "updated_at") if k in raw})

    if state.get("accent") not in MATERIAL_ACCENTS:
        state["accent"] = "indigo"
    if state.get("font") not in {f["key"] for f in FUNKY_ROUNDED_FONTS}:
        state["font"] = "fredoka"

    if not isinstance(state.get("categories"), list):
        state["categories"] = default_state()["categories"]
    if not isinstance(state.get("topics"), list):
        state["topics"] = default_state()["topics"]

    if not isinstance(state.get("selected"), dict):
        state["selected"] = default_state()["selected"]
    if not isinstance(state.get("trash"), dict):
        state["trash"] = default_state()["trash"]
    if not isinstance(state["trash"].get("categories"), list):
        state["trash"]["categories"] = []
    if not isinstance(state["trash"].get("topics"), list):
        state["trash"]["topics"] = []

    valid_segments = static_segment_keys()
    normalized_categories = []
    for category in state.get("categories", []):
        if not isinstance(category, dict):
            continue
        normalized = dict(category)
        if normalized.get("segment_key") not in valid_segments:
            normalized["segment_key"] = DEFAULT_SEGMENT_KEY
        normalized_categories.append(normalized)
    state["categories"] = normalized_categories or default_state()["categories"]

    selected = dict(state.get("selected") or {})
    if selected.get("segment_key") not in valid_segments:
        selected["segment_key"] = DEFAULT_SEGMENT_KEY
    state["selected"] = selected

    return state


def migrate_from_legacy_entry(legacy: dict[str, Any]) -> dict[str, Any]:
    state = default_state()
    title = str(legacy.get("title") or "").strip()
    desc = str(legacy.get("description") or "").strip()
    if title:
        state["app_title"] = title
    if desc:
        state["topics"][0]["content"] = desc
    legacy_font = str(legacy.get("font") or "").strip()
    if legacy_font:
        # best-effort map old arbitrary fonts to nearest choice
        lower = legacy_font.lower()
        if "nunito" in lower:
            state["font"] = "nunito"
        elif "rubik" in lower:
            state["font"] = "rubik"
        elif "quick" in lower:
            state["font"] = "quicksand"
        elif "poppins" in lower:
            state["font"] = "poppins"
        else:
            state["font"] = "fredoka"
    legacy_theme = str(legacy.get("theme") or "").strip().lower()
    # map old themes to accent colors
    theme_map = {
        "ocean": "blue",
        "forest": "green",
        "sunset": "deepOrange",
        "rose": "pink",
        "slate": "indigo",
    }
    if legacy_theme in theme_map:
        state["accent"] = theme_map[legacy_theme]
    return state
