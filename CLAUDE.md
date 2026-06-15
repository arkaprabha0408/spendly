# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
python app.py          # starts Flask dev server at http://localhost:5001
```

Dependencies are in `requirements.txt`. Install into a virtualenv (`myenv/` is gitignored):

```bash
pip install -r requirements.txt
```

## Running tests

```bash
pytest                 # run all tests
pytest tests/test_foo.py::test_bar   # run a single test
```

Test stack: `pytest` + `pytest-flask`. No tests exist yet — they will be added as features are built.

## Architecture

This is a **Flask + Jinja2 + SQLite** app. There is no JavaScript framework; all interactivity is server-rendered.

spendly/
├── app.py # All routes — single file, no blueprints
├── database/
│ └── db.py # SQLite helpers: get_db(), init_db(), seed_db()
├── templates/
│ ├── base.html # Shared layout — all templates must extend this
│ └── \*.html # One template per page
├── static/
│ ├── css/
│ │ ├── style.css # Global styles
│ │ └── landing.css # Landing-page-only styles
│ └── js/
│ └── main.js # Vanilla JS only
└── requirements.txt

Where things belong:

New routes → app.py only, no blueprints
DB logic → database/db.py only, never inline in routes
New pages → new .html file extending base.html
Page-specific styles → new .css file, not inline <style> tags

### Request flow

```
browser → app.py (route) → render_template(*.html) → templates/base.html (layout shell)
```

All pages extend `templates/base.html`, which provides the sticky navbar, footer (with Terms/Privacy links), and loads `static/css/style.css` and `static/js/main.js`.

### Code style

Python: PEP 8, snake_case for all variables and functions
Templates: Jinja2 with url_for() for every internal link — never hardcode URLs
Route functions: one responsibility only — fetch data, render template, done
DB queries: always use parameterized queries (? placeholders) — never f-strings in SQL
Error handling: use abort() for HTTP errors, not bare return "error string"

### Tech constraints

Flask only — no FastAPI, no Django, no other web frameworks
SQLite only — no PostgreSQL, no SQLAlchemy ORM, no external DB
Vanilla JS only — no React, no jQuery, no npm packages
No new pip packages — work within requirements.txt as-is unless explicitly told otherwise
Python 3.10+ assumed — f-strings and match statements are fine

### Subagent Policy

Always use a builtin explore subagent for codebase exploration before implementing any new feature
Always use a subagent to verify test results after any implementation
When asked to plan, delegate codebase research to a subagent before presenting the plan
always use a builtin plan subagent in plan mode

### Route map (`app.py`)

| Route                          | Status         | Notes                                             |
| ------------------------------ | -------------- | ------------------------------------------------- |
| `GET /`                        | done           | landing page                                      |
| `GET /register`                | done (UI only) | form POSTs to `/register` — handler not yet wired |
| `GET /login`                   | done (UI only) | form POSTs to `/login` — handler not yet wired    |
| `GET /terms`                   | done           | static page                                       |
| `GET /privacy`                 | done           | static page                                       |
| `GET /logout`                  | placeholder    | Step 3                                            |
| `GET /profile`                 | placeholder    | Step 4                                            |
| `GET /expenses/add`            | placeholder    | Step 7                                            |
| `GET/POST /expenses/<id>/edit` | placeholder    | Step 8                                            |
| `GET /expenses/<id>/delete`    | placeholder    | Step 9                                            |

### Database (`database/db.py`)

Placeholder file. Students implement it in Step 1. It must export:

- `get_db()` — SQLite connection with `row_factory` and foreign keys enabled
- `init_db()` — `CREATE TABLE IF NOT EXISTS` for all tables
- `seed_db()` — sample data for development

### CSS design system (`static/css/style.css`)

Single stylesheet. Key conventions:

- **Fonts**: `--font-display` (DM Serif Display, for headings/numbers) and `--font-body` (DM Sans)
- **Colours**: `--ink` (near-black), `--accent` (forest green `#1a472a`), `--accent-2` (amber), `--danger` (red)
- **Landing page hero** uses `lp-*` prefixed classes (badge, title, browser mockup, stat cards, bar chart)
- **Auth pages** use `auth-*` prefixed classes
- **Terms/Privacy pages** use `terms-*` prefixed classes
- Responsive breakpoints: 900px (features grid collapses) and 600px (nav collapses, stat cards stack)

### Warnings and things to avoid

Never use raw string returns for stub routes once a step is implemented — always render a template
Never hardcode URLs in templates — always use url_for()
Never put DB logic in route functions — it belongs in database/db.py
Never install new packages mid-feature without flagging it — keep requirements.txt in sync
Never use JS frameworks — the frontend is intentionally vanilla
database/db.py is currently empty — do not assume helpers exist until the step that implements them
FK enforcement is manual — SQLite foreign keys are off by default; get_db() must run PRAGMA foreign_keys = ON on every connection
The app runs on port 5001, not the Flask default 5000 — don't change this
