import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, abort
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "dev-secret-change-in-production"


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

    user = {
        "name": "Arka Biswas",
        "email": "arka@example.com",
        "member_since": "January 2025",
        "initials": "AB",
    }

    stats = {
        "total_spent": "₹24,850",
        "transaction_count": 18,
        "top_category": "Food",
    }

    transactions = [
        {"date": "12 Jun 2025", "description": "Swiggy Order",      "category": "Food",     "amount": "₹430"},
        {"date": "10 Jun 2025", "description": "Uber Cab",           "category": "Travel",   "amount": "₹280"},
        {"date": "08 Jun 2025", "description": "Electricity Bill",   "category": "Bills",    "amount": "₹1,200"},
        {"date": "06 Jun 2025", "description": "Apollo Pharmacy",    "category": "Health",   "amount": "₹650"},
        {"date": "04 Jun 2025", "description": "Amazon Purchase",    "category": "Shopping", "amount": "₹2,100"},
    ]

    categories = [
        {"name": "Food",     "total": "₹8,400", "percent": 34},
        {"name": "Bills",    "total": "₹6,200", "percent": 25},
        {"name": "Shopping", "total": "₹5,100", "percent": 21},
        {"name": "Travel",   "total": "₹3,200", "percent": 13},
        {"name": "Health",   "total": "₹1,950", "percent": 8},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


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
