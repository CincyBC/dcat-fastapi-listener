from unittest.mock import patch, AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from dcat_listener import attach_query_listener
from dcat_listener.hook import QueryBuffer


class TestAttachQueryListener:
    def test_returns_buffer_and_shipper(self):
        app = FastAPI()
        engine = create_engine("sqlite:///:memory:")
        buf, shipper = attach_query_listener(
            app, engine, catalog_url="http://catalog/api", api_slug="test-api"
        )
        assert isinstance(buf, QueryBuffer)
        assert shipper is not None

    def test_end_to_end_captures_lineage(self, tmp_path):
        db_path = tmp_path / "test.db"
        app = FastAPI()
        engine = create_engine(f"sqlite:///{db_path}")

        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE addresses (id INTEGER, street TEXT)"))
            conn.commit()

        buf, _ = attach_query_listener(
            app, engine, catalog_url="http://catalog/api", api_slug="test-api"
        )

        @app.get("/v1/address/")
        def list_addresses():
            with engine.connect() as conn:
                conn.execute(text("SELECT * FROM addresses"))
            return {"ok": True}

        @app.post("/v1/address/")
        def create_address():
            with engine.connect() as conn:
                conn.execute(
                    text("INSERT INTO addresses (id, street) VALUES (1, 'Main St')")
                )
                conn.commit()
            return {"ok": True}

        client = TestClient(app)
        client.get("/v1/address/")
        client.post("/v1/address/")

        snap = buf.snapshot()
        assert "addresses" in snap[("GET", "/v1/address/")]
        assert "addresses" in snap[("POST", "/v1/address/")]

    def test_registers_shutdown_event(self):
        app = FastAPI()
        engine = create_engine("sqlite:///:memory:")
        attach_query_listener(
            app, engine, catalog_url="http://catalog/api", api_slug="test-api"
        )
        handler_names = [
            h.__name__ for h in app.router.on_shutdown
        ]
        assert "_flush_on_shutdown" in handler_names

    def test_request_succeeds_even_if_sql_extraction_fails(self):
        app = FastAPI()
        engine = create_engine("sqlite:///:memory:")
        attach_query_listener(
            app, engine, catalog_url="http://catalog/api", api_slug="test-api"
        )

        @app.get("/v1/test")
        def test_route():
            with engine.connect() as conn:
                conn.execute(text("PRAGMA table_info('nonexistent')"))
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/v1/test")
        assert resp.status_code == 200
