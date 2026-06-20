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


def extract_columns(sql: str | None) -> dict[str, set[str]]:
    """Extract {table_name: {col, ...}} from SELECT columns.

    Resolves table aliases so columns are keyed by the real
    (optionally schema-qualified) table name.  Columns from
    ``SELECT *`` or unresolvable references are silently skipped.
    """
    if not sql:
        return {}
    try:
        parsed = sqlglot.parse_one(sql, error_level=sqlglot.ErrorLevel.IGNORE)
    except Exception:
        return {}
    if parsed is None or not isinstance(parsed, exp.Select):
        return {}

    cte_names = {cte.alias.lower() for cte in parsed.find_all(exp.CTE) if cte.alias}

    alias_map: dict[str, str] = {}
    for tbl in parsed.find_all(exp.Table):
        name = tbl.name
        if not name or name.lower() in cte_names:
            continue
        full = f"{tbl.db}.{name}" if tbl.db else name
        if tbl.alias:
            alias_map[tbl.alias.lower()] = full
        alias_map[name.lower()] = full

    out: dict[str, set[str]] = {}
    for col in parsed.find_all(exp.Column):
        col_name = col.name
        if not col_name:
            continue
        table_ref = col.table
        if not table_ref:
            if len(alias_map) == 1:
                table_ref = next(iter(alias_map))
            else:
                continue
        real_table = alias_map.get(table_ref.lower())
        if not real_table:
            continue
        out.setdefault(real_table, set()).add(col_name)
    return out
