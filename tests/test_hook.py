from unittest.mock import patch

from sqlalchemy import create_engine, text

from dcat_listener.hook import QueryBuffer, install_hook


class TestQueryBuffer:
    def test_record_adds_tables(self):
        buf = QueryBuffer(max_entries=100)
        buf.record("GET", "/v1/users", {"users", "profiles"})
        assert buf.get("GET", "/v1/users") == {"users", "profiles"}

    def test_record_merges_tables(self):
        buf = QueryBuffer(max_entries=100)
        buf.record("GET", "/v1/users", {"users"})
        buf.record("GET", "/v1/users", {"profiles"})
        assert buf.get("GET", "/v1/users") == {"users", "profiles"}

    def test_max_entries_bounds_buffer(self):
        buf = QueryBuffer(max_entries=3)
        for i in range(5):
            buf.record("GET", f"/v1/route{i}", {f"table{i}"})
        assert len(buf.snapshot()) <= 3

    def test_snapshot_returns_copy(self):
        buf = QueryBuffer(max_entries=100)
        buf.record("GET", "/v1/users", {"users"})
        snap = buf.snapshot()
        buf.record("GET", "/v1/users", {"orders"})
        assert "orders" not in snap[("GET", "/v1/users")]

    def test_clear(self):
        buf = QueryBuffer(max_entries=100)
        buf.record("GET", "/v1/users", {"users"})
        buf.clear()
        assert buf.snapshot() == {}


class TestInstallHook:
    def test_captures_query_with_context(self):
        engine = create_engine("sqlite:///:memory:")
        buf = QueryBuffer(max_entries=100)

        install_hook(engine, buf)

        with patch("dcat_listener.hook.get_current_route", return_value=("GET", "/v1/users")):
            with engine.connect() as conn:
                conn.execute(text("CREATE TABLE users (id INTEGER)"))
                conn.execute(text("SELECT * FROM users"))

        assert "users" in buf.get("GET", "/v1/users")

    def test_ignores_query_without_context(self):
        engine = create_engine("sqlite:///:memory:")
        buf = QueryBuffer(max_entries=100)

        install_hook(engine, buf)

        with patch("dcat_listener.hook.get_current_route", return_value=None):
            with engine.connect() as conn:
                conn.execute(text("CREATE TABLE orders (id INTEGER)"))
                conn.execute(text("SELECT * FROM orders"))

        assert buf.snapshot() == {}

    def test_hook_does_not_raise_on_bad_sql(self):
        engine = create_engine("sqlite:///:memory:")
        buf = QueryBuffer(max_entries=100)

        install_hook(engine, buf)

        with patch("dcat_listener.hook.get_current_route", return_value=("GET", "/test")):
            with engine.connect() as conn:
                conn.execute(text("CREATE TABLE t (id INTEGER)"))
                conn.execute(text("SELECT 1"))
