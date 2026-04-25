from __future__ import annotations

import re
from datetime import datetime
from difflib import SequenceMatcher
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

EMOTION_OPTIONS: list[dict[str, str]] = [
    {"key": "normal", "emoji": "🙂", "label": "Normal"},
    {"key": "happy", "emoji": "😄", "label": "Happy"},
    {"key": "calm", "emoji": "😌", "label": "Calm"},
    {"key": "focused", "emoji": "🤓", "label": "Focused"},
    {"key": "confident", "emoji": "😎", "label": "Confident"},
    {"key": "anxious", "emoji": "😟", "label": "Anxious"},
    {"key": "frustrated", "emoji": "😤", "label": "Frustrated"},
    {"key": "tired", "emoji": "😴", "label": "Tired"},
]
DEFAULT_EMOTION_KEY = "normal"

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
THEMES = {"light", "dark"}


def static_segment_keys() -> set[str]:
    return {segment["key"] for segment in STATIC_SEGMENTS}


def emotion_keys() -> set[str]:
    return {emotion["key"] for emotion in EMOTION_OPTIONS}


def split_paragraphs(content: str) -> list[str]:
    normalized = str(content or "").replace("\r\n", "\n")
    parts = [part.strip() for part in re.split(r"\n\s*\n+", normalized) if part.strip()]
    return parts


def paragraph_records_from_content(content: str, fallback_updated_at: str) -> list[dict[str, str]]:
    return [
        {"text": paragraph, "updated_at": fallback_updated_at, "mood": DEFAULT_EMOTION_KEY}
        for paragraph in split_paragraphs(content)
    ]


def normalize_topic(topic: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(topic)
    fallback_updated_at = str(normalized.get("updated_at") or iso_now())
    content = str(normalized.get("content") or "")
    paragraphs = normalized.get("paragraphs")
    if not isinstance(paragraphs, list):
        normalized["paragraphs"] = paragraph_records_from_content(content, fallback_updated_at)
        return normalized

    normalized_paragraphs = []
    valid_moods = emotion_keys()
    for paragraph in paragraphs:
        if not isinstance(paragraph, dict):
            continue
        text = str(paragraph.get("text") or "").strip()
        if not text:
            continue
        mood = str(paragraph.get("mood") or DEFAULT_EMOTION_KEY)
        if mood not in valid_moods:
            mood = DEFAULT_EMOTION_KEY
        normalized_paragraphs.append(
            {
                "text": text,
                "updated_at": str(paragraph.get("updated_at") or fallback_updated_at),
                "mood": mood,
            }
        )
    normalized["paragraphs"] = normalized_paragraphs or paragraph_records_from_content(content, fallback_updated_at)
    return normalized


def merge_paragraph_updates(
    existing_paragraphs: list[dict[str, Any]] | None, incoming_paragraphs: list[dict[str, Any]] | None, updated_at: str
) -> list[dict[str, str]]:
    previous = []
    valid_moods = emotion_keys()
    for paragraph in existing_paragraphs or []:
        if not isinstance(paragraph, dict):
            continue
        text = str(paragraph.get("text") or "").strip()
        if not text:
            continue
        previous.append(
            {
                "text": text,
                "updated_at": str(paragraph.get("updated_at") or updated_at),
                "mood": str(paragraph.get("mood") or DEFAULT_EMOTION_KEY),
            }
        )

    current = []
    for paragraph in incoming_paragraphs or []:
        if not isinstance(paragraph, dict):
            continue
        text = str(paragraph.get("text") or "").strip()
        if not text:
            continue
        mood = str(paragraph.get("mood") or DEFAULT_EMOTION_KEY)
        if mood not in valid_moods:
            mood = DEFAULT_EMOTION_KEY
        current.append(
            {
                "text": text,
                "mood": mood,
            }
        )
    if not previous:
        return [
            {"text": paragraph["text"], "updated_at": updated_at, "mood": paragraph["mood"]}
            for paragraph in current
        ]

    matcher = SequenceMatcher(a=[item["text"] for item in previous], b=[item["text"] for item in current])
    merged: list[dict[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            merged.extend(
                {
                    "text": previous[index]["text"],
                    "updated_at": previous[index]["updated_at"],
                    "mood": current[j1 + (index - i1)]["mood"],
                }
                for index in range(i1, i2)
            )
            continue
        if tag in {"replace", "insert"}:
            merged.extend(
                {
                    "text": paragraph["text"],
                    "updated_at": updated_at,
                    "mood": paragraph["mood"],
                }
                for paragraph in current[j1:j2]
            )
    return merged


def default_state() -> dict[str, Any]:
    cat_id = new_id("cat")
    topic_id = new_id("topic")
    topic_updated_at = iso_now()
    return {
        "version": 3,
        "app_title": "Daily-Journal",
        "accent": "indigo",
        "font": "fredoka",
        "theme": "light",
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
                "content": "Start writing your notes here.\n\nOpen a main thread on the left, then add topics in the middle column.",
                "paragraphs": [
                    {
                        "text": "Start writing your notes here.",
                        "updated_at": topic_updated_at,
                        "mood": DEFAULT_EMOTION_KEY,
                    },
                    {
                        "text": "Open a main thread on the left, then add topics in the middle column.",
                        "updated_at": topic_updated_at,
                        "mood": DEFAULT_EMOTION_KEY,
                    },
                ],
                "created_at": topic_updated_at,
                "updated_at": topic_updated_at,
            }
        ],
        "trash": {"categories": [], "topics": []},
        "updated_at": iso_now(),
    }


def coerce_state(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return default_state()

    state = default_state()
    state.update({k: raw.get(k) for k in ("version", "app_title", "accent", "font", "theme", "categories", "topics", "trash", "selected", "updated_at") if k in raw})
    state["version"] = 4

    if state.get("accent") not in MATERIAL_ACCENTS:
        state["accent"] = "indigo"
    if state.get("font") not in {f["key"] for f in FUNKY_ROUNDED_FONTS}:
        state["font"] = "fredoka"
    if state.get("theme") not in THEMES:
        state["theme"] = "light"

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

    normalized_topics = []
    for topic in state.get("topics", []):
        if not isinstance(topic, dict):
            continue
        normalized_topics.append(normalize_topic(topic))
    state["topics"] = normalized_topics or default_state()["topics"]

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
        state["topics"][0]["paragraphs"] = paragraph_records_from_content(desc, state["topics"][0]["updated_at"])
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
