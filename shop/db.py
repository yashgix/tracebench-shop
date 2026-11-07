"""The inventory database: SQLite, shared in memory between the pool's connections."""

import re
import sqlite3

from . import config

SCHEMA = "CREATE TABLE items (sku TEXT PRIMARY KEY, stock INTEGER NOT NULL)"


def connector(name):
    uri = f"file:{name}?mode=memory&cache=shared"
    return lambda: sqlite3.connect(uri, uri=True, isolation_level=None)


def create(connect, stock):
    """Create and fill the database; the returned connection keeps it alive."""
    keeper = connect()
    keeper.execute(SCHEMA)
    keeper.executemany("INSERT INTO items VALUES (?, ?)", sorted(stock.items()))
    return keeper


SCAN = re.compile(r"\bSCAN (\w+)")


async def query(runtime, connection, sql, params=()):
    """Run one statement and wait what SQLite's plan says it costs: QUERY_MS, plus each row of a scanned table."""
    plan = " ".join(row[3] for row in connection.execute("EXPLAIN QUERY PLAN " + sql, params))
    rows = connection.execute(sql, params).fetchall()
    scanned = sum(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in SCAN.findall(plan))
    await runtime.sleep(config.QUERY_MS + scanned * config.SCAN_US_PER_ROW // 1000)
    return rows
