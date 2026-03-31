# Trading Journal

<div align="center">
  <h1>Local-first trading journaling, with a "pro" writing flow</h1>
  <p>
    Create categories and subtopics, write your trading notes, and let autosave + undo/redo keep your work safe.
    Everything runs locally on your machine -- no accounts, no tracking, no external services.
  </p>
</div>

<div align="center">
  <sub>
    Built with <b>Python</b> (tiny WSGI server) + <b>vanilla JavaScript</b> (single-page UI) + <b>JSON</b> persistence.
  </sub>
</div>

---

## Why this project is different

- **Local-first storage**: your journal is saved in `data/journal_state.json` on your machine.
- **Fast, distraction-free journaling**: major categories + subtopics keep your notes organized like a mini knowledge base.
- **Autosave that actually helps**: edits are periodically persisted, and you can force-save any time.
- **Editing confidence**: browser-side undo/redo for your current writing session.
- **Personal style, built in**: pick an accent color, a rounded font, and even edit the app title.

## How to journal efficiently (recommended workflow)

1. **Create a Major Category** (left panel)  
   Example: `Strategies`, `FIIs/Institutions`, `Trading Mistakes`, `Rules`.
2. **Create a Subtopic** inside that category (middle panel)  
   Example: `Nifty mean reversion - Week 1`, `AAR/VAR notes`, `Mistake #12`.
3. **Write in the Editor** (right panel)  
   Use the notes box like your trading notebook: thesis, execution details, emotions, outcomes, and learnings.
4. **Trust Autosave** (and use Save when needed)  
   Your content is persisted without you needing manual steps.
5. **Review later instantly**  
   Switch subtopics and keep building your journal over time.

## UI Features (what you can do inside the app)

- Create categories and subtopics
- Select a topic and continue writing
- Autosave status indicator (so you know what's happening)
- Force save (`Ctrl/Cmd + S`)
- Undo/redo during editing
- Delete a subtopic (with confirmation)
- Change theme accents and fonts (persisted as settings)
- Edit the app title (top bar input)

## Technology Stack

- **Backend (Python)**: a small WSGI app served via `wsgiref.simple_server`
- **Frontend**: server-rendered HTML + `static/app.js` + `static/app.css`
- **Persistence**: a single local JSON state file
- **No framework lock-in**: plain HTML/JS makes the code easy to understand and customize

## Data model (where your journal lives)

The entire app state is stored in:

- `data/journal_state.json`

It includes:

- `categories`: major groups (name, created_at)
- `topics`: subtopics (title, content, timestamps, category_id)
- `selected`: which category/topic is currently active
- `version`: state schema version

### Legacy migration

If a legacy file exists at:

- `data/journal_entry.json`

the app will migrate it into the new `data/journal_state.json` format on first load.

## Getting Started

### Run the server

```bash
python3 app.py
```

Then open:

- `http://127.0.0.1:9000`

### Port override

If port `9000` is busy, the app can auto-increment; you can also override explicitly:

```bash
PORT=9010 python3 app.py
```

## Keyboard shortcuts

- **Save now**: `Ctrl + S` (Windows/Linux) or `Cmd + S` (macOS)
- **Undo**: `Ctrl + Z` or `Cmd + Z`
- **Redo**: `Ctrl + Y` (Windows/Linux) or `Shift + Cmd + Z`

## Customization

Theme controls are built into the app:

- Accent color: choose from the built-in set (stored in settings/state)
- Font: choose from the provided rounded fonts
- App title: editable in the top bar

If you want to add more accents/fonts, update:

- `core/state.py` (`MATERIAL_ACCENTS`, `FUNKY_ROUNDED_FONTS`)

## Backups (quick tip)

Because everything is local, consider backing up `data/journal_state.json` occasionally (for example, before major changes).
