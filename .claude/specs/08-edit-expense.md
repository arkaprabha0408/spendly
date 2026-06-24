# Spec: Edit Expense

## Overview
Step 8 upgrades the placeholder `GET /expenses/<id>/edit` route into a fully functional edit form, and adds a `POST /expenses/<id>/edit` handler to validate and persist updates. The pre-filled form lets logged-in users correct mistakes (wrong amount, wrong category, wrong date) without having to delete and re-add entries. Two new DB helpers are added to `database/db.py`: one to fetch a single expense by id (with ownership check) and one to update it. On success the user is redirected back to `/profile` so the corrected entry is immediately visible. Edit links are wired into the existing transactions table on the profile page.

## Depends on
- Step 1: Database setup (`get_db()`, `expenses` table with `user_id`, `amount`, `category`, `date`, `description` columns)
- Step 2: Registration (users exist in DB)
- Step 3: Login / Logout (`session["user_id"]` is set on login, logout clears it)
- Step 4: Profile page (source of edit links, destination after a successful update)
- Step 5: Backend routes for profile page (`get_recent_transactions()` populates the list where edit links live)
- Step 7: Add Expense (established the `VALID_CATEGORIES` constant in `app.py` and the `expenses` rows to edit)

## Routes
- `GET /expenses/<int:id>/edit` — fetch expense by id, render pre-filled edit form — logged-in only
- `POST /expenses/<int:id>/edit` — validate fields, update expense row, redirect to `/profile` — logged-in only

## Database changes
No new tables or columns. The existing `expenses` schema covers all required fields:

```
expenses(id, user_id, amount, category, date, description, created_at)
```

Two new helper functions are added to `database/db.py`:

- `get_expense_by_id(expense_id, user_id)` — returns the expense row if it exists **and** belongs to `user_id`, otherwise returns `None`.
- `update_expense(expense_id, user_id, amount, category, date, description)` — updates `amount`, `category`, `date`, `description` on the matching row; uses `WHERE id = ? AND user_id = ?` to prevent cross-user writes.

## Templates
**Create:** `templates/edit_expense.html`
- Extends `base.html`.
- Contains a single `<form method="POST" action="{{ url_for('edit_expense', id=expense.id) }}">` with the same four fields as the add-expense form, pre-populated from the fetched `expense` row:
  - **Amount** — `<input type="number" name="amount" step="0.01" min="0.01" required value="{{ form.amount }}">` — pre-filled with the existing amount.
  - **Category** — `<select name="category" required>` with the same seven fixed options; the current category is pre-selected.
  - **Date** — `<input type="date" name="date" required value="{{ form.date }}">` — pre-filled with the existing date.
  - **Description** — `<input type="text" name="description" maxlength="200" value="{{ form.description }}">` — pre-filled with the existing description.
  - A **Save Changes** submit button.
- Displays an inline `error` message if validation fails (re-renders form with error, preserving the in-progress values via a `form` dict).
- Includes a "Cancel" link back to `url_for('profile')`.

**Modify:** `templates/profile.html`
- In the transactions table/list, add an Edit link per row: `<a href="{{ url_for('edit_expense', id=tx.id) }}">Edit</a>`.

## Files to change
- `app.py` — replace the `edit_expense` stub with a full `GET`/`POST` handler:
  - `GET`: require login; call `get_expense_by_id(id, session["user_id"])`; abort(404) if `None`; render `edit_expense.html` with `expense`, `categories=VALID_CATEGORIES`, `form` pre-populated from expense, `error=None`.
  - `POST`: require login; call `get_expense_by_id(id, session["user_id"])`; abort(404) if `None`; validate amount, category, and date (same rules as add-expense); call `update_expense()` on success; redirect to `/profile`; re-render `edit_expense.html` with error on failure.
- `database/db.py` — add `get_expense_by_id()` and `update_expense()` helpers.
- `templates/profile.html` — add Edit link to each row in the transactions list.

## Files to create
- `templates/edit_expense.html` — the pre-filled edit form page.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`.
- Parameterised queries only — never f-strings or string concatenation in SQL.
- Both new DB helpers live in `database/db.py` — no SQL in the route function.
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- No inline `<style>` blocks in templates.
- Auth guard: if `session.get("user_id")` is falsy on either GET or POST, redirect to `url_for('login')`.
- Ownership guard: `get_expense_by_id` must include `AND user_id = ?` — a logged-in user must never be able to view or update another user's expense. Use `abort(404)` (not 403) when the row is missing or unowned.
- Amount validation: must be a positive number greater than 0; reject non-numeric or zero/negative values.
- Category validation: must be one of the `VALID_CATEGORIES` list defined in `app.py`.
- Date validation: must be a valid `YYYY-MM-DD` date string.
- Description is optional — store empty string as `""` if omitted, never `None`.
- After a successful update, redirect to `/profile` using `redirect(url_for('profile'))` — do not render the profile template directly.
- `update_expense()` helper signature: `update_expense(expense_id, user_id, amount, category, date, description)` where `amount` is a Python `float`.
- `get_expense_by_id()` helper signature: `get_expense_by_id(expense_id, user_id)` — returns a `sqlite3.Row` or `None`.

## Definition of done
- [ ] `GET /expenses/<id>/edit` returns 200 when logged in and the expense belongs to the logged-in user.
- [ ] The edit form is pre-filled with the existing amount, category, date, and description.
- [ ] `GET /expenses/<id>/edit` redirects to `/login` when the user is not logged in.
- [ ] `GET /expenses/<id>/edit` returns 404 when the expense id does not exist.
- [ ] `GET /expenses/<id>/edit` returns 404 when the expense belongs to a different user.
- [ ] Submitting the form with valid changes updates the row in the database and redirects to `/profile`.
- [ ] The updated values appear immediately in the transaction list on `/profile` after submission.
- [ ] Submitting with a missing or zero amount shows an inline error and re-renders the form — no DB update occurs.
- [ ] Submitting with a negative amount shows an inline error and re-renders the form.
- [ ] Submitting without selecting a category (or with an invalid category) shows an inline error.
- [ ] Submitting with a missing or invalid date shows an inline error.
- [ ] The profile page shows an Edit link next to each transaction that links to the correct `/expenses/<id>/edit` URL.
- [ ] No hex colour values appear in the new template — only CSS variables or class names.
