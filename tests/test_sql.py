from dcat_listener.sql import extract_columns, extract_tables


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


class TestExtractColumns:
    def test_simple_select(self):
        result = extract_columns("SELECT id, name FROM users")
        assert result == {"users": {"id", "name"}}

    def test_aliased_table(self):
        result = extract_columns("SELECT u.id, u.name FROM users u")
        assert result == {"users": {"id", "name"}}

    def test_join_columns_per_table(self):
        result = extract_columns(
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
        )
        assert result == {"users": {"name", "id"}, "orders": {"total", "user_id"}}

    def test_schema_qualified_table(self):
        result = extract_columns("SELECT a.id, a.street FROM location.addresses a")
        assert result == {"location.addresses": {"id", "street"}}

    def test_multiple_schema_tables(self):
        result = extract_columns(
            "SELECT a.id, p.number FROM location.addresses a "
            "JOIN parcels.parcel_data p ON a.id = p.address_id"
        )
        assert result == {
            "location.addresses": {"id"},
            "parcels.parcel_data": {"number", "address_id"},
        }

    def test_star_is_skipped(self):
        result = extract_columns("SELECT * FROM users")
        assert result == {}

    def test_not_a_select(self):
        result = extract_columns("INSERT INTO users (name) VALUES ('x')")
        assert result == {}

    def test_none(self):
        assert extract_columns(None) == {}

    def test_garbage(self):
        assert extract_columns("not sql") == {}

    def test_single_table_unqualified_columns(self):
        result = extract_columns("SELECT id, name FROM users")
        assert result == {"users": {"id", "name"}}
