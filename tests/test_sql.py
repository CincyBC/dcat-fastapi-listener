from dcat_listener.sql import extract_tables


class TestExtractTables:
    def test_simple_select(self):
        assert extract_tables("SELECT * FROM users") == {"users"}

    def test_join(self):
        result = extract_tables(
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
        )
        assert result == {"users", "orders"}

    def test_schema_qualified(self):
        result = extract_tables("SELECT * FROM location.addresses")
        assert result == {"location.addresses"}

    def test_insert(self):
        assert extract_tables("INSERT INTO events (name) VALUES ('click')") == {"events"}

    def test_update(self):
        assert extract_tables("UPDATE users SET name = 'x' WHERE id = 1") == {"users"}

    def test_delete(self):
        assert extract_tables("DELETE FROM sessions WHERE expired = true") == {"sessions"}

    def test_subquery(self):
        result = extract_tables(
            "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)"
        )
        assert result == {"users", "orders"}

    def test_cte_excluded(self):
        result = extract_tables(
            "WITH active AS (SELECT * FROM users WHERE active) SELECT * FROM active"
        )
        assert result == {"users"}

    def test_garbage_returns_empty(self):
        assert extract_tables("not sql at all") == set()

    def test_empty_string(self):
        assert extract_tables("") == set()

    def test_none_returns_empty(self):
        assert extract_tables(None) == set()

    def test_multiple_schemas(self):
        result = extract_tables(
            "SELECT a.id, p.number FROM location.addresses a "
            "JOIN parcels.parcel_data p ON a.id = p.address_id"
        )
        assert result == {"location.addresses", "parcels.parcel_data"}
