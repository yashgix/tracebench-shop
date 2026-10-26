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

    def test_one_trace_per_request(self):
        app = shop()
        run(app.runtime, app.web.checkout("u1", "sku-1", 1))
        self.assertEqual(len({s["trace_id"] for s in app.telemetry.spans}), 1)
        self.assertEqual([s["service"] for s in app.telemetry.spans if s["kind"] == "server"],
                         ["inventory", "orders", "web"])


if __name__ == "__main__":
    unittest.main()
