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
      <div class="brand">
        <div class="brand__mark" aria-hidden="true"></div>
        <div class="brand__titleWrap">
          <input id="appTitle" class="brand__title" type="text" value="{_html_escape(title)}" aria-label="App title">
        </div>
      </div>

      <div class="topbar__right">
        <div class="control">
          <label class="control__label" for="accent">Color</label>
          <select id="accent" class="control__select" aria-label="Accent color"></select>
        </div>
        <div class="control">
          <label class="control__label" for="font">Font</label>
          <select id="font" class="control__select" aria-label="Font"></select>
        </div>
      </div>
    </header>

    <div id="subbar" class="subbar subbar--hidden">
      <button id="homeToggle" class="subbar__tab subbar__tab--active" type="button">Categories</button>
      <div id="breadcrumb" class="subbar__crumb">Local first • Main Threads + Topics</div>
      <div class="subbar__actions">
        <button id="newCategory" class="btn" type="button">New Main Thread</button>
        <button id="newTopic" class="btn" type="button">New Topic</button>
      </div>
    </div>

    <main class="workspace">
      <section id="homeView" class="homeView" aria-label="Segments overview">
        <div class="hero">
          <div class="hero__content">
            <div class="eyebrow">Dashboard</div>
            <h1 class="hero__title">Your Life Segments</h1>
            <p class="hero__copy">Click any segment to open its main threads, see their topics, and continue writing without leaving the page.</p>
          </div>
          <aside class="statsCard" aria-label="Global stats">
            <div class="statsCard__label">Global Stats</div>
            <div id="statsSummary" class="statsCard__value">0 total entries</div>
            <div id="statsDetail" class="statsCard__sub">0 categories</div>
          </aside>
        </div>

        <div id="segmentGrid" class="segmentGrid" aria-label="Category segments"></div>
        <button id="openTrash" class="floatingTrash" type="button" aria-label="Open trash">
          <svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
        </button>
        <section id="trashPanel" class="trashPanel trashPanel--hidden" aria-label="Deleted items">
          <div class="trashPanel__head">
            <div>
              <div class="trashPanel__title">Trash Bin</div>
              <div class="trashPanel__hint">Restore deleted main threads and topics from here.</div>
            </div>
            <button id="closeTrash" class="btn btn--ghost" type="button">Close</button>
          </div>
          <div id="trashList" class="trashList"></div>
        </section>
      </section>

      <section id="detailView" class="detailView detailView--hidden" aria-label="Category detail view">
        <div class="detailShell">
          <aside class="detailPanel detailPanel--categories">
            <button id="backToHome" class="backButton" type="button">Back to Segments</button>
            
            <div class="browserPanel">
              <div class="browserPanel__head">
                <div class="browserPanel__title">Main Threads</div>
                <div class="browserPanel__hint">Open a main thread inside this static segment</div>
              </div>
              <div id="categoryList" class="browserStack"></div>
            </div>
          </aside>

          <aside class="detailPanel detailPanel--topics">
            <div class="browserPanel">
              <div class="browserPanel__head">
                <div class="browserPanel__title">Topics</div>
                <div class="browserPanel__hint">Vertical scrolling column for your notes</div>
              </div>
              <div id="topicList" class="browserStack browserStack--topics"></div>
            </div>
          </aside>

          <section class="editorPanel" aria-label="Writing area">
            <div class="editorCard">
              <div class="editorCard__header">
                <div class="editorCard__titleWrap">
                  <div class="editorCard__eyebrow">Journal Entry</div>
                  <input id="topicTitle" class="editor__title" type="text" placeholder="Topic title">
                </div>
                <div class="editor__meta">
                  <span id="saveStatus" class="badge badge--status">Ready</span>
                  <div class="editor__actions" role="toolbar" aria-label="Editor actions">
                    <button id="undoBtn" class="btn btn--ghost btn--icon" type="button" title="Undo (⌘Z / Ctrl+Z)" aria-label="Undo">
                      <svg class="btn__icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"/></svg>
                    </button>
                    <button id="redoBtn" class="btn btn--ghost btn--icon" type="button" title="Redo (⇧⌘Z / Ctrl+Y)" aria-label="Redo">
                      <svg class="btn__icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 7v6h-6"/><path d="M3 17a9 9 0 0 1 9-9 9 9 0 0 1 6 2.3L21 13"/></svg>
                    </button>
                    <button id="saveNowBtn" class="btn btn--ghost btn--icon" type="button" title="Save (⌘S / Ctrl+S)" aria-label="Save">
                      <svg class="btn__icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                    </button>
                  </div>
                </div>
              </div>
              <textarea id="topicContent" class="editor__textarea" placeholder="Write your journal notes here..."></textarea>
            </div>
          </section>
        </div>
      </section>
    </main>
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
