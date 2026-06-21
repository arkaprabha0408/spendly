import sqlite3
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, abort
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email, add_expense, get_expense_by_id, update_expense
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown

app = Flask(__name__)
app.secret_key = "dev-secret-change-in-production"


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def resolve_date_filter(preset, date_from, date_to):
    """Resolve URL params into (date_from, date_to, filter_label, active_preset)."""
    today = date.today()

    if preset == "7d":
        return (today - timedelta(days=6)).isoformat(), today.isoformat(), "Last 7 Days", "7d"
    if preset == "30d":
        return (today - timedelta(days=29)).isoformat(), today.isoformat(), "Last 30 Days", "30d"
    if preset == "month":
        return today.replace(day=1).isoformat(), today.isoformat(), "This Month", "month"
    if preset == "all":
        return None, None, "All Time", "all"

    if date_from and date_to:
        try:
            d_from = date.fromisoformat(date_from)
            d_to   = date.fromisoformat(date_to)
            if d_from > d_to:
                d_from, d_to = d_to, d_from
            label = (
                f"{d_from.strftime('%d %b %Y')} – {d_to.strftime('%d %b %Y')}"
            )
            return d_from.isoformat(), d_to.isoformat(), label, ""
        except ValueError:
            pass

    return None, None, "All Time", "all"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not name:
        return render_template("register.html", error="Full name is required.")
    if not email:
        return render_template("register.html", error="Email address is required.")
    if not password:
        return render_template("register.html", error="Password is required.")
    if len(password) < 6:
        return render_template("register.html", error="Password must be at least 6 characters.")
    if "@" not in email or "." not in email.split("@")[-1]:
        return render_template("register.html", error="Enter a valid email address (e.g. you@example.com).")

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        return render_template("register.html", error="An account with that email already exists.")

    return redirect(url_for("login", registered=1))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        success = "Account created! Please sign in." if request.args.get("registered") else None
        return render_template("login.html", success=success)

    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not email or not password:
        return render_template("login.html", error="Email and password are required.")

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"]   = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    preset    = request.args.get("preset", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to   = request.args.get("date_to",   "").strip()

    date_from, date_to, filter_label, active_preset = resolve_date_filter(
        preset, date_from, date_to
    )

    stats        = get_summary_stats(user_id, date_from=date_from, date_to=date_to)
    transactions = get_recent_transactions(user_id, date_from=date_from, date_to=date_to)
    categories   = get_category_breakdown(user_id, date_from=date_from, date_to=date_to)

    success = "Expense updated successfully!" if request.args.get("edited") else None

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        filter_label=filter_label,
        active_preset=active_preset,
        date_from=date_from or "",
        date_to=date_to or "",
        success=success,
    )


VALID_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


@app.route("/expenses/add", methods=["GET", "POST"], endpoint="add_expense")
def add_expense_view():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            today=date.today().isoformat(),
            categories=VALID_CATEGORIES,
            error=None,
            form={},
        )

    amount_raw  = request.form.get("amount", "").strip()
    category    = request.form.get("category", "").strip()
    date_raw    = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    form = {"amount": amount_raw, "category": category, "date": date_raw, "description": description}

    def rerender(error):
        return render_template(
            "add_expense.html",
            today=date.today().isoformat(),
            categories=VALID_CATEGORIES,
            error=error,
            form=form,
        )

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return rerender("Amount must be a number greater than zero.")

    if category not in VALID_CATEGORIES:
        return rerender("Please select a valid category.")

    try:
        datetime.strptime(date_raw, "%Y-%m-%d")
    except (ValueError, TypeError):
        return rerender("Date must be a valid date (YYYY-MM-DD).")

    add_expense(session["user_id"], amount, category, date_raw, description)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    if request.method == "GET":
        return render_template(
            "edit_expense.html",
            expense=expense,
            categories=VALID_CATEGORIES,
            form={
                "amount": expense["amount"],
                "category": expense["category"],
                "date": expense["date"],
                "description": expense["description"] or "",
            },
            error=None,
        )

    amount_raw  = request.form.get("amount", "").strip()
    category    = request.form.get("category", "").strip()
    date_raw    = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    form = {"amount": amount_raw, "category": category, "date": date_raw, "description": description}

    def rerender(error):
        return render_template(
            "edit_expense.html",
            expense=expense,
            categories=VALID_CATEGORIES,
            form=form,
            error=error,
        )

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return rerender("Amount must be a number greater than zero.")

    if category not in VALID_CATEGORIES:
        return rerender("Please select a valid category.")

    try:
        datetime.strptime(date_raw, "%Y-%m-%d")
    except (ValueError, TypeError):
        return rerender("Date must be a valid date (YYYY-MM-DD).")

    update_expense(id, session["user_id"], amount, category, date_raw, description)
    return redirect(url_for("profile", edited=1))


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


# ------------------------------------------------------------------ #
# Database initialisation                                             #
# ------------------------------------------------------------------ #

with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
