# dcat-fastapi-listener

Lightweight SQLAlchemy query listener for FastAPI apps. Captures which database tables each API endpoint touches at runtime and ships the mappings to a DCAT catalog for lineage tracking.

## How it works

1. A **middleware** tags each request with its HTTP method and path template via a context variable
2. A **SQLAlchemy `before_cursor_execute` hook** captures every SQL statement, extracts table names, and associates them with the current request
3. A **background shipper** periodically POSTs the accumulated endpoint→table mappings to the catalog, then clears the buffer

All hooks are wrapped in `try/except` — if the listener fails at any point, the API request proceeds unaffected.

## Install

```bash
pip install git+https://github.com/cincybc/dcat-fastapi-listener.git
```

Or pin to a tag:

```bash
pip install git+https://github.com/cincybc/dcat-fastapi-listener.git@v0.1.0
```

## Usage

```python
from fastapi import FastAPI
from sqlalchemy import create_engine
from dcat_listener import attach_query_listener

app = FastAPI()
engine = create_engine("postgresql://...")

attach_query_listener(
    app,
    engine,
    catalog_url="http://192.168.86.115/api/v1/lineage/sql",
    api_slug="psql-hamco",
    flush_interval=300.0,  # seconds between flushes (default: 5 min)
)
```

That's it. The listener will start capturing SQL queries and shipping lineage data on the flush interval and on shutdown.

## What gets shipped

The shipper POSTs JSON to `catalog_url`:

```json
{
  "api_slug": "psql-hamco",
  "mappings": [
    {"method": "GET", "path": "/v1/address/", "tables": ["addresses"]},
    {"method": "POST", "path": "/v1/address/", "tables": ["addresses", "parcel_to_address"]}
  ]
}
```

The catalog side receives this and writes `prov:used` / `ex:modifiesTable` lineage triples linking operation nodes to table nodes.

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `catalog_url` | (required) | URL of the catalog lineage ingestion endpoint |
| `api_slug` | `""` | API slug matching the Oxigraph operation URI prefix |
| `flush_interval` | `300.0` | Seconds between automatic flushes |
| `max_entries` | `2048` | Max unique (method, path) pairs to buffer |

## Development

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest
```
