"""Web front end: the public checkout and product pages."""

from . import config
from .rpc import ServiceError, call

SERVICE = "web"


class Web:
    def __init__(self, runtime, telemetry, orders, inventory):
        self.runtime, self.telemetry = runtime, telemetry
        self.orders, self.inventory = orders, inventory
        self._window, self._counts = None, {}

    async def checkout(self, user, sku, quantity):
        key = user if config.CHECKOUT_LIMIT_KEY == "user" else sku
        if self._count(key) > config.CHECKOUT_LIMIT:
            return self._slow_down(key)
        return await self._serve("POST /checkout", "orders", "POST /orders", self.orders.place, user, sku, quantity)

    async def product(self, sku):
        return await self._serve("GET /products/{sku}", "inventory", "GET /stock/{sku}", self.inventory.stock, sku)

    def _count(self, key):
        window = self.runtime.now // config.CHECKOUT_LIMIT_WINDOW_MS
        if window != self._window:
            self._window, self._counts = window, {}
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    def _slow_down(self, key):
        with self.telemetry.span(SERVICE, "POST /checkout") as span:
            if self._counts[key] == config.CHECKOUT_LIMIT + 1:
                self.telemetry.log(SERVICE, "WARN", f"checkout limit reached for {key}: 503 until the window ends")
            span["attributes"]["http.status_code"] = 503
            span["status"] = "ERROR"
        return 503

    async def _serve(self, route, target, name, handler, *args):
        with self.telemetry.span(SERVICE, route) as span:
            try:
                await call(self.runtime, self.telemetry, SERVICE, target, name, handler, *args,
                           timeout_ms=config.UPSTREAM_TIMEOUT_MS)
                status = 200
            except ServiceError as exc:
                status = exc.status if exc.status < 500 else 502
                if status >= 500:
                    self.telemetry.log(SERVICE, "ERROR", f"{route} failed: {target} {name} returned {exc.status}")
            span["attributes"]["http.status_code"] = status
            if status >= 500:
                span["status"] = "ERROR"
            return status
