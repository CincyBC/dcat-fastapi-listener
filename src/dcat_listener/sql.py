from __future__ import annotations

import sqlglot
import sqlglot.expressions as exp


def extract_tables(sql: str | None) -> set[str]:
    if not sql:
        return set()
    try:
        parsed = sqlglot.parse_one(sql, error_level=sqlglot.ErrorLevel.IGNORE)
    except Exception:
        return set()
    if parsed is None:
        return set()

    cte_names = {cte.alias.lower() for cte in parsed.find_all(exp.CTE) if cte.alias}

    tables: set[str] = set()
    for tbl in parsed.find_all(exp.Table):
        name = tbl.name
        if not name or name.lower() in cte_names:
            continue
        schema = tbl.db
        tables.add(f"{schema}.{name}" if schema else name)
    return tables
