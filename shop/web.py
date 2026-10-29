"""Web front end: the public checkout and product pages."""

from .rpc import ServiceError, call

SERVICE = "web"


class Web:
    def __init__(self, runtime, telemetry, orders, inventory):
        self.runtime, self.telemetry = runtime, telemetry
        self.orders, self.inventory = orders, inventory

    async def checkout(self, user, sku, quantity):
        return await self._serve("POST /checkout", "orders", "POST /orders", self.orders.place, user, sku, quantity)

    async def product(self, sku):
        return await self._serve("GET /products/{sku}", "inventory", "GET /stock/{sku}", self.inventory.stock, sku)

    async def _serve(self, route, target, name, handler, *args):
        with self.telemetry.span(SERVICE, route) as span:
            try:
                await call(self.runtime, self.telemetry, SERVICE, target, name, handler, *args)
                status = 200
            except ServiceError as exc:
                status = exc.status if exc.status < 500 else 502
                if status >= 500:
                    self.telemetry.log(SERVICE, "ERROR", f"{route} failed: upstream {target} returned {exc.status}")
            span["attributes"]["http.status_code"] = status
            if status >= 500:
                span["status"] = "ERROR"
            return status
