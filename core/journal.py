from __future__ import annotations

from pathlib import Path
from typing import Any

from core.state import coerce_state, default_state, iso_now, migrate_from_legacy_entry
from core.storage import read_json, write_json


def state_path(base_dir: Path) -> Path:
    return base_dir / "data" / "journal_state.json"


def legacy_path(base_dir: Path) -> Path:
    return base_dir / "data" / "journal_entry.json"


def load_state(base_dir: Path) -> dict[str, Any]:
    path = state_path(base_dir)
    raw = read_json(path)
    if raw is not None:
        return coerce_state(raw)

    legacy = read_json(legacy_path(base_dir))
    if legacy is not None:
        state = migrate_from_legacy_entry(legacy)
        write_json(path, state)
        return state

    state = default_state()
    write_json(path, state)
    return state


def save_state(base_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    state = coerce_state(state)
    state["updated_at"] = iso_now()
    write_json(state_path(base_dir), state)
    return state
