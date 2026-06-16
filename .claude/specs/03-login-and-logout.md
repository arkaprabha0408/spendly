# Spec: Login and Logout

## Overview

This step wires up the authentication flow so registered users can sign in and out of Spendly. The `GET /login` route and `login.html` template already exist as UI-only stubs; this step adds the `POST /login` handler that validates credentials against the database, writes the authenticated user's `id` and `name` into the Flask session, and redirects to the landing page. It also implements `GET /logout`, which clears the session and redirects to `/`. Together these two routes complete the auth lifecycle started in Step 2 and gate every protected route that follows.

---

## Depends on

- **Step 1 — Database setup**: `get_db()` and the `users` table must exist.
- **Step 2 — Registration**: `create_user()` and the hashed-password column must exist; at least one user (the seeded demo account) must be in the database.

---

## Routes

| Method | Path      | Description                                                             | Access                              |
| ------ | --------- | ----------------------------------------------------------------------- | ----------------------------------- |
| `GET`  | `/login`  | Render the login form (already exists — extend to accept `error` kwarg) | Public                              |
| `POST` | `/login`  | Validate email + password, set session, redirect to `/`                 | Public                              |
| `GET`  | `/logout` | Clear session, redirect to `/`                                          | Logged-in (no hard enforcement yet) |

---

## Database changes

No database changes. The existing `users` table already has all required fields:

- `id` (INTEGER PRIMARY KEY)
- `email` (TEXT UNIQUE NOT NULL)
- `password_hash` (TEXT NOT NULL)
- `name` (TEXT NOT NULL)

---

## Templates

**Modify:**

- `templates/login.html` — change `action="/login"` to `action="{{ url_for('login') }}"` so it posts correctly; the template already renders `{{ error }}` so no further changes are needed for error display.
- `templates/base.html` — update the navbar "Sign in" / "Log out" links to be conditional: show "Log out" (linking to `url_for('logout')`) when `session.user_id` is set, otherwise show "Sign in" (linking to `url_for('login')`).

**Create:** None.

---

## Files to change

- `app.py` — add `POST /login` handler; implement `GET /logout`; add `session` to the Flask import; add `get_user_by_email` call (or inline query via `get_db()`).
- `database/db.py` — add `get_user_by_email(email)` helper that returns the matching `users` row or `None`.
- `templates/login.html` — fix `action` attribute to use `url_for('login')`.
- `templates/base.html` — make navbar auth link conditional on `session`.

---

## Files to create

None.

---

## New dependencies

No new pip packages. Uses:

- `werkzeug.security.check_password_hash` (already installed with Flask)
- `flask.session` (already installed with Flask; `app.secret_key` already set in `app.py`)

---

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`.
- Parameterised queries only — never use f-strings or `%` formatting in SQL.
- Verify passwords with `werkzeug.security.check_password_hash` — never compare plaintext.
- Use CSS variables — never hardcode hex colour values in templates or CSS.
- All templates extend `base.html`.
- Use `url_for()` for every internal link and form `action` — never hardcode paths.
- On invalid credentials (wrong email or wrong password), re-render `login.html` with a **single** generic error message: "Invalid email or password." — do not reveal which field was wrong.
- On successful login, store `session["user_id"]` (integer) and `session["user_name"]` (string) then `redirect(url_for("landing"))`.
- `GET /logout` must call `session.clear()` before redirecting — do not pop individual keys.
- Validate server-side: email and password must both be non-empty before hitting the database.
- Use `abort()` for unexpected HTTP errors, not bare string returns.

---

## Definition of done

- [ ] Submitting the login form with the seeded demo credentials (`demo@spendly.com` / `demo123`) sets `session["user_id"]` and `session["user_name"]` and redirects to `/`.
- [ ] Submitting with a correct email but wrong password re-renders the form with "Invalid email or password." and does not set a session.
- [ ] Submitting with an email that does not exist re-renders the form with "Invalid email or password." and does not set a session.
- [ ] Submitting with either field empty re-renders the form with a validation error and does not query the database.
- [ ] Visiting `/logout` clears the session and redirects to `/`.
- [ ] After logout, `session["user_id"]` is no longer present.
- [ ] The navbar shows "Log out" when the user is logged in and "Sign in" when they are not.
- [ ] All form actions and internal links use `url_for()` — no hardcoded URLs in templates.
- [ ] The app starts without errors and the existing `/register` flow still works.
- [ ] When a user is logged in, he shouldn't be able to visit /login and /register routes.He should be redirected back.
