import unittest

from helpers import run, shop


class CheckoutTest(unittest.TestCase):
    def test_checkout_reserves_stock(self):
        app = shop({"sku-1": 3})
        self.assertEqual(run(app.runtime, app.web.checkout("u1", "sku-1", 2)), 200)
        self.assertEqual(app.keeper.execute("SELECT stock FROM items").fetchone()[0], 1)
        self.assertEqual(app.orders.placed, 1)

    def test_out_of_stock_is_a_conflict(self):
        app = shop({"sku-1": 1})
        self.assertEqual(run(app.runtime, app.web.checkout("u1", "sku-1", 2)), 409)
        self.assertEqual(app.orders.placed, 0)

    def test_unknown_product_is_not_found(self):
        app = shop()
        self.assertEqual(run(app.runtime, app.web.product("nope")), 404)

    def test_a_user_over_the_limit_is_slowed_down(self):
        app, statuses = shop({"sku-1": 100}), []

        async def buy():
            statuses.append(await app.web.checkout("u1", "sku-1", 1))

        for _ in range(6):
            app.runtime.spawn(buy())
        app.runtime.run(1_000)
        self.assertEqual(sorted(statuses), [200] * 5 + [503])

    def test_a_slow_upstream_times_out(self):
        app = shop()

        async def stuck(sku):
            await app.runtime.sleep(60_000)

        app.web.inventory.stock = stuck
        self.assertEqual(run(app.runtime, app.web.product("sku-1"), until=5_000), 502)

    def test_one_trace_per_request(self):
        app = shop()
        run(app.runtime, app.web.checkout("u1", "sku-1", 1))
        self.assertEqual(len({s["trace_id"] for s in app.telemetry.spans}), 1)
        self.assertEqual([s["service"] for s in app.telemetry.spans if s["kind"] == "server"],
                         ["inventory", "orders", "web"])


if __name__ == "__main__":
    unittest.main()
