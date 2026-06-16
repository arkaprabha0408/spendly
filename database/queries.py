from datetime import datetime
from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        words = row["name"].split()
        initials = "".join(w[0].upper() for w in words if w)[:2]
        try:
            dt = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = datetime.strptime(row["created_at"][:10], "%Y-%m-%d")
        return {
            "name": row["name"],
            "email": row["email"],
            "initials": initials,
            "member_since": dt.strftime("%B %Y"),
        }
    finally:
        conn.close()


def get_summary_stats(user_id):
    conn = get_db()
    try:
        agg = conn.execute(
            "SELECT SUM(amount) AS total, COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        count = agg["cnt"] or 0
        if count == 0:
            return {"total_spent": "₹0.00", "transaction_count": 0, "top_category": "—"}
        top_row = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return {
            "total_spent": f"₹{agg['total']:,.2f}",
            "transaction_count": count,
            "top_category": top_row["category"],
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount "
            "FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        result = []
        for row in rows:
            dt = datetime.strptime(row["date"], "%Y-%m-%d")
            result.append({
                "date": dt.strftime("%d %b %Y"),
                "description": row["description"],
                "category": row["category"],
                "amount": f"₹{row['amount']:,.2f}",
            })
        return result
    finally:
        conn.close()


def get_category_breakdown(user_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total "
            "FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY total DESC",
            (user_id,),
        ).fetchall()
        if not rows:
            return []
        grand_total = sum(row["total"] for row in rows)
        breakdown = []
        for row in rows:
            pct = round(row["total"] / grand_total * 100)
            breakdown.append({
                "name": row["category"],
                "total": f"₹{row['total']:,.2f}",
                "percent": pct,
            })
        # adjust largest category so all percentages sum to exactly 100
        remainder = 100 - sum(item["percent"] for item in breakdown)
        breakdown[0]["percent"] += remainder
        return breakdown
    finally:
        conn.close()
