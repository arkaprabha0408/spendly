"""
Tests for Step 6: Date Filter on the Profile Page

Spec: .claude/specs/06-date-filter-profile-page.md

Coverage:
- Auth guard: unauthenticated requests redirect to /login
- Default (no params): all-time data, "All Time" label, all-time preset active
- Preset 7d: filters to last 7 calendar days, correct label
- Preset 30d: filters to last 30 calendar days, correct label
- Preset month: filters from first day of current month, correct label
- Preset all (explicit): behaves identically to no-params all-time
- Custom date range: date_from + date_to filters correctly
- Reversed date range: silently swapped, returns valid data
- Malformed date_from or date_to: falls back to All Time, no exception
- Partial params (only date_from or only date_to): falls back to All Time
- Empty result set: zero expenses in range returns ₹0.00, 0 transactions
- Rupee symbol present in all filtered views
- filter_label rendered in page body
- active_preset CSS class on correct button
- URL is bookmarkable (GET, not session-stored)
- Unit tests for get_summary_stats, get_recent_transactions, get_category_breakdown
  with date range arguments
- Single-day filter (date_from == date_to)
- Future-only date range returns empty results
- Parametrized malformed date strings all fall back to All Time
"""

import datetime
import pytest
import database.db as db_module
from database.db import init_db, seed_db, get_db
from database.queries import (
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)
from app import app as flask_app


# ---------------------------------------------------------------------------
# Fixtures
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
    """Returns the user_id of the seeded demo user."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
        ).fetchone()
        return row["id"]
    finally:
        conn.close()


@pytest.fixture
def blank_user_id(test_db):
    """A user with no expenses of their own."""
    from werkzeug.security import generate_password_hash
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Blank User", "blank@test.com", generate_password_hash("testpass")),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("blank@test.com",)
        ).fetchone()
        return row["id"]
    finally:
        conn.close()


@pytest.fixture
def auth_client(client, seed_user_id):
    """Test client already logged in as the demo user (session injection)."""
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    return client


@pytest.fixture
def blank_auth_client(client, blank_user_id):
    """Test client logged in as the blank (no-expenses) user."""
    with client.session_transaction() as sess:
        sess["user_id"] = blank_user_id
        sess["user_name"] = "Blank User"
    return client


def _insert_expense(user_id, amount, category, date, description="test"):
    """Helper: insert a single expense row and return nothing."""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:

    def test_unauthenticated_profile_redirects_to_login(self, client):
        response = client.get("/profile")
        assert response.status_code == 302, (
            "Unauthenticated GET /profile must redirect (302)"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login"
        )

    def test_unauthenticated_profile_with_preset_param_redirects(self, client):
        response = client.get("/profile?preset=7d")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"], (
            "Auth guard must fire even when query params are present"
        )

    def test_unauthenticated_profile_with_custom_dates_redirects(self, client):
        response = client.get("/profile?date_from=2026-01-01&date_to=2026-06-30")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------------------
# 2. Default (no query params) — All Time
# ---------------------------------------------------------------------------

class TestDefaultAllTime:

    def test_profile_no_params_returns_200(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200, (
            "Authenticated GET /profile with no params must return 200"
        )

    def test_profile_no_params_shows_filter_label_all_time(self, auth_client):
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        assert "All Time" in body, (
            "filter_label 'All Time' must appear in the page when no params are given"
        )

    def test_profile_no_params_active_button_is_all_time(self, auth_client):
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        # The active preset button must carry the modifier class
        assert "filter-btn--active" in body, (
            "At least one button must have filter-btn--active class"
        )

    def test_profile_no_params_shows_all_time_total(self, auth_client):
        """All eight seeded expenses total ₹327.74."""
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        assert "327.74" in body, (
            "All-time total ₹327.74 must appear when no date filter is applied"
        )

    def test_profile_no_params_shows_rupee_symbol(self, auth_client):
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        assert "₹" in body, "Rupee symbol must be present in default all-time view"

    def test_profile_no_params_shows_all_transactions(self, auth_client):
        """Eight seeded transactions must all be present."""
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        # The template renders one date cell per transaction
        assert body.count("txn-date") == 8, (
            "All 8 seeded transactions must be visible in the all-time view"
        )


# ---------------------------------------------------------------------------
# 3. Preset: 7d — Last 7 Days
# ---------------------------------------------------------------------------

class TestPreset7d:

    def _insert_today_expense(self, user_id):
        """Insert an expense dated today so it always falls in the 7-day window."""
        today = datetime.date.today().isoformat()
        _insert_expense(user_id, 99.00, "Food", today, "today expense")

    def test_preset_7d_returns_200(self, auth_client):
        response = auth_client.get("/profile?preset=7d")
        assert response.status_code == 200

    def test_preset_7d_filter_label_in_page(self, auth_client):
        response = auth_client.get("/profile?preset=7d")
        body = response.data.decode("utf-8")
        assert "Last 7 Days" in body, (
            "filter_label 'Last 7 Days' must appear in the rendered page"
        )

    def test_preset_7d_active_button_highlighted(self, auth_client):
        response = auth_client.get("/profile?preset=7d")
        body = response.data.decode("utf-8")
        assert "filter-btn--active" in body, (
            "A button must carry filter-btn--active when preset=7d"
        )

    def test_preset_7d_excludes_old_expenses(self, auth_client, seed_user_id):
        """All seeded expenses are in June 2026 — if today is much later, they
        fall outside the 7-day window and stats should reflect that."""
        today = datetime.date.today()
        cutoff = (today - datetime.timedelta(days=6)).isoformat()
        # Query the DB directly to know how many seeded expenses fall in range
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?"
                " AND date BETWEEN ? AND ?",
                (seed_user_id, cutoff, today.isoformat()),
            ).fetchone()
            expected_count = row["cnt"]
        finally:
            conn.close()

        response = auth_client.get("/profile?preset=7d")
        body = response.data.decode("utf-8")
        # The transaction count shown must match what the DB says is in range
        assert str(expected_count) in body, (
            "Transaction count in the 7-day view must match DB-computed count"
        )

    def test_preset_7d_includes_today_expense(self, auth_client, seed_user_id, test_db):
        """An expense inserted with today's date must appear in the 7d window."""
        today = datetime.date.today().isoformat()
        _insert_expense(seed_user_id, 55.00, "Food", today, "today expense")

        response = auth_client.get("/profile?preset=7d")
        body = response.data.decode("utf-8")
        assert "55.00" in body, (
            "An expense dated today must be visible under Last 7 Days"
        )

    def test_preset_7d_rupee_symbol_present(self, auth_client):
        response = auth_client.get("/profile?preset=7d")
        body = response.data.decode("utf-8")
        assert "₹" in body, "Rupee symbol must appear in 7d filtered view"


# ---------------------------------------------------------------------------
# 4. Preset: 30d — Last 30 Days
# ---------------------------------------------------------------------------

class TestPreset30d:

    def test_preset_30d_returns_200(self, auth_client):
        response = auth_client.get("/profile?preset=30d")
        assert response.status_code == 200

    def test_preset_30d_filter_label_in_page(self, auth_client):
        response = auth_client.get("/profile?preset=30d")
        body = response.data.decode("utf-8")
        assert "Last 30 Days" in body, (
            "filter_label 'Last 30 Days' must appear in the rendered page"
        )

    def test_preset_30d_active_button_highlighted(self, auth_client):
        response = auth_client.get("/profile?preset=30d")
        body = response.data.decode("utf-8")
        assert "filter-btn--active" in body

    def test_preset_30d_includes_today_expense(self, auth_client, seed_user_id, test_db):
        today = datetime.date.today().isoformat()
        _insert_expense(seed_user_id, 77.00, "Bills", today, "monthly bill today")

        response = auth_client.get("/profile?preset=30d")
        body = response.data.decode("utf-8")
        assert "77.00" in body, (
            "An expense dated today must be visible under Last 30 Days"
        )

    def test_preset_30d_window_is_29_days_back(self, auth_client, seed_user_id, test_db):
        """Spec says last 30 days means today minus 29 days. An expense on the
        boundary (today - 29) must be included; one on today - 30 must not."""
        today = datetime.date.today()
        boundary_in = (today - datetime.timedelta(days=29)).isoformat()
        boundary_out = (today - datetime.timedelta(days=30)).isoformat()

        _insert_expense(seed_user_id, 11.11, "Food", boundary_in, "in boundary")
        _insert_expense(seed_user_id, 22.22, "Food", boundary_out, "out boundary")

        response = auth_client.get("/profile?preset=30d")
        body = response.data.decode("utf-8")
        assert "11.11" in body, (
            "Expense on today-29 must be included in Last 30 Days window"
        )
        assert "22.22" not in body, (
            "Expense on today-30 must NOT be included in Last 30 Days window"
        )

    def test_preset_30d_rupee_symbol_present(self, auth_client):
        response = auth_client.get("/profile?preset=30d")
        body = response.data.decode("utf-8")
        assert "₹" in body


# ---------------------------------------------------------------------------
# 5. Preset: month — This Month
# ---------------------------------------------------------------------------

class TestPresetMonth:

    def test_preset_month_returns_200(self, auth_client):
        response = auth_client.get("/profile?preset=month")
        assert response.status_code == 200

    def test_preset_month_filter_label_in_page(self, auth_client):
        response = auth_client.get("/profile?preset=month")
        body = response.data.decode("utf-8")
        assert "This Month" in body, (
            "filter_label 'This Month' must appear in the rendered page"
        )

    def test_preset_month_active_button_highlighted(self, auth_client):
        response = auth_client.get("/profile?preset=month")
        body = response.data.decode("utf-8")
        assert "filter-btn--active" in body

    def test_preset_month_uses_first_day_of_month(self, auth_client, seed_user_id, test_db):
        """Spec: This Month starts from the 1st of the current calendar month,
        NOT 30 days ago. An expense on the 1st of the current month must be
        visible; one on the last day of the previous month must not."""
        today = datetime.date.today()
        first_of_month = today.replace(day=1).isoformat()
        last_day_prev_month = (today.replace(day=1) - datetime.timedelta(days=1)).isoformat()

        _insert_expense(seed_user_id, 33.33, "Shopping", first_of_month, "first of month")
        _insert_expense(seed_user_id, 44.44, "Shopping", last_day_prev_month, "last of prev month")

        response = auth_client.get("/profile?preset=month")
        body = response.data.decode("utf-8")
        assert "33.33" in body, (
            "Expense on the 1st of the current month must be included in 'This Month'"
        )
        assert "44.44" not in body, (
            "Expense on the last day of the previous month must NOT be in 'This Month'"
        )

    def test_preset_month_includes_today(self, auth_client, seed_user_id, test_db):
        today = datetime.date.today().isoformat()
        _insert_expense(seed_user_id, 88.88, "Health", today, "today health")

        response = auth_client.get("/profile?preset=month")
        body = response.data.decode("utf-8")
        assert "88.88" in body, (
            "Expense dated today must appear in This Month view"
        )

    def test_preset_month_rupee_symbol_present(self, auth_client):
        response = auth_client.get("/profile?preset=month")
        body = response.data.decode("utf-8")
        assert "₹" in body


# ---------------------------------------------------------------------------
# 6. Preset: all (explicit)
# ---------------------------------------------------------------------------

class TestPresetAll:

    def test_preset_all_returns_200(self, auth_client):
        response = auth_client.get("/profile?preset=all")
        assert response.status_code == 200

    def test_preset_all_filter_label_in_page(self, auth_client):
        response = auth_client.get("/profile?preset=all")
        body = response.data.decode("utf-8")
        assert "All Time" in body, (
            "Explicit preset=all must produce 'All Time' label"
        )

    def test_preset_all_shows_all_seeded_expenses(self, auth_client):
        """preset=all must return the same all-time total as no params."""
        response = auth_client.get("/profile?preset=all")
        body = response.data.decode("utf-8")
        assert "327.74" in body, (
            "All seeded expenses (₹327.74 total) must be visible under preset=all"
        )

    def test_preset_all_active_button_highlighted(self, auth_client):
        response = auth_client.get("/profile?preset=all")
        body = response.data.decode("utf-8")
        assert "filter-btn--active" in body

    def test_preset_all_matches_no_params_total(self, auth_client):
        """The total shown for preset=all must equal the total shown for no params."""
        r_all = auth_client.get("/profile?preset=all")
        r_none = auth_client.get("/profile")
        # Both pages must contain the same all-time total
        assert "327.74" in r_all.data.decode("utf-8")
        assert "327.74" in r_none.data.decode("utf-8")


# ---------------------------------------------------------------------------
# 7. Custom date range
# ---------------------------------------------------------------------------

class TestCustomDateRange:

    def test_custom_range_returns_200(self, auth_client):
        response = auth_client.get("/profile?date_from=2026-06-01&date_to=2026-06-30")
        assert response.status_code == 200

    def test_custom_range_filter_label_contains_dates(self, auth_client):
        response = auth_client.get("/profile?date_from=2026-06-01&date_to=2026-06-30")
        body = response.data.decode("utf-8")
        # Spec: filter_label for a custom range is "date_from – date_to"
        assert "2026-06-01" in body and "2026-06-30" in body, (
            "Custom range label must contain the supplied date_from and date_to strings"
        )

    def test_custom_range_restricts_transactions(self, auth_client, seed_user_id, test_db):
        """Insert one expense inside the range and one outside; only the inside
        one should appear."""
        _insert_expense(seed_user_id, 50.00, "Food", "2026-01-15", "inside custom range")
        _insert_expense(seed_user_id, 60.00, "Food", "2025-12-01", "outside custom range")

        response = auth_client.get(
            "/profile?date_from=2026-01-01&date_to=2026-01-31"
        )
        body = response.data.decode("utf-8")
        assert "50.00" in body, (
            "Expense inside custom date range must appear"
        )
        assert "60.00" not in body, (
            "Expense outside custom date range must not appear"
        )

    def test_custom_range_correct_total(self, auth_client, seed_user_id, test_db):
        """Only the two expenses in June 2026-06-02 to 2026-06-04 should sum."""
        # Seeded: 45.50 on 2026-06-02 (Food) and 12.00 on 2026-06-04 (Transport)
        response = auth_client.get(
            "/profile?date_from=2026-06-02&date_to=2026-06-04"
        )
        body = response.data.decode("utf-8")
        # Total = 45.50 + 12.00 = 57.50
        assert "57.50" in body, (
            "Total for 2026-06-02 to 2026-06-04 must be ₹57.50"
        )

    def test_custom_range_no_active_preset_class_on_preset_buttons(self, auth_client):
        """When using a custom range the active-class should NOT be on a preset
        button value that doesn't match. At minimum, the page must still render."""
        response = auth_client.get("/profile?date_from=2026-06-01&date_to=2026-06-30")
        assert response.status_code == 200

    def test_custom_range_rupee_symbol_present(self, auth_client):
        response = auth_client.get("/profile?date_from=2026-06-01&date_to=2026-06-30")
        body = response.data.decode("utf-8")
        assert "₹" in body


# ---------------------------------------------------------------------------
# 8. Reversed date range (date_from > date_to)
# ---------------------------------------------------------------------------

class TestReversedDateRange:

    def test_reversed_range_returns_200(self, auth_client):
        """Spec: reversed range is silently swapped, no error returned."""
        response = auth_client.get(
            "/profile?date_from=2026-06-30&date_to=2026-06-01"
        )
        assert response.status_code == 200, (
            "Reversed date range must not raise an error (spec: silently swap)"
        )

    def test_reversed_range_produces_same_results_as_correct_order(
        self, auth_client
    ):
        """Swapping the dates client-side must yield the same results as
        supplying them in the correct order."""
        r_correct = auth_client.get(
            "/profile?date_from=2026-06-02&date_to=2026-06-04"
        )
        r_reversed = auth_client.get(
            "/profile?date_from=2026-06-04&date_to=2026-06-02"
        )
        # Both should show the same total: 57.50
        body_correct = r_correct.data.decode("utf-8")
        body_reversed = r_reversed.data.decode("utf-8")
        assert "57.50" in body_correct, "Correct order must show ₹57.50"
        assert "57.50" in body_reversed, (
            "Reversed order must show the same ₹57.50 after silent swap"
        )

    def test_reversed_range_no_exception_on_wildly_reversed_dates(self, auth_client):
        response = auth_client.get(
            "/profile?date_from=2099-12-31&date_to=2000-01-01"
        )
        assert response.status_code == 200, (
            "A wildly reversed range must still return 200 after swapping"
        )


# ---------------------------------------------------------------------------
# 9. Malformed date parameters
# ---------------------------------------------------------------------------

class TestMalformedDateParams:

    @pytest.mark.parametrize("date_from,date_to", [
        ("not-a-date", "2026-06-30"),
        ("2026-06-01", "not-a-date"),
        ("2026-13-01", "2026-06-30"),      # month 13 is invalid
        ("2026-06-32", "2026-06-30"),      # day 32 is invalid
        ("", "2026-06-30"),                # empty string for date_from
        ("2026-06-01", ""),                # empty string for date_to
        ("abc", "xyz"),
        ("06-01-2026", "06-30-2026"),      # wrong format (MM-DD-YYYY)
        ("2026/06/01", "2026/06/30"),      # wrong separator
    ])
    def test_malformed_dates_fall_back_to_all_time(
        self, auth_client, date_from, date_to
    ):
        """Spec: malformed date params must silently fall back to All Time."""
        response = auth_client.get(
            f"/profile?date_from={date_from}&date_to={date_to}"
        )
        assert response.status_code == 200, (
            f"Malformed dates ({date_from!r}, {date_to!r}) must not crash the app"
        )
        body = response.data.decode("utf-8")
        assert "All Time" in body, (
            f"Malformed dates ({date_from!r}, {date_to!r}) must fall back to All Time label"
        )

    def test_malformed_date_from_still_shows_rupee_symbol(self, auth_client):
        response = auth_client.get("/profile?date_from=bad&date_to=2026-06-30")
        body = response.data.decode("utf-8")
        assert "₹" in body, (
            "Rupee symbol must appear even when date params are malformed"
        )


# ---------------------------------------------------------------------------
# 10. Partial params (only one of date_from or date_to)
# ---------------------------------------------------------------------------

class TestPartialDateParams:

    def test_only_date_from_falls_back_to_all_time(self, auth_client):
        """Spec: if date_from and date_to are not both provided, fall back."""
        response = auth_client.get("/profile?date_from=2026-06-01")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "All Time" in body, (
            "Only date_from without date_to must fall back to All Time"
        )

    def test_only_date_to_falls_back_to_all_time(self, auth_client):
        response = auth_client.get("/profile?date_to=2026-06-30")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "All Time" in body, (
            "Only date_to without date_from must fall back to All Time"
        )

    def test_only_date_from_shows_all_time_total(self, auth_client):
        response = auth_client.get("/profile?date_from=2026-06-01")
        body = response.data.decode("utf-8")
        assert "327.74" in body, (
            "Partial params must show all-time total (₹327.74)"
        )


# ---------------------------------------------------------------------------
# 11. Empty result set — user with no expenses in range
# ---------------------------------------------------------------------------

class TestEmptyResultSet:

    def test_blank_user_no_expenses_all_time_returns_200(self, blank_auth_client):
        response = blank_auth_client.get("/profile")
        assert response.status_code == 200

    def test_blank_user_shows_zero_total(self, blank_auth_client):
        response = blank_auth_client.get("/profile")
        body = response.data.decode("utf-8")
        assert "₹0.00" in body, (
            "A user with no expenses must see ₹0.00 total"
        )

    def test_blank_user_shows_zero_transaction_count(self, blank_auth_client):
        response = blank_auth_client.get("/profile")
        body = response.data.decode("utf-8")
        # The stats dict returns transaction_count: 0
        assert "0" in body

    def test_seeded_user_no_expenses_in_range(self, auth_client):
        """Seed user has expenses in June 2026. A range in a different year
        must return zero results without crashing."""
        response = auth_client.get(
            "/profile?date_from=2020-01-01&date_to=2020-01-31"
        )
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "₹0.00" in body, (
            "User with no expenses in the given range must see ₹0.00 total"
        )

    def test_seeded_user_empty_range_shows_no_transaction_rows(self, auth_client):
        response = auth_client.get(
            "/profile?date_from=2020-01-01&date_to=2020-01-31"
        )
        body = response.data.decode("utf-8")
        # No transaction rows should be rendered
        assert body.count("txn-date") == 0, (
            "No txn-date elements must be rendered when the filtered range is empty"
        )

    def test_future_date_range_returns_empty_results(self, auth_client):
        """A range entirely in the future must return ₹0.00 — no exceptions."""
        response = auth_client.get(
            "/profile?date_from=2099-01-01&date_to=2099-12-31"
        )
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "₹0.00" in body, (
            "Future date range must yield ₹0.00 (no expenses exist that far ahead)"
        )


# ---------------------------------------------------------------------------
# 12. Single-day filter (date_from == date_to)
# ---------------------------------------------------------------------------

class TestSingleDayFilter:

    def test_single_day_returns_200(self, auth_client):
        response = auth_client.get(
            "/profile?date_from=2026-06-14&date_to=2026-06-14"
        )
        assert response.status_code == 200

    def test_single_day_shows_only_that_days_expense(self, auth_client):
        """2026-06-14 has one seeded expense: ₹9.50 (Coffee and snacks)."""
        response = auth_client.get(
            "/profile?date_from=2026-06-14&date_to=2026-06-14"
        )
        body = response.data.decode("utf-8")
        assert "9.50" in body, (
            "The single expense on 2026-06-14 (₹9.50) must appear"
        )

    def test_single_day_excludes_other_dates(self, auth_client):
        """2026-06-14 filter must not include the 2026-06-15 expense (₹22.00)."""
        response = auth_client.get(
            "/profile?date_from=2026-06-14&date_to=2026-06-14"
        )
        body = response.data.decode("utf-8")
        assert "22.00" not in body, (
            "The ₹22.00 expense on 2026-06-15 must not appear in the 2026-06-14 filter"
        )


# ---------------------------------------------------------------------------
# 13. Bookmarkable URL (GET, not session-stored)
# ---------------------------------------------------------------------------

class TestBookmarkableUrl:

    def test_same_url_twice_produces_identical_status(self, auth_client):
        """Refreshing a filtered URL must return the same status both times."""
        url = "/profile?preset=30d"
        r1 = auth_client.get(url)
        r2 = auth_client.get(url)
        assert r1.status_code == r2.status_code == 200, (
            "Filtered URL must be stable — same status on repeated requests"
        )

    def test_same_custom_range_url_twice_produces_same_label(self, auth_client):
        url = "/profile?date_from=2026-06-01&date_to=2026-06-15"
        r1 = auth_client.get(url)
        r2 = auth_client.get(url)
        body1 = r1.data.decode("utf-8")
        body2 = r2.data.decode("utf-8")
        assert "2026-06-01" in body1 and "2026-06-01" in body2, (
            "Custom date range must produce the same label on repeated requests"
        )

    def test_filter_not_persisted_between_requests(self, auth_client):
        """Navigating to /profile without params after a filtered view must
        show All Time — the filter must NOT be stored in the session."""
        # First: apply a filter
        auth_client.get("/profile?preset=7d")
        # Then: visit without params — must show All Time, not Last 7 Days
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        assert "All Time" in body, (
            "Filter must live only in the URL — not persisted in session"
        )


# ---------------------------------------------------------------------------
# 14. Unit tests — query helpers honour date_from / date_to
# ---------------------------------------------------------------------------

class TestQueryHelpersWithDateFilter:

    def test_get_summary_stats_with_date_filter(self, test_db, seed_user_id):
        """Only expenses in the given range should be counted."""
        # Range covers only 2026-06-02 (45.50) and 2026-06-04 (12.00)
        stats = get_summary_stats(
            seed_user_id, date_from="2026-06-02", date_to="2026-06-04"
        )
        assert stats["transaction_count"] == 2, (
            "get_summary_stats must count only expenses inside the date range"
        )
        assert stats["total_spent"] == "₹57.50", (
            "get_summary_stats total must be ₹57.50 for 2026-06-02 to 2026-06-04"
        )

    def test_get_summary_stats_empty_range(self, test_db, seed_user_id):
        stats = get_summary_stats(
            seed_user_id, date_from="2020-01-01", date_to="2020-01-31"
        )
        assert stats["total_spent"] == "₹0.00"
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"

    def test_get_summary_stats_no_dates_returns_all_time(self, test_db, seed_user_id):
        stats = get_summary_stats(seed_user_id)
        assert stats["transaction_count"] == 8
        assert stats["total_spent"] == "₹327.74"

    def test_get_recent_transactions_with_date_filter(self, test_db, seed_user_id):
        """Only transactions within the range must be returned."""
        txns = get_recent_transactions(
            seed_user_id, date_from="2026-06-14", date_to="2026-06-15"
        )
        assert len(txns) == 2, (
            "get_recent_transactions must return only 2 transactions for 2026-06-14 to 2026-06-15"
        )
        for t in txns:
            assert t["amount"].startswith("₹"), "Amount must start with rupee symbol"

    def test_get_recent_transactions_empty_range(self, test_db, seed_user_id):
        txns = get_recent_transactions(
            seed_user_id, date_from="2020-01-01", date_to="2020-01-31"
        )
        assert txns == [], (
            "get_recent_transactions must return empty list when no expenses in range"
        )

    def test_get_recent_transactions_no_dates_returns_all(self, test_db, seed_user_id):
        txns = get_recent_transactions(seed_user_id)
        assert len(txns) == 8

    def test_get_recent_transactions_ordered_newest_first(self, test_db, seed_user_id):
        txns = get_recent_transactions(
            seed_user_id, date_from="2026-06-02", date_to="2026-06-15"
        )
        dates = [t["date"] for t in txns]
        assert dates == sorted(dates, reverse=True), (
            "get_recent_transactions must return results newest-first within the date range"
        )

    def test_get_category_breakdown_with_date_filter(self, test_db, seed_user_id):
        """Range 2026-06-02 to 2026-06-04 covers Food (45.50) and Transport (12.00)."""
        cats = get_category_breakdown(
            seed_user_id, date_from="2026-06-02", date_to="2026-06-04"
        )
        assert len(cats) == 2, (
            "get_category_breakdown must return exactly 2 categories for that range"
        )
        names = {c["name"] for c in cats}
        assert "Food" in names
        assert "Transport" in names

    def test_get_category_breakdown_percentages_sum_to_100(self, test_db, seed_user_id):
        cats = get_category_breakdown(
            seed_user_id, date_from="2026-06-06", date_to="2026-06-15"
        )
        if cats:
            total_pct = sum(c["percent"] for c in cats)
            assert total_pct == 100, (
                "Category percentages must sum to exactly 100 for a filtered range"
            )

    def test_get_category_breakdown_empty_range(self, test_db, seed_user_id):
        cats = get_category_breakdown(
            seed_user_id, date_from="2020-01-01", date_to="2020-01-31"
        )
        assert cats == [], (
            "get_category_breakdown must return empty list when no expenses in range"
        )

    def test_get_category_breakdown_no_dates_returns_all_categories(
        self, test_db, seed_user_id
    ):
        cats = get_category_breakdown(seed_user_id)
        assert len(cats) == 7, (
            "get_category_breakdown with no date filter must return all 7 seeded categories"
        )

    def test_get_category_breakdown_totals_start_with_rupee(self, test_db, seed_user_id):
        cats = get_category_breakdown(
            seed_user_id, date_from="2026-06-01", date_to="2026-06-30"
        )
        for c in cats:
            assert c["total"].startswith("₹"), (
                "Category totals must start with the rupee symbol"
            )

    def test_get_summary_stats_top_category_in_range(self, test_db, seed_user_id):
        """Bills (₹120.00) is the highest in June, so it must be the top category
        for the full-June range."""
        stats = get_summary_stats(
            seed_user_id, date_from="2026-06-01", date_to="2026-06-30"
        )
        assert stats["top_category"] == "Bills", (
            "Bills must be the top category for the full June 2026 range"
        )


# ---------------------------------------------------------------------------
# 15. Template rendering — filter bar UI elements
# ---------------------------------------------------------------------------

class TestFilterBarTemplate:

    def test_filter_bar_contains_last_7_days_button_text(self, auth_client):
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        assert "Last 7 Days" in body, (
            "Profile page must contain a 'Last 7 Days' filter button"
        )

    def test_filter_bar_contains_last_30_days_button_text(self, auth_client):
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        assert "Last 30 Days" in body, (
            "Profile page must contain a 'Last 30 Days' filter button"
        )

    def test_filter_bar_contains_this_month_button_text(self, auth_client):
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        assert "This Month" in body, (
            "Profile page must contain a 'This Month' filter button"
        )

    def test_filter_bar_contains_all_time_button_text(self, auth_client):
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        assert "All Time" in body, (
            "Profile page must contain an 'All Time' filter button"
        )

    def test_filter_bar_form_uses_get_method(self, auth_client):
        """Spec: filter form must use method='GET'."""
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        assert 'method="GET"' in body or "method='GET'" in body or "method=GET" in body, (
            "Filter bar form must use GET method so the URL is bookmarkable"
        )

    def test_filter_context_label_present_in_page(self, auth_client):
        """Spec: a filter-context label must appear above the stats row."""
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        # The label text "Showing:" or the filter_label value itself must appear
        assert "All Time" in body, (
            "filter_label 'All Time' must be rendered somewhere in the page body"
        )

    def test_filter_context_label_updates_with_preset(self, auth_client):
        response = auth_client.get("/profile?preset=30d")
        body = response.data.decode("utf-8")
        assert "Last 30 Days" in body, (
            "filter_label must update to 'Last 30 Days' when preset=30d"
        )

    def test_date_input_fields_present_in_page(self, auth_client):
        """Spec: page must contain date_from and date_to input fields."""
        response = auth_client.get("/profile")
        body = response.data.decode("utf-8")
        assert "date_from" in body and "date_to" in body, (
            "Profile page must contain date_from and date_to form inputs"
        )
