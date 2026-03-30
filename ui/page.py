from __future__ import annotations

import json
from typing import Any

from core.state import FUNKY_ROUNDED_FONTS, MATERIAL_ACCENTS


def render_index(state: dict[str, Any]) -> bytes:
    title = str(state.get("app_title") or "Trading journal")
    accents = json.dumps(MATERIAL_ACCENTS)
    fonts = json.dumps(FUNKY_ROUNDED_FONTS)
    initial = json.dumps(
        {
            "app_title": title,
            "accent": state.get("accent"),
            "font": state.get("font"),
            "selected": state.get("selected"),
        }
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_html_escape(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&family=Nunito:wght@400;600;700&family=Poppins:wght@400;600;700&family=Quicksand:wght@400;600;700&family=Rubik:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/app.css">
</head>
<body>
  <div id="app" class="app" aria-label="Trading journal app">
    <header class="topbar">
      <div class="topbar__left">
        <div class="brand">
          <div class="brand__mark" aria-hidden="true"></div>
          <div class="brand__titleWrap">
            <input id="appTitle" class="brand__title" type="text" value="{_html_escape(title)}" aria-label="App title">
            <div class="brand__sub">Local-first • Categories • Subtopics</div>
          </div>
        </div>
      </div>
      <div class="topbar__right">
        <button id="undoBtn" class="btn btn--ghost" type="button" title="Undo (⌘Z / Ctrl+Z)">Undo</button>
        <button id="redoBtn" class="btn btn--ghost" type="button" title="Redo (⇧⌘Z / Ctrl+Y)">Redo</button>
        <button id="saveNowBtn" class="btn btn--ghost" type="button" title="Save now (⌘S / Ctrl+S)">Save</button>
        <div class="control">
          <label class="control__label" for="accent">Color</label>
          <select id="accent" class="control__select" aria-label="Accent color"></select>
        </div>
        <div class="control">
          <label class="control__label" for="font">Font</label>
          <select id="font" class="control__select" aria-label="Font"></select>
        </div>
        <button id="newCategory" class="btn btn--ghost" type="button">New category</button>
        <button id="newTopic" class="btn" type="button">New subtopic</button>
      </div>
    </header>

    <div class="content">
      <aside class="panel panel--left" aria-label="Major categories">
        <div class="panel__header">
          <div class="panel__title">Categories</div>
          <div class="panel__hint">Major topics</div>
        </div>
        <div id="categoryList" class="list"></div>
      </aside>

      <aside class="panel panel--mid" aria-label="Subtopics list">
        <div class="panel__header">
          <div class="panel__title">Subtopics</div>
          <div class="panel__hint">Within selected category</div>
        </div>
        <div id="topicList" class="list"></div>
      </aside>

      <main class="editor" aria-label="Writing area">
        <div class="editor__header">
          <input id="topicTitle" class="editor__title" type="text" placeholder="Subtopic title">
          <div class="editor__meta">
            <span id="saveStatus" class="badge">Ready</span>
            <button id="deleteTopic" class="btn btn--danger btn--ghost" type="button">Delete</button>
          </div>
        </div>
        <textarea id="topicContent" class="editor__textarea" placeholder="Write your trading notes…"></textarea>
      </main>
    </div>
  </div>

  <script>
    window.__ACCENTS__ = {accents};
    window.__FONTS__ = {fonts};
    window.__INITIAL__ = {initial};
  </script>
  <script src="/static/app.js"></script>
</body>
</html>
"""
    return html.encode("utf-8")


def _html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
