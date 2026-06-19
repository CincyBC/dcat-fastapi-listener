from __future__ import annotations

import httpx

from .hook import QueryBuffer


class Shipper:
    def __init__(self, buf: QueryBuffer, *, catalog_url: str, api_slug: str):
        self._buf = buf
        self._catalog_url = catalog_url
        self._api_slug = api_slug

    def build_payload(self) -> dict:
        snap = self._buf.snapshot()
        return {
            "api_slug": self._api_slug,
            "mappings": [
                {"method": method, "path": path, "tables": sorted(tables)}
                for (method, path), tables in snap.items()
            ],
        }

    async def flush(self) -> None:
        if not self._buf.snapshot():
            return
        payload = self.build_payload()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self._catalog_url,
                    json=payload,
                    timeout=10.0,
                )
                resp.raise_for_status()
            self._buf.clear()
        except Exception:
            pass
