"""The inventory database: SQLite, shared in memory between the pool's connections."""

import sqlite3

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
