# Spec: Registration

## Overview

This step wires up the user registration flow so new visitors can create a Spendly account. The `GET /register` route and `register.html` template already exist as UI-only stubs; this step adds the `POST /register` handler that validates submitted data, hashes the password, inserts a new row into the `users` table.On success, and a success message is shown and redirects the user to the login page . It also introduces Flask sessions so the app can track who is logged in — a prerequisite for every authenticated route that follows.

---

## Depends on

- **Step 1 — Database setup**: `get_db()`, `init_db()`, `seed_db()`, and both tables must exist.

---

## Routes

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET`  | `/register` | Render the registration form (already exists — no change needed) | Public |
| `POST` | `/register` | Validate form data, insert user, redirect to `/login` | Public |

---

## Database changes

No new tables or columns. The existing `users` table already has all required fields:
- `name` (TEXT NOT NULL)
- `email` (TEXT UNIQUE NOT NULL)
- `password_hash` (TEXT NOT NULL)
- `created_at` (TEXT DEFAULT datetime('now'))

---

## Templates

**Modify:**
- `templates/register.html` — ensure the `<form>` has `method="POST"` and `action="{{ url_for('register_post') }}"` (or the route function name chosen). Add a visible flash message block to display validation errors and success notices.

**No new templates.**

---

## Files to change

- `app.py` — add `POST /register` route; import `request`, `redirect`, `url_for`, `flash`, `session` from Flask; set `app.secret_key`.
- `database/db.py` — add `create_user(name, email, password)` helper that inserts into `users` and returns the new `id`.
- `templates/register.html` — add flash message display block and ensure form posts correctly.

## Files to create

None.

---

## New dependencies

No new pip packages. Uses:
- `werkzeug.security.generate_password_hash` (already installed)
- `flask.session`, `flask.flash`, `flask.request`, `flask.redirect` (already installed with Flask)

---

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`.
- Parameterised queries only — never use f-strings or `%` formatting in SQL.
- Hash passwords with `werkzeug.security.generate_password_hash` — never store plaintext.
- `app.secret_key` must be set before any session or flash usage; use a hard-coded dev string for now (e.g. `"spendly-dev-secret"`).
- All templates extend `base.html`.
- Use CSS variables — never hardcode hex colour values in templates or new CSS.
- Use `url_for()` for every internal link and form `action` — never hardcode paths.
- On duplicate email, catch the `sqlite3.IntegrityError` and re-render the form with a user-friendly flash message — do not let the exception bubble to a 500.
- On success, redirect to `GET /login` with a flash success message.
- Validate server-side: name and email and password must all be non-empty; password must be at least 6 characters.
- Use `abort()` for unexpected HTTP errors, not bare string returns.

---

## Definition of done

- [ ] Submitting the registration form with valid data creates a new row in `users` with a hashed password.
- [ ] After successful registration, the user is redirected to `/login` and sees a success flash message.
- [ ] Submitting with an already-registered email re-renders the form with an error flash message and does not insert a duplicate row.
- [ ] Submitting with any empty field re-renders the form with a validation error message.
- [ ] Submitting with a password shorter than 6 characters re-renders the form with an error message.
- [ ] The `password_hash` column in the DB never contains a plaintext password.
- [ ] The app starts without errors after `app.secret_key` is set.
- [ ] All form actions and links use `url_for()` — no hardcoded URLs in the template.
