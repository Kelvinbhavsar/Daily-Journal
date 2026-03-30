from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ENTRY_PATH = DATA_DIR / "journal_entry.json"
HOST = "127.0.0.1"
PORT = 9000


DEFAULT_ENTRY: dict[str, Any] = {
    "title": "",
    "description": "",
    "theme": "ocean",
    "font": "Georgia",
    "updated_at": None,
}

THEMES: dict[str, dict[str, str]] = {
    "ocean": {
        "bg": "#f3fbff",
        "panel": "#ffffff",
        "text": "#0f172a",
        "muted": "#475569",
        "accent": "#0284c7",
        "border": "#bae6fd",
    },
    "forest": {
        "bg": "#f4fbf6",
        "panel": "#ffffff",
        "text": "#132a13",
        "muted": "#4f6f52",
        "accent": "#2d6a4f",
        "border": "#b7e4c7",
    },
    "sunset": {
        "bg": "#fff6f1",
        "panel": "#ffffff",
        "text": "#431407",
        "muted": "#7c2d12",
        "accent": "#ea580c",
        "border": "#fed7aa",
    },
    "rose": {
        "bg": "#fff5f7",
        "panel": "#ffffff",
        "text": "#4a044e",
        "muted": "#9d174d",
        "accent": "#db2777",
        "border": "#fbcfe8",
    },
    "slate": {
        "bg": "#f8fafc",
        "panel": "#ffffff",
        "text": "#111827",
        "muted": "#4b5563",
        "accent": "#334155",
        "border": "#cbd5e1",
    },
}

FONTS = [
    "Georgia",
    "Times New Roman",
    "Trebuchet MS",
    "Verdana",
    "Courier New",
    "Palatino",
    "Garamond",
    "Tahoma",
    "Lucida Sans Unicode",
    "Book Antiqua",
    "Segoe UI",
    "Arial",
]


def ensure_storage() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not ENTRY_PATH.exists():
        payload = DEFAULT_ENTRY.copy()
        with ENTRY_PATH.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)


def load_entry() -> dict[str, Any]:
    ensure_storage()
    with ENTRY_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    entry = DEFAULT_ENTRY.copy()
    entry.update(data)
    if entry["theme"] not in THEMES:
        entry["theme"] = DEFAULT_ENTRY["theme"]
    if entry["font"] not in FONTS:
        entry["font"] = DEFAULT_ENTRY["font"]
    return entry


def save_entry(entry: dict[str, Any]) -> dict[str, Any]:
    ensure_storage()
    payload = DEFAULT_ENTRY.copy()
    payload.update(
        {
            "title": str(entry.get("title", "")).strip(),
            "description": str(entry.get("description", "")).strip(),
            "theme": entry.get("theme", DEFAULT_ENTRY["theme"]),
            "font": entry.get("font", DEFAULT_ENTRY["font"]),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    if payload["theme"] not in THEMES:
        payload["theme"] = DEFAULT_ENTRY["theme"]
    if payload["font"] not in FONTS:
        payload["font"] = DEFAULT_ENTRY["font"]

    with ENTRY_PATH.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
    return payload


def render_page(entry: dict[str, Any]) -> bytes:
    theme_options = "".join(
        (
            f'<option value="{name}"{" selected" if entry["theme"] == name else ""}>'
            f"{name.title()}</option>"
        )
        for name in THEMES
    )
    font_options = "".join(
        (
            f'<option value="{font}"{" selected" if entry["font"] == font else ""}>'
            f"{font}</option>"
        )
        for font in FONTS
    )
    theme_json = json.dumps(THEMES)
    font_json = json.dumps(FONTS)
    updated_at = entry.get("updated_at") or "Not saved yet"
    title = html_escape(entry.get("title", ""))
    description = html_escape(entry.get("description", ""))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Trading Journal</title>
  <style>
    :root {{
      --bg: {THEMES[entry["theme"]]["bg"]};
      --panel: {THEMES[entry["theme"]]["panel"]};
      --text: {THEMES[entry["theme"]]["text"]};
      --muted: {THEMES[entry["theme"]]["muted"]};
      --accent: {THEMES[entry["theme"]]["accent"]};
      --border: {THEMES[entry["theme"]]["border"]};
      --font-choice: "{css_escape(entry["font"])}";
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      min-height: 100vh;
      font-family: var(--font-choice), serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, color-mix(in srgb, var(--accent) 16%, transparent), transparent 32%),
        linear-gradient(135deg, var(--bg), #ffffff 52%, color-mix(in srgb, var(--bg) 72%, white));
      transition: background 0.25s ease, color 0.25s ease, font-family 0.25s ease;
    }}

    .shell {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}

    .hero {{
      display: grid;
      gap: 24px;
      grid-template-columns: 1.15fr 0.85fr;
      align-items: start;
    }}

    .card {{
      background: color-mix(in srgb, var(--panel) 90%, white);
      border: 1px solid var(--border);
      border-radius: 24px;
      box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
      backdrop-filter: blur(12px);
    }}

    .intro {{
      padding: 28px;
    }}

    .intro h1 {{
      margin: 0 0 12px;
      font-size: clamp(2.1rem, 4vw, 3.6rem);
      line-height: 0.95;
      letter-spacing: -0.04em;
    }}

    .intro p {{
      margin: 0;
      max-width: 44ch;
      color: var(--muted);
      font-size: 1.02rem;
      line-height: 1.7;
    }}

    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 24px;
    }}

    .meta-tile {{
      padding: 16px 18px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.55);
      border: 1px solid var(--border);
    }}

    .meta-tile span {{
      display: block;
      color: var(--muted);
      font-size: 0.85rem;
      margin-bottom: 6px;
    }}

    .meta-tile strong {{
      font-size: 1rem;
    }}

    .controls {{
      padding: 24px;
    }}

    .controls h2,
    .editor h2 {{
      margin: 0 0 16px;
      font-size: 1.15rem;
    }}

    label {{
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
    }}

    select,
    input[type="text"],
    textarea {{
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.88);
      color: var(--text);
      padding: 14px 16px;
      font: inherit;
      outline: none;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}

    select:focus,
    input[type="text"]:focus,
    textarea:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 16%, transparent);
    }}

    .control-group + .control-group {{
      margin-top: 16px;
    }}

    .editor {{
      margin-top: 22px;
      padding: 24px;
    }}

    textarea {{
      min-height: 320px;
      resize: vertical;
      line-height: 1.65;
    }}

    .action-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-top: 18px;
      flex-wrap: wrap;
    }}

    button {{
      border: none;
      border-radius: 999px;
      background: var(--accent);
      color: white;
      padding: 14px 20px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 14px 28px color-mix(in srgb, var(--accent) 25%, transparent);
    }}

    button:hover {{
      filter: brightness(1.04);
    }}

    .status {{
      color: var(--muted);
      font-size: 0.95rem;
    }}

    .footer-note {{
      margin-top: 20px;
      color: var(--muted);
      font-size: 0.95rem;
    }}

    @media (max-width: 860px) {{
      .hero {{
        grid-template-columns: 1fr;
      }}

      .meta-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="card intro">
        <h1>Trading Journal</h1>
        <p>Capture setups, mistakes, emotions, and lessons in one local-first journal that runs on your own machine at 127.0.0.1:9000.</p>
        <div class="meta-grid">
          <div class="meta-tile">
            <span>Storage</span>
            <strong>{html_escape(str(ENTRY_PATH))}</strong>
          </div>
          <div class="meta-tile">
            <span>Autosave</span>
            <strong>Every 1 minute</strong>
          </div>
          <div class="meta-tile">
            <span>Themes</span>
            <strong>5 switchable color styles</strong>
          </div>
          <div class="meta-tile">
            <span>Fonts</span>
            <strong>{len(FONTS)} selectable text styles</strong>
          </div>
        </div>
      </div>

      <aside class="card controls">
        <h2>Appearance</h2>
        <div class="control-group">
          <label for="theme">Color theme</label>
          <select id="theme" name="theme">{theme_options}</select>
        </div>
        <div class="control-group">
          <label for="font">Font style</label>
          <select id="font" name="font">{font_options}</select>
        </div>
        <p class="footer-note">Your title, description, theme, and font are all saved to local disk on manual save and on each autosave.</p>
      </aside>
    </section>

    <section class="card editor">
      <h2>Journal Entry</h2>
      <form id="journal-form">
        <div class="control-group">
          <label for="title">Title</label>
          <input id="title" name="title" type="text" placeholder="Example: Nifty breakout trade review" value="{title}">
        </div>
        <div class="control-group">
          <label for="description">Description</label>
          <textarea id="description" name="description" placeholder="Write your trade notes, mindset, entry reason, exit reason, and lesson here...">{description}</textarea>
        </div>
        <div class="action-row">
          <button type="submit">Save Now</button>
          <div class="status" id="status">Last saved: {html_escape(updated_at)}</div>
        </div>
      </form>
    </section>
  </main>

  <script>
    const THEMES = {theme_json};
    const FONTS = {font_json};
    const form = document.getElementById("journal-form");
    const titleInput = document.getElementById("title");
    const descriptionInput = document.getElementById("description");
    const themeSelect = document.getElementById("theme");
    const fontSelect = document.getElementById("font");
    const status = document.getElementById("status");

    function applyAppearance() {{
      const theme = THEMES[themeSelect.value] || THEMES.ocean;
      document.documentElement.style.setProperty("--bg", theme.bg);
      document.documentElement.style.setProperty("--panel", theme.panel);
      document.documentElement.style.setProperty("--text", theme.text);
      document.documentElement.style.setProperty("--muted", theme.muted);
      document.documentElement.style.setProperty("--accent", theme.accent);
      document.documentElement.style.setProperty("--border", theme.border);
      const font = FONTS.includes(fontSelect.value) ? fontSelect.value : "Georgia";
      document.documentElement.style.setProperty("--font-choice", `"${{font}}"`);
    }}

    async function persistEntry(reason) {{
      const payload = new URLSearchParams();
      payload.set("title", titleInput.value);
      payload.set("description", descriptionInput.value);
      payload.set("theme", themeSelect.value);
      payload.set("font", fontSelect.value);

      status.textContent = reason === "autosave" ? "Autosaving..." : "Saving...";

      try {{
        const response = await fetch("/save", {{
          method: "POST",
          headers: {{
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
          }},
          body: payload.toString(),
        }});

        if (!response.ok) {{
          throw new Error("Save failed");
        }}

        const data = await response.json();
        status.textContent = `Last saved: ${{data.updated_at}}`;
      }} catch (error) {{
        status.textContent = "Save failed. Please try again.";
      }}
    }}

    form.addEventListener("submit", async (event) => {{
      event.preventDefault();
      await persistEntry("manual");
    }});

    themeSelect.addEventListener("change", applyAppearance);
    fontSelect.addEventListener("change", applyAppearance);
    applyAppearance();

    window.setInterval(() => {{
      persistEntry("autosave");
    }}, 60000);
  </script>
</body>
</html>
"""
    return html.encode("utf-8")


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def css_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def json_response(status: str, payload: dict[str, Any]) -> list[bytes]:
    body = json.dumps(payload).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ]
    return status, headers, [body]


def app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
    method = environ["REQUEST_METHOD"]
    path = environ.get("PATH_INFO", "/")

    if method == "GET" and path == "/":
        entry = load_entry()
        body = render_page(entry)
        start_response(
            "200 OK",
            [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(body))),
            ],
        )
        return [body]

    if method == "POST" and path == "/save":
        size = int(environ.get("CONTENT_LENGTH") or 0)
        raw_body = environ["wsgi.input"].read(size).decode("utf-8")
        params = parse_qs(raw_body)
        saved_entry = save_entry(
            {
                "title": params.get("title", [""])[0],
                "description": params.get("description", [""])[0],
                "theme": params.get("theme", [DEFAULT_ENTRY["theme"]])[0],
                "font": params.get("font", [DEFAULT_ENTRY["font"]])[0],
            }
        )
        status, headers, body = json_response("200 OK", saved_entry)
        start_response(status, headers)
        return body

    status, headers, body = json_response("404 Not Found", {"error": "Not found"})
    start_response(status, headers)
    return body


if __name__ == "__main__":
    ensure_storage()
    with make_server(HOST, PORT, app) as server:
        print(f"Trading Journal running at http://{HOST}:{PORT}")
        server.serve_forever()
