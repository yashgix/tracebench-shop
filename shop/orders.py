"""Orders service: places an order by reserving stock in inventory."""

from .rpc import ServiceError, call

SERVICE = "orders"


class Orders:
    def __init__(self, runtime, telemetry, inventory):
        self.runtime, self.telemetry, self.inventory = runtime, telemetry, inventory
        self.placed = 0

    async def place(self, user, sku, quantity):
        with self.telemetry.span(SERVICE, "POST /orders", user=user, sku=sku):
            try:
                await call(self.runtime, self.telemetry, SERVICE, "inventory", "POST /reserve",
                           self.inventory.reserve, sku, quantity)
            except ServiceError as exc:
                if exc.status < 500:
                    self.telemetry.log(SERVICE, "INFO", f"order rejected: {exc}")
                    raise
                self.telemetry.log(SERVICE, "ERROR", f"reserve failed: {exc.status} {exc}")
                raise ServiceError(503, "inventory unavailable") from exc
            self.placed += 1
            return self.placed
