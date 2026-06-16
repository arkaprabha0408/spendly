from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


# ── get_user_by_id ──────────────────────────────────────────────────────────

def test_get_user_by_id_valid(test_db, seed_user_id):
    user = get_user_by_id(seed_user_id)
    assert user is not None
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["initials"] == "DU"
    assert "member_since" in user
    # format should be "Month YYYY"
    parts = user["member_since"].split()
    assert len(parts) == 2
    assert parts[1].isdigit()


def test_get_user_by_id_invalid(test_db):
    assert get_user_by_id(99999) is None


# ── get_summary_stats ────────────────────────────────────────────────────────

def test_get_summary_stats_with_expenses(test_db, seed_user_id):
    stats = get_summary_stats(seed_user_id)
    assert stats["total_spent"] == "₹327.74"
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(test_db, blank_user_id):
    stats = get_summary_stats(blank_user_id)
    assert stats == {"total_spent": "₹0.00", "transaction_count": 0, "top_category": "—"}


# ── get_recent_transactions ──────────────────────────────────────────────────

def test_get_recent_transactions_with_expenses(test_db, seed_user_id):
    txns = get_recent_transactions(seed_user_id)
    assert len(txns) == 8
    # newest first: 2026-06-15 should come before 2026-06-14, etc.
    assert txns[0]["date"] == "15 Jun 2026"
    for t in txns:
        assert "date" in t
        assert "description" in t
        assert "category" in t
        assert "amount" in t
        assert t["amount"].startswith("₹")


def test_get_recent_transactions_no_expenses(test_db, blank_user_id):
    assert get_recent_transactions(blank_user_id) == []


# ── get_category_breakdown ───────────────────────────────────────────────────

def test_get_category_breakdown_with_expenses(test_db, seed_user_id):
    cats = get_category_breakdown(seed_user_id)
    assert len(cats) == 7
    # ordered by amount descending — Bills (120.00) must be first
    assert cats[0]["name"] == "Bills"
    for c in cats:
        assert "name" in c
        assert "total" in c
        assert isinstance(c["percent"], int)
        assert c["total"].startswith("₹")
    assert sum(c["percent"] for c in cats) == 100


def test_get_category_breakdown_no_expenses(test_db, blank_user_id):
    assert get_category_breakdown(blank_user_id) == []


# ── Route: GET /profile ───────────────────────────────────────────────────────

def test_profile_unauthenticated(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated(client, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"

    response = client.get("/profile")
    assert response.status_code == 200
    body = response.data.decode("utf-8")

    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body
    assert "327.74" in body
    assert "Bills" in body
    # 8 transaction rows — count occurrences of a per-row class
    assert body.count("txn-date") == 8
    # 7 category rows — count the opening <li> tag, not the class prefix
    assert body.count('class="cat-row"') == 7
