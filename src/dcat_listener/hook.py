from __future__ import annotations

from collections import OrderedDict

from sqlalchemy import event

from .middleware import get_current_route
from .sql import extract_columns, extract_tables


class QueryBuffer:
    def __init__(self, max_entries: int = 2048):
        self._max = max_entries
        self._data: OrderedDict[tuple[str, str], set[str]] = OrderedDict()
        self._columns: dict[tuple[str, str], dict[str, set[str]]] = {}

    def record(
        self,
        method: str,
        path: str,
        tables: set[str],
        columns: dict[str, set[str]] | None = None,
    ) -> None:
        key = (method, path)
        if key in self._data:
            self._data[key] |= tables
            self._data.move_to_end(key)
        else:
            if len(self._data) >= self._max:
                evicted = next(iter(self._data))
                self._data.popitem(last=False)
                self._columns.pop(evicted, None)
            self._data[key] = set(tables)

        if columns:
            existing = self._columns.get(key, {})
            for tbl, cols in columns.items():
                existing.setdefault(tbl, set()).update(cols)
            self._columns[key] = existing

    def get(self, method: str, path: str) -> set[str]:
        return self._data.get((method, path), set())

    def get_columns(self, method: str, path: str) -> dict[str, set[str]]:
        return self._columns.get((method, path), {})

    def snapshot(self) -> dict[tuple[str, str], set[str]]:
        return {k: set(v) for k, v in self._data.items()}

    def snapshot_columns(self) -> dict[tuple[str, str], dict[str, set[str]]]:
        return {k: {t: set(c) for t, c in v.items()} for k, v in self._columns.items()}

    def clear(self) -> None:
        self._data.clear()
        self._columns.clear()


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
                columns = extract_columns(statement)
                buf.record(route[0], route[1], tables, columns or None)
        except Exception:
            pass
