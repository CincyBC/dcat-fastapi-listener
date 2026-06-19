import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dcat_listener.middleware import RequestContextMiddleware, get_current_route


class TestRequestContextMiddleware:
    def test_context_var_set_during_request(self):
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)
        captured = {}

        @app.get("/v1/users/{user_id}")
        def get_user(user_id: int):
            route = get_current_route()
            captured["route"] = route
            return {"ok": True}

        client = TestClient(app)
        client.get("/v1/users/42")
        assert captured["route"] == ("GET", "/v1/users/{user_id}")

    def test_context_var_cleared_after_request(self):
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)

        @app.get("/health")
        def health():
            return {"ok": True}

        client = TestClient(app)
        client.get("/health")
        assert get_current_route() is None

    def test_post_method(self):
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)
        captured = {}

        @app.post("/v1/address/")
        def create_address():
            captured["route"] = get_current_route()
            return {"ok": True}

        client = TestClient(app)
        client.post("/v1/address/")
        assert captured["route"] == ("POST", "/v1/address/")

    def test_middleware_does_not_break_on_error_route(self):
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)

        @app.get("/boom")
        def boom():
            raise ValueError("intentional")

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/boom")
        assert resp.status_code == 500
        assert get_current_route() is None
