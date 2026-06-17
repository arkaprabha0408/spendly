# Spec: Add Expense

## Overview
Step 7 implements the add-expense form, letting logged-in users record a new spending entry. The placeholder `GET /expenses/add` route is upgraded to render a real form, and a `POST /expenses/add` handler is added to validate and persist the submission. A new `add_expense()` DB helper is introduced in `database/db.py` to keep SQL out of the route. On success the user is redirected to `/profile` so they immediately see their new entry in the transaction list and updated stats.

## Depends on
- Step 1: Database setup (`get_db()`, `expenses` table with `user_id`, `amount`, `category`, `date`, `description` columns)
- Step 2: Registration (users exist in DB)
- Step 3: Login / Logout (`session["user_id"]` is set on login, logout clears it)
- Step 4: Profile page (destination after successful add)
- Step 5: Backend routes for profile page (profile page displays live data after insert)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert the new expense, then redirect to `/profile` — logged-in only

## Database changes
No new tables or columns. The `expenses` table already has all required columns:

```
expenses(id, user_id, amount, category, date, description, created_at)
```

A new helper function `add_expense()` is added to `database/db.py` to insert a row.

## Templates
**Create:** `templates/add_expense.html`
- Extends `base.html`.
- Contains a single `<form method="POST" action="{{ url_for('add_expense') }}">` with these fields:
  - **Amount** — `<input type="number" name="amount" step="0.01" min="0.01" required>` — positive decimal, up to 2 decimal places.
  - **Category** — `<select name="category" required>` with these fixed options: Food, Transport, Bills, Health, Entertainment, Shopping, Other.
  - **Date** — `<input type="date" name="date" required>` — defaults to today's date (set via `value="{{ today }}"` passed from the route).
  - **Description** — `<input type="text" name="description" maxlength="200">` — optional, free text.
  - A **Save Expense** submit button.
- Displays an inline `error` flash if validation fails (re-renders form with error message, preserving previously entered values).
- Includes a "Cancel" link back to `url_for('profile')`.

**No modifications** to existing templates.

## Files to change
- `app.py` — replace the `add_expense` stub with a full `GET`/`POST` handler:
  - `GET`: require login; render `add_expense.html` with `today=date.today().isoformat()`.
  - `POST`: require login; read and validate form fields; call `add_expense()` DB helper; redirect to `/profile` on success, or re-render form with error on failure.

## Files to create
- `templates/add_expense.html` — the add-expense form page.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`.
- Parameterised queries only — never f-strings or string concatenation in SQL.
- The `add_expense()` helper lives in `database/db.py` — no SQL in the route function.
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- No inline `<style>` blocks in templates.
- Auth guard: if `session.get("user_id")` is falsy on either GET or POST, redirect to `url_for('login')` with `abort()` not called — a plain redirect is correct.
- Amount validation: must be a positive number greater than 0; reject non-numeric or zero/negative values with a user-facing error message.
- Category validation: must be one of the seven fixed options; reject unknown values.
- Date validation: must be a valid `YYYY-MM-DD` date string; reject malformed values.
- Description is optional — store empty string as `""` if omitted, never `None`.
- After a successful insert, redirect to `/profile` using `redirect(url_for('profile'))` — do not render the profile template directly.
- The `add_expense()` helper signature: `add_expense(user_id, amount, category, date, description)` where `amount` is a Python `float`.

## Definition of done
- [ ] `GET /expenses/add` returns 200 when logged in and renders a form with amount, category, date, and description fields.
- [ ] `GET /expenses/add` redirects to `/login` when the user is not logged in.
- [ ] Submitting the form with valid data inserts a row into the `expenses` table and redirects to `/profile`.
- [ ] The new expense appears immediately in the transaction list on `/profile` after submission.
- [ ] Summary stats on `/profile` (total spent, transaction count, top category) update to reflect the new expense.
- [ ] Submitting with a missing or zero amount shows an inline error and re-renders the form — no DB insert occurs.
- [ ] Submitting with a negative amount shows an inline error and re-renders the form.
- [ ] Submitting without selecting a category (or with an invalid category) shows an inline error.
- [ ] Submitting with a missing date shows an inline error.
- [ ] Submitting with an invalid date string shows an inline error.
- [ ] The date field defaults to today's date when the form first loads.
- [ ] The "Cancel" link on the form returns the user to `/profile` without inserting anything.
- [ ] No hex colour values appear in the new template — only CSS variables or class names.
- [ ] All amounts on `/profile` after adding an expense display the ₹ symbol.
