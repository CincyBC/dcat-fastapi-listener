import json
from unittest.mock import AsyncMock, patch

import pytest

from dcat_listener.hook import QueryBuffer
from dcat_listener.shipper import Shipper


class TestShipperPayload:
    def test_build_payload_from_buffer(self):
        buf = QueryBuffer(max_entries=100)
        buf.record("GET", "/v1/users", {"users", "profiles"})
        buf.record("POST", "/v1/orders", {"orders"})

        shipper = Shipper(buf, catalog_url="http://catalog/api/v1/lineage/sql", api_slug="my-api")
        payload = shipper.build_payload()

        assert payload["api_slug"] == "my-api"
        assert len(payload["mappings"]) == 2

        by_key = {(m["method"], m["path"]): set(m["tables"]) for m in payload["mappings"]}
        assert by_key[("GET", "/v1/users")] == {"users", "profiles"}
        assert by_key[("POST", "/v1/orders")] == {"orders"}

    def test_build_payload_empty_buffer(self):
        buf = QueryBuffer(max_entries=100)
        shipper = Shipper(buf, catalog_url="http://catalog/api/v1/lineage/sql", api_slug="my-api")
        payload = shipper.build_payload()
        assert payload["mappings"] == []


class TestShipperFlush:
    @pytest.mark.asyncio
    async def test_flush_clears_buffer_on_success(self):
        buf = QueryBuffer(max_entries=100)
        buf.record("GET", "/v1/users", {"users"})

        shipper = Shipper(buf, catalog_url="http://catalog/api/v1/lineage/sql", api_slug="my-api")

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = AsyncMock()

        with patch("dcat_listener.shipper.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            await shipper.flush()

        assert buf.snapshot() == {}

    @pytest.mark.asyncio
    async def test_flush_retains_buffer_on_failure(self):
        buf = QueryBuffer(max_entries=100)
        buf.record("GET", "/v1/users", {"users"})

        shipper = Shipper(buf, catalog_url="http://catalog/api/v1/lineage/sql", api_slug="my-api")

        with patch("dcat_listener.shipper.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.side_effect = Exception("connection refused")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            await shipper.flush()

        assert buf.get("GET", "/v1/users") == {"users"}

    @pytest.mark.asyncio
    async def test_flush_skips_when_empty(self):
        buf = QueryBuffer(max_entries=100)
        shipper = Shipper(buf, catalog_url="http://catalog/api/v1/lineage/sql", api_slug="my-api")

        with patch("dcat_listener.shipper.httpx.AsyncClient") as MockClient:
            await shipper.flush()
            MockClient.assert_not_called()
