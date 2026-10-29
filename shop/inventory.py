"""Inventory service: stock levels, reservations, and the database pool."""

from . import config
from .pool import Pool, PoolTimeout
from .rpc import ServiceError

SERVICE = "inventory"


class Inventory:
    def __init__(self, runtime, telemetry, connect):
        self.runtime, self.telemetry = runtime, telemetry
        self.pool = Pool(runtime, connect, config.POOL_SIZE, config.POOL_TIMEOUT_MS)
        self.running = True

    async def stock(self, sku):
        with self.telemetry.span(SERVICE, "GET /stock/{sku}", sku=sku):
            connection = await self._connection()
            try:
                return await self._read_stock(connection, sku)
            finally:
                self.pool.release(connection)

    async def reserve(self, sku, quantity):
        with self.telemetry.span(SERVICE, "POST /reserve", sku=sku, quantity=quantity):
            connection = await self._connection()
            try:
                stock = await self._read_stock(connection, sku)
                if stock < quantity:
                    raise ServiceError(409, f"out of stock: {sku}")
                connection.execute("UPDATE items SET stock = stock - ? WHERE sku = ?", (quantity, sku))
                await self.runtime.sleep(config.QUERY_MS)
                return stock - quantity
            finally:
                self.pool.release(connection)

    async def report_pool(self):
        while self.running:
            self.telemetry.gauge(SERVICE, "db.client.connections.usage", self.pool.in_use)
            self.telemetry.gauge(SERVICE, "db.client.connections.pending_requests", self.pool.waiting)
            await self.runtime.sleep(config.POOL_REPORT_MS)

    async def _connection(self):
        try:
            return await self.pool.acquire()
        except PoolTimeout as exc:
            self.telemetry.log(SERVICE, "ERROR", f"database pool: {exc}")
            raise ServiceError(503, "database unavailable") from exc

    async def _read_stock(self, connection, sku):
        row = connection.execute("SELECT stock FROM items WHERE sku = ?", (sku,)).fetchone()
        await self.runtime.sleep(config.QUERY_MS)
        if row is None:
            raise ServiceError(404, f"unknown sku: {sku}")
        return row[0]
