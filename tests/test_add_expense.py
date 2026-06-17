"""
Tests for Step 7: Add Expense

Coverage:
- Unit tests for add_expense() DB helper (insert, empty description, retrieval)
- Auth guard: GET and POST to /expenses/add redirect to /login when not logged in
- GET /expenses/add: 200, page contains expected landmarks and today's date
- POST happy path: valid submission redirects to /profile, row inserted correctly
- POST happy path: empty description stored as "" not NULL
- POST amount validation: 0, negative, non-numeric, missing → 200 + error
- POST category validation: invalid name, missing → 200 + error
- POST date validation: malformed string, missing → 200 + error
- POST value preservation: invalid submission re-populates category and date fields
- Template rendering: all seven valid categories appear on GET
"""

import pytest
import database.db as db_module
from database.db import init_db, seed_db, get_db, add_expense
from app import app as flask_app


# ---------------------------------------------------------------------------
# Fixtures — follow the same pattern as conftest.py and existing test files
# ---------------------------------------------------------------------------

@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Isolated SQLite DB in a temp directory, seeded with demo data."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    init_db()
    seed_db()
    return db_path


@pytest.fixture
def app(test_db):
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_user_id(test_db):
    """Returns the user_id of the seeded demo user (demo@spendly.com)."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
        ).fetchone()
        return row["id"]
    finally:
        conn.close()


@pytest.fixture
def auth_client(client, seed_user_id):
    """Test client already logged in as the demo user via session injection."""
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    return client


# ---------------------------------------------------------------------------
# 1. Unit tests — add_expense() DB helper
# ---------------------------------------------------------------------------

class TestAddExpenseHelper:

    def test_add_expense_inserts_row(self, test_db, seed_user_id):
        """A call to add_expense() must create exactly one row in expenses."""
        conn = get_db()
        try:
            before = conn.execute(
                "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
                (seed_user_id,),
            ).fetchone()["cnt"]
        finally:
            conn.close()

        add_expense(seed_user_id, 42.50, "Food", "2026-07-01", "test insert")

        conn = get_db()
        try:
            after = conn.execute(
                "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
                (seed_user_id,),
            ).fetchone()["cnt"]
        finally:
            conn.close()

        assert after == before + 1, (
            "add_expense() must insert exactly one new row into the expenses table"
        )

    def test_add_expense_correct_values(self, test_db, seed_user_id):
        """The inserted row must store all field values exactly as passed."""
        add_expense(seed_user_id, 99.99, "Health", "2026-07-10", "vitamins")

        conn = get_db()
        try:
            row = conn.execute(
                "SELECT * FROM expenses WHERE user_id = ? AND date = ?",
                (seed_user_id, "2026-07-10"),
            ).fetchone()
        finally:
            conn.close()

        assert row is not None, "Inserted row must be retrievable by user_id and date"
        assert row["user_id"] == seed_user_id, "user_id must match"
        assert row["amount"] == pytest.approx(99.99), "amount must match"
        assert row["category"] == "Health", "category must match"
        assert row["date"] == "2026-07-10", "date must match"
        assert row["description"] == "vitamins", "description must match"

    def test_add_expense_empty_description_stored_as_empty_string(
        self, test_db, seed_user_id
    ):
        """Passing description='' must store '' in the DB, not NULL."""
        add_expense(seed_user_id, 10.00, "Transport", "2026-07-15", "")

        conn = get_db()
        try:
            row = conn.execute(
                "SELECT description FROM expenses WHERE user_id = ? AND date = ?",
                (seed_user_id, "2026-07-15"),
            ).fetchone()
        finally:
            conn.close()

        assert row is not None, "Row must exist after add_expense() with empty description"
        assert row["description"] == "", (
            "Empty description must be stored as '' not NULL"
        )
        assert row["description"] is not None, (
            "description column must not be NULL when '' was supplied"
        )

    def test_add_expense_row_retrievable_with_all_correct_fields(
        self, test_db, seed_user_id
    ):
        """Full round-trip: insert then SELECT and verify every column."""
        add_expense(seed_user_id, 5.75, "Other", "2026-08-01", "coffee")

        conn = get_db()
        try:
            row = conn.execute(
                "SELECT user_id, amount, category, date, description"
                "  FROM expenses WHERE user_id = ? AND description = ?",
                (seed_user_id, "coffee"),
            ).fetchone()
        finally:
            conn.close()

        assert row["user_id"] == seed_user_id
        assert row["amount"] == pytest.approx(5.75)
        assert row["category"] == "Other"
        assert row["date"] == "2026-08-01"
        assert row["description"] == "coffee"


# ---------------------------------------------------------------------------
# 2. Auth guard — GET and POST while unauthenticated
# ---------------------------------------------------------------------------

class TestAddExpenseAuthGuard:

    def test_unauthenticated_get_redirects_to_login(self, client):
        response = client.get("/expenses/add")
        assert response.status_code == 302, (
            "Unauthenticated GET /expenses/add must return 302"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login"
        )

    def test_unauthenticated_post_redirects_to_login(self, client):
        response = client.post("/expenses/add", data={
            "amount": "25.00",
            "category": "Food",
            "date": "2026-07-01",
            "description": "lunch",
        })
        assert response.status_code == 302, (
            "Unauthenticated POST /expenses/add must return 302"
        )
        assert "/login" in response.headers["Location"], (
            "Unauthenticated POST must redirect to /login"
        )

    def test_unauthenticated_post_does_not_insert_row(self, client, test_db):
        """A rejected unauthenticated POST must not write anything to the DB."""
        conn = get_db()
        try:
            before = conn.execute("SELECT COUNT(*) AS cnt FROM expenses").fetchone()["cnt"]
        finally:
            conn.close()

        client.post("/expenses/add", data={
            "amount": "25.00",
            "category": "Food",
            "date": "2026-07-01",
            "description": "should not appear",
        })

        conn = get_db()
        try:
            after = conn.execute("SELECT COUNT(*) AS cnt FROM expenses").fetchone()["cnt"]
        finally:
            conn.close()

        assert after == before, (
            "Unauthenticated POST must not insert any row into the expenses table"
        )


# ---------------------------------------------------------------------------
# 3. GET /expenses/add — authenticated
# ---------------------------------------------------------------------------

class TestAddExpenseGet:

    def test_authenticated_get_returns_200(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert response.status_code == 200, (
            "Authenticated GET /expenses/add must return 200"
        )

    def test_get_page_contains_add_expense_heading(self, auth_client):
        response = auth_client.get("/expenses/add")
        body = response.data.decode("utf-8")
        assert "Add Expense" in body, (
            "Page must contain the 'Add Expense' heading"
        )

    def test_get_page_contains_save_expense_button(self, auth_client):
        response = auth_client.get("/expenses/add")
        body = response.data.decode("utf-8")
        assert "Save Expense" in body, (
            "Page must contain the 'Save Expense' submit button label"
        )

    def test_get_page_contains_todays_date(self, auth_client, app):
        """The form's date field must default to today's ISO date."""
        from datetime import date
        with app.app_context():
            today_iso = date.today().isoformat()

        response = auth_client.get("/expenses/add")
        body = response.data.decode("utf-8")
        assert today_iso in body, (
            f"Today's ISO date ({today_iso}) must appear in the page for the date field default"
        )

    def test_get_page_contains_all_valid_categories(self, auth_client):
        """All seven valid categories must appear as <option> elements."""
        expected_categories = [
            "Food", "Transport", "Bills", "Health",
            "Entertainment", "Shopping", "Other",
        ]
        response = auth_client.get("/expenses/add")
        body = response.data.decode("utf-8")
        for cat in expected_categories:
            assert cat in body, (
                f"Category '{cat}' must appear as an option in the category dropdown"
            )

    def test_get_page_has_amount_input(self, auth_client):
        response = auth_client.get("/expenses/add")
        body = response.data.decode("utf-8")
        assert 'name="amount"' in body, (
            "Page must contain an input with name='amount'"
        )

    def test_get_page_has_category_select(self, auth_client):
        response = auth_client.get("/expenses/add")
        body = response.data.decode("utf-8")
        assert 'name="category"' in body, (
            "Page must contain a select/input with name='category'"
        )

    def test_get_page_has_date_input(self, auth_client):
        response = auth_client.get("/expenses/add")
        body = response.data.decode("utf-8")
        assert 'name="date"' in body, (
            "Page must contain an input with name='date'"
        )

    def test_get_page_has_description_input(self, auth_client):
        response = auth_client.get("/expenses/add")
        body = response.data.decode("utf-8")
        assert 'name="description"' in body, (
            "Page must contain an input with name='description'"
        )

    def test_get_page_no_error_on_fresh_load(self, auth_client):
        """A fresh GET must not render any error message."""
        response = auth_client.get("/expenses/add")
        body = response.data.decode("utf-8")
        assert "auth-error" not in body, (
            "A fresh GET must not render an error block"
        )


# ---------------------------------------------------------------------------
# 4. POST /expenses/add — happy path
# ---------------------------------------------------------------------------

class TestAddExpensePostHappyPath:

    def test_valid_post_redirects_to_profile(self, auth_client):
        response = auth_client.post("/expenses/add", data={
            "amount": "35.00",
            "category": "Food",
            "date": "2026-07-01",
            "description": "dinner",
        })
        assert response.status_code == 302, (
            "Valid POST must return 302 redirect"
        )
        assert "/profile" in response.headers["Location"], (
            "Valid POST must redirect to /profile"
        )

    def test_valid_post_inserts_row_in_db(self, auth_client, seed_user_id, test_db):
        """After a valid POST the expense must be retrievable from the DB."""
        auth_client.post("/expenses/add", data={
            "amount": "55.50",
            "category": "Bills",
            "date": "2026-07-02",
            "description": "electricity",
        })

        conn = get_db()
        try:
            row = conn.execute(
                "SELECT * FROM expenses WHERE user_id = ? AND date = ? AND description = ?",
                (seed_user_id, "2026-07-02", "electricity"),
            ).fetchone()
        finally:
            conn.close()

        assert row is not None, "Expense row must exist in DB after a valid POST"
        assert row["amount"] == pytest.approx(55.50), "amount must be stored correctly"
        assert row["category"] == "Bills", "category must be stored correctly"

    def test_valid_post_stores_correct_user_id(self, auth_client, seed_user_id, test_db):
        """The inserted row must be associated with the logged-in user's id."""
        auth_client.post("/expenses/add", data={
            "amount": "12.00",
            "category": "Transport",
            "date": "2026-07-03",
            "description": "bus fare",
        })

        conn = get_db()
        try:
            row = conn.execute(
                "SELECT user_id FROM expenses WHERE date = ? AND description = ?",
                ("2026-07-03", "bus fare"),
            ).fetchone()
        finally:
            conn.close()

        assert row is not None, "Row must exist"
        assert row["user_id"] == seed_user_id, (
            "Inserted expense must be attributed to the logged-in user"
        )

    def test_valid_post_with_decimal_amount_stored_correctly(
        self, auth_client, seed_user_id, test_db
    ):
        """Decimal amounts must survive the float conversion and storage round-trip."""
        auth_client.post("/expenses/add", data={
            "amount": "19.99",
            "category": "Shopping",
            "date": "2026-07-04",
            "description": "book",
        })

        conn = get_db()
        try:
            row = conn.execute(
                "SELECT amount FROM expenses WHERE date = ? AND description = ?",
                ("2026-07-04", "book"),
            ).fetchone()
        finally:
            conn.close()

        assert row is not None
        assert row["amount"] == pytest.approx(19.99), (
            "Decimal amount 19.99 must be stored and retrieved accurately"
        )

    def test_valid_post_empty_description_redirects(self, auth_client):
        """An empty description is optional — the form must still succeed."""
        response = auth_client.post("/expenses/add", data={
            "amount": "8.00",
            "category": "Other",
            "date": "2026-07-05",
            "description": "",
        })
        assert response.status_code == 302, (
            "POST with empty description must still redirect (description is optional)"
        )
        assert "/profile" in response.headers["Location"]

    def test_valid_post_empty_description_stored_as_empty_string(
        self, auth_client, seed_user_id, test_db
    ):
        """Empty description submitted via the form must be stored as '' not NULL."""
        auth_client.post("/expenses/add", data={
            "amount": "8.00",
            "category": "Other",
            "date": "2026-07-05",
            "description": "",
        })

        conn = get_db()
        try:
            row = conn.execute(
                "SELECT description FROM expenses WHERE user_id = ? AND date = ?",
                (seed_user_id, "2026-07-05"),
            ).fetchone()
        finally:
            conn.close()

        assert row is not None, "Row must be present even with empty description"
        assert row["description"] == "", (
            "description must be stored as empty string, not NULL"
        )
        assert row["description"] is not None, (
            "description must not be NULL when an empty string was submitted"
        )

    def test_all_valid_categories_accepted(self, auth_client, seed_user_id, test_db):
        """Every category in VALID_CATEGORIES must be accepted by the route."""
        valid_categories = [
            "Food", "Transport", "Bills", "Health",
            "Entertainment", "Shopping", "Other",
        ]
        base_date = "2026-08-0{}"
        for i, cat in enumerate(valid_categories, start=1):
            response = auth_client.post("/expenses/add", data={
                "amount": "1.00",
                "category": cat,
                "date": base_date.format(i),
                "description": f"test {cat}",
            })
            assert response.status_code == 302, (
                f"Category '{cat}' must be accepted and redirect to /profile"
            )


# ---------------------------------------------------------------------------
# 5. POST /expenses/add — amount validation
# ---------------------------------------------------------------------------

class TestAddExpenseAmountValidation:

    @pytest.mark.parametrize("amount_value", ["0", "0.00", "-5", "-0.01"])
    def test_non_positive_amount_returns_200_with_error(
        self, auth_client, amount_value
    ):
        response = auth_client.post("/expenses/add", data={
            "amount": amount_value,
            "category": "Food",
            "date": "2026-07-10",
            "description": "test",
        })
        assert response.status_code == 200, (
            f"Amount '{amount_value}' must not redirect — must re-render the form"
        )
        body = response.data.decode("utf-8")
        assert "Amount must be a number greater than zero." in body, (
            f"Error message must appear for non-positive amount '{amount_value}'"
        )

    @pytest.mark.parametrize("amount_value", ["abc", "twelve", "1,000", "--5", "1e3x"])
    def test_non_numeric_amount_returns_200_with_error(
        self, auth_client, amount_value
    ):
        response = auth_client.post("/expenses/add", data={
            "amount": amount_value,
            "category": "Food",
            "date": "2026-07-10",
            "description": "test",
        })
        assert response.status_code == 200, (
            f"Non-numeric amount '{amount_value}' must not redirect"
        )
        body = response.data.decode("utf-8")
        assert "Amount must be a number greater than zero." in body, (
            f"Error message must appear for non-numeric amount '{amount_value}'"
        )

    def test_missing_amount_returns_200_with_error(self, auth_client):
        """Submitting the form without an amount field must trigger the error."""
        response = auth_client.post("/expenses/add", data={
            "category": "Food",
            "date": "2026-07-10",
            "description": "no amount",
        })
        assert response.status_code == 200, (
            "Missing amount must not redirect — must re-render the form"
        )
        body = response.data.decode("utf-8")
        assert "Amount must be a number greater than zero." in body, (
            "Error message must appear when amount field is absent"
        )

    def test_empty_amount_string_returns_200_with_error(self, auth_client):
        response = auth_client.post("/expenses/add", data={
            "amount": "",
            "category": "Food",
            "date": "2026-07-10",
            "description": "empty amount",
        })
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "Amount must be a number greater than zero." in body, (
            "Empty amount string must trigger the amount error"
        )

    def test_invalid_amount_does_not_insert_row(
        self, auth_client, test_db
    ):
        """A rejected amount must result in zero new rows being written."""
        conn = get_db()
        try:
            before = conn.execute("SELECT COUNT(*) AS cnt FROM expenses").fetchone()["cnt"]
        finally:
            conn.close()

        auth_client.post("/expenses/add", data={
            "amount": "abc",
            "category": "Food",
            "date": "2026-07-10",
            "description": "should not save",
        })

        conn = get_db()
        try:
            after = conn.execute("SELECT COUNT(*) AS cnt FROM expenses").fetchone()["cnt"]
        finally:
            conn.close()

        assert after == before, (
            "A POST with an invalid amount must not insert any row into the DB"
        )


# ---------------------------------------------------------------------------
# 6. POST /expenses/add — category validation
# ---------------------------------------------------------------------------

class TestAddExpenseCategoryValidation:

    @pytest.mark.parametrize("bad_category", [
        "Fuel", "Groceries", "Rent", "fuel", "food", "FOOD", "Unknown",
    ])
    def test_invalid_category_returns_200_with_error(
        self, auth_client, bad_category
    ):
        response = auth_client.post("/expenses/add", data={
            "amount": "20.00",
            "category": bad_category,
            "date": "2026-07-10",
            "description": "test",
        })
        assert response.status_code == 200, (
            f"Invalid category '{bad_category}' must not redirect"
        )
        body = response.data.decode("utf-8")
        assert "Please select a valid category." in body, (
            f"Error message must appear for invalid category '{bad_category}'"
        )

    def test_missing_category_returns_200_with_error(self, auth_client):
        """Submitting with no category field must trigger the category error."""
        response = auth_client.post("/expenses/add", data={
            "amount": "20.00",
            "date": "2026-07-10",
            "description": "no category",
        })
        assert response.status_code == 200, (
            "Missing category must not redirect"
        )
        body = response.data.decode("utf-8")
        assert "Please select a valid category." in body, (
            "Error message must appear when category field is absent"
        )

    def test_empty_category_string_returns_200_with_error(self, auth_client):
        response = auth_client.post("/expenses/add", data={
            "amount": "20.00",
            "category": "",
            "date": "2026-07-10",
            "description": "empty cat",
        })
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "Please select a valid category." in body, (
            "Empty category string must trigger the category error"
        )

    def test_invalid_category_does_not_insert_row(self, auth_client, test_db):
        conn = get_db()
        try:
            before = conn.execute("SELECT COUNT(*) AS cnt FROM expenses").fetchone()["cnt"]
        finally:
            conn.close()

        auth_client.post("/expenses/add", data={
            "amount": "20.00",
            "category": "Fuel",
            "date": "2026-07-10",
            "description": "invalid cat row",
        })

        conn = get_db()
        try:
            after = conn.execute("SELECT COUNT(*) AS cnt FROM expenses").fetchone()["cnt"]
        finally:
            conn.close()

        assert after == before, (
            "A POST with an invalid category must not insert any row into the DB"
        )


# ---------------------------------------------------------------------------
# 7. POST /expenses/add — date validation
# ---------------------------------------------------------------------------

class TestAddExpenseDateValidation:

    @pytest.mark.parametrize("bad_date", [
        "not-a-date",
        "2026-13-01",    # month 13 — invalid
        "2026-06-32",    # day 32 — invalid
        "01-07-2026",    # DD-MM-YYYY format — wrong format
        "2026/07/10",    # wrong separator
        "July 10 2026",  # human-readable — not YYYY-MM-DD
        "20260710",      # no separators
    ])
    def test_invalid_date_returns_200_with_error(self, auth_client, bad_date):
        response = auth_client.post("/expenses/add", data={
            "amount": "15.00",
            "category": "Health",
            "date": bad_date,
            "description": "test",
        })
        assert response.status_code == 200, (
            f"Invalid date '{bad_date}' must not redirect — must re-render the form"
        )
        body = response.data.decode("utf-8")
        assert "Date must be a valid date (YYYY-MM-DD)." in body, (
            f"Error message must appear for invalid date '{bad_date}'"
        )

    def test_missing_date_returns_200_with_error(self, auth_client):
        response = auth_client.post("/expenses/add", data={
            "amount": "15.00",
            "category": "Health",
            "description": "no date",
        })
        assert response.status_code == 200, (
            "Missing date must not redirect"
        )
        body = response.data.decode("utf-8")
        assert "Date must be a valid date (YYYY-MM-DD)." in body, (
            "Error message must appear when date field is absent"
        )

    def test_empty_date_string_returns_200_with_error(self, auth_client):
        response = auth_client.post("/expenses/add", data={
            "amount": "15.00",
            "category": "Health",
            "date": "",
            "description": "empty date",
        })
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "Date must be a valid date (YYYY-MM-DD)." in body, (
            "Empty date string must trigger the date error"
        )

    def test_invalid_date_does_not_insert_row(self, auth_client, test_db):
        conn = get_db()
        try:
            before = conn.execute("SELECT COUNT(*) AS cnt FROM expenses").fetchone()["cnt"]
        finally:
            conn.close()

        auth_client.post("/expenses/add", data={
            "amount": "15.00",
            "category": "Health",
            "date": "not-a-date",
            "description": "bad date row",
        })

        conn = get_db()
        try:
            after = conn.execute("SELECT COUNT(*) AS cnt FROM expenses").fetchone()["cnt"]
        finally:
            conn.close()

        assert after == before, (
            "A POST with an invalid date must not insert any row into the DB"
        )


# ---------------------------------------------------------------------------
# 8. Value preservation on validation failure
# ---------------------------------------------------------------------------

class TestAddExpenseValuePreservation:

    def test_submitted_category_repopulated_after_invalid_amount(
        self, auth_client
    ):
        """When amount is invalid the submitted category must re-appear in the
        re-rendered form so the user does not have to re-select it."""
        response = auth_client.post("/expenses/add", data={
            "amount": "abc",
            "category": "Entertainment",
            "date": "2026-07-15",
            "description": "cinema",
        })
        body = response.data.decode("utf-8")
        # The template marks the previously-selected option as selected;
        # at minimum the category value must appear in the HTML.
        assert "Entertainment" in body, (
            "Submitted category must be preserved in the re-rendered form after an amount error"
        )

    def test_submitted_date_repopulated_after_invalid_amount(
        self, auth_client
    ):
        """When amount is invalid the submitted date must re-appear in the
        re-rendered form's date input value."""
        response = auth_client.post("/expenses/add", data={
            "amount": "-10",
            "category": "Shopping",
            "date": "2026-07-20",
            "description": "shoes",
        })
        body = response.data.decode("utf-8")
        assert "2026-07-20" in body, (
            "Submitted date must be preserved in the re-rendered form after an amount error"
        )

    def test_submitted_description_repopulated_after_invalid_category(
        self, auth_client
    ):
        """When category is invalid the description text must be preserved."""
        response = auth_client.post("/expenses/add", data={
            "amount": "25.00",
            "category": "Fuel",
            "date": "2026-07-21",
            "description": "petrol",
        })
        body = response.data.decode("utf-8")
        assert "petrol" in body, (
            "Submitted description must be preserved in the re-rendered form after a category error"
        )

    def test_submitted_amount_repopulated_after_invalid_date(
        self, auth_client
    ):
        """When date is invalid the submitted amount must be preserved."""
        response = auth_client.post("/expenses/add", data={
            "amount": "33.33",
            "category": "Food",
            "date": "bad-date",
            "description": "lunch",
        })
        body = response.data.decode("utf-8")
        assert "33.33" in body, (
            "Submitted amount must be preserved in the re-rendered form after a date error"
        )

    def test_error_block_rendered_on_validation_failure(self, auth_client):
        """When any validation fails the auth-error block must be present."""
        response = auth_client.post("/expenses/add", data={
            "amount": "0",
            "category": "Food",
            "date": "2026-07-10",
            "description": "zero",
        })
        body = response.data.decode("utf-8")
        assert "auth-error" in body, (
            "The auth-error block must be rendered when a validation error occurs"
        )

    def test_all_valid_categories_still_present_after_error(self, auth_client):
        """Even on a re-render after an error, the full category list must be
        present in the dropdown."""
        expected_categories = [
            "Food", "Transport", "Bills", "Health",
            "Entertainment", "Shopping", "Other",
        ]
        response = auth_client.post("/expenses/add", data={
            "amount": "abc",
            "category": "Food",
            "date": "2026-07-10",
            "description": "bad amount",
        })
        body = response.data.decode("utf-8")
        for cat in expected_categories:
            assert cat in body, (
                f"Category '{cat}' must still appear in the dropdown after a validation error"
            )
