from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from .hook import QueryBuffer, install_hook
from .middleware import RequestContextMiddleware
from .shipper import Shipper

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy import Engine


def attach_query_listener(
    app: FastAPI,
    engine: Engine,
    *,
    catalog_url: str,
    api_slug: str = "",
    flush_interval: float = 300.0,
    max_entries: int = 2048,
) -> tuple[QueryBuffer, Shipper]:
    buf = QueryBuffer(max_entries=max_entries)
    shipper = Shipper(buf, catalog_url=catalog_url, api_slug=api_slug)

    app.add_middleware(RequestContextMiddleware)
    install_hook(engine, buf)

    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def _lifespan(a):
        timer: asyncio.TimerHandle | None = None

        async def _periodic_flush():
            nonlocal timer
            try:
                await shipper.flush()
            except Exception:
                pass
            loop = asyncio.get_running_loop()
            timer = loop.call_later(flush_interval, lambda: loop.create_task(_periodic_flush()))

        loop = asyncio.get_running_loop()
        timer = loop.call_later(flush_interval, lambda: loop.create_task(_periodic_flush()))

        async with original_lifespan(a) as state:
            yield state

        if timer is not None:
            timer.cancel()
        await _flush_on_shutdown()

    async def _flush_on_shutdown():
        try:
            await shipper.flush()
        except Exception:
            pass

    app.router.lifespan_context = _lifespan
    app.router.on_shutdown.append(_flush_on_shutdown)

    return buf, shipper
