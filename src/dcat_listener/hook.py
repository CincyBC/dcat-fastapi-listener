from __future__ import annotations

from collections import OrderedDict

from sqlalchemy import event

from .middleware import get_current_route
from .sql import extract_tables


class QueryBuffer:
    def __init__(self, max_entries: int = 2048):
        self._max = max_entries
        self._data: OrderedDict[tuple[str, str], set[str]] = OrderedDict()

    def record(self, method: str, path: str, tables: set[str]) -> None:
        key = (method, path)
        if key in self._data:
            self._data[key] |= tables
            self._data.move_to_end(key)
        else:
            if len(self._data) >= self._max:
                self._data.popitem(last=False)
            self._data[key] = set(tables)

    def get(self, method: str, path: str) -> set[str]:
        return self._data.get((method, path), set())

    def snapshot(self) -> dict[tuple[str, str], set[str]]:
        return {k: set(v) for k, v in self._data.items()}

    def clear(self) -> None:
        self._data.clear()


def install_hook(engine, buf: QueryBuffer) -> None:
    target = getattr(engine, "sync_engine", engine)

    @event.listens_for(target, "before_cursor_execute")
    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        try:
            route = get_current_route()
            if route is None:
                return
            tables = extract_tables(statement)
            if tables:
                buf.record(route[0], route[1], tables)
        except Exception:
            pass
