# Spec: Date Filter For Profile Page

## Overview
Step 6 adds a date-range filter to the profile page so users can slice their spending data by time period. Currently all three data sections — summary stats, transaction history, and category breakdown — always show all-time figures. This step adds a filter bar with preset buttons (Last 7 Days, Last 30 Days, This Month, All Time) and a custom date-range picker, all submitted as GET query parameters to `/profile`. The route and query helpers are updated to apply the selected range, giving users meaningful period-over-period visibility into their spending.

## Depends on
- Step 1: Database setup (`get_db()`, `expenses` table with `date` column)
- Step 2: Registration (users exist in DB)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 4: Profile page UI (template structure is in place)
- Step 5: Backend routes for profile page (`get_summary_stats`, `get_recent_transactions`, `get_category_breakdown` all exist in `database/queries.py`)

## Routes
`GET /profile` — same route, now reads optional `date_from` and `date_to` query params (format `YYYY-MM-DD`). Also reads an optional `preset` param (`7d`, `30d`, `month`, `all`) as a convenience alias that the server resolves to concrete `date_from`/`date_to` values before querying. — logged-in only.

## Database changes
No database changes. The `expenses.date` column (`TEXT`, stored as `YYYY-MM-DD`) already supports range filtering with `BETWEEN ? AND ?`.

## Templates
**Modify:** `templates/profile.html`
- Add a filter bar section between the page title and the stats row.
- Filter bar contains:
  - Four preset buttons: **Last 7 Days**, **Last 30 Days**, **This Month**, **All Time** (default active state on All Time when no params present).
  - A collapsible custom range row with two `<input type="date">` fields (`date_from`, `date_to`) and an **Apply** button.
  - The entire bar is a `<form method="GET" action="{{ url_for('profile') }}">`.
  - The currently active preset button gets a CSS modifier class (`filter-btn--active`).
- Add a filter-context label just above the stats row: e.g. *"Showing: Last 30 Days (17 May 2026 – 16 Jun 2026)"* — uses `filter_label` context variable passed from the route.
- No other structural changes.

## Files to change
- `app.py` — update `profile()` to:
  1. Read `preset`, `date_from`, `date_to` from `request.args`.
  2. Resolve `preset` to concrete `date_from`/`date_to` strings using `datetime` (today's date as the reference).
  3. If `date_from` and `date_to` are both absent and no preset, default to All Time (pass `None` for both to query helpers).
  4. Build a human-readable `filter_label` string and pass it to the template.
  5. Pass the resolved `date_from`, `date_to`, and `preset` back to the template so the active button can be highlighted.
  6. Pass all four values (`date_from`, `date_to`, `preset`, `filter_label`) alongside the existing context.
- `database/queries.py` — update all three query helpers to accept optional `date_from=None` and `date_to=None` keyword arguments:
  - When both are `None`, queries are unchanged (all-time behaviour preserved).
  - When provided, add `AND date BETWEEN ? AND ?` to the WHERE clause.
  - `get_recent_transactions` signature becomes `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)`.
  - `get_summary_stats` signature becomes `get_summary_stats(user_id, date_from=None, date_to=None)`.
  - `get_category_breakdown` signature becomes `get_category_breakdown(user_id, date_from=None, date_to=None)`.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`.
- Parameterised queries only — never f-strings or string concatenation in SQL.
- Use `datetime.date.today()` (not `datetime.datetime.now()`) to compute preset boundaries.
- Date arithmetic for "This Month" must use the first day of the current calendar month, not 30 days ago.
- Preset resolution lives in `app.py`, not in query helpers — helpers are kept dumb.
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- No inline `<style>` blocks in templates.
- Filter form must use `method="GET"` — never POST — so the filtered URL is bookmarkable.
- Never store selected date range in the session — it must live in the URL query string only.
- Validate `date_from`/`date_to` format in the route (`YYYY-MM-DD`) and silently fall back to All Time if either is malformed.
- If `date_from` is later than `date_to`, swap them before querying — do not return an error.
- Preset buttons must be `<button type="submit" name="preset" value="...">` — no JavaScript needed to activate them.
- The custom date inputs should be shown/hidden with a pure CSS toggle (checkbox hack or a `<details>` element) — no JS required.

## Definition of done
- [ ] Visiting `/profile` with no query params shows all-time data and the **All Time** button is highlighted.
- [ ] Clicking **Last 7 Days** filters all three sections (stats, transactions, breakdown) to the last 7 calendar days.
- [ ] Clicking **Last 30 Days** filters to the last 30 calendar days.
- [ ] Clicking **This Month** filters to the first day of the current month through today.
- [ ] Entering a custom `date_from` and `date_to` and clicking **Apply** filters correctly.
- [ ] The filter-context label above the stats row reflects the currently active range (e.g. "Showing: Last 7 Days (10 Jun 2026 – 16 Jun 2026)").
- [ ] A user with no expenses in the selected range sees ₹0.00 total spent, 0 transactions, and the empty-state messages — no errors or exceptions.
- [ ] Supplying a reversed range (`date_from` > `date_to`) is silently corrected and returns valid results.
- [ ] Supplying a malformed date param falls back to All Time without raising an exception.
- [ ] The filtered URL is bookmarkable — refreshing it produces the same filtered view.
- [ ] No hex colour values appear in any modified template — only CSS variables or class names.
- [ ] All amounts still display the ₹ symbol in all filtered views.
