import pytest
import database.db as db_module
from database.db import init_db, seed_db, get_db
from app import app as flask_app


@pytest.fixture
def test_db(tmp_path, monkeypatch):
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
    conn = get_db()
    try:
        from werkzeug.security import generate_password_hash
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("New User", "new@test.com", generate_password_hash("pass")),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("new@test.com",)
        ).fetchone()
        return row["id"]
    finally:
        conn.close()
