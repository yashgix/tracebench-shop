import unittest

from shop.pool import Pool, PoolTimeout
from shop.runtime import Runtime


class PoolTest(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.pool = Pool(self.runtime, object, size=2, timeout_ms=100)
        self.results = []

    def take(self, hold_ms=None):
        async def task():
            try:
                connection = await self.pool.acquire()
            except PoolTimeout:
                self.results.append(("timeout", self.runtime.now))
                return
            self.results.append(("got", self.runtime.now))
            if hold_ms is not None:
                await self.runtime.sleep(hold_ms)
                self.pool.release(connection)
        self.runtime.spawn(task())

    def test_opens_up_to_size(self):
        self.take(), self.take()
        self.runtime.run(10)
        self.assertEqual((self.pool.opened, self.pool.in_use), (2, 2))

    def test_waiter_gets_a_released_connection(self):
        self.take(50), self.take(50), self.take(50)
        self.runtime.run(1000)
        self.assertEqual(self.results, [("got", 0), ("got", 0), ("got", 50)])
        self.assertEqual(self.pool.in_use, 0)

    def test_waiter_times_out(self):
        self.take(), self.take(), self.take()
        self.runtime.run(1000)
        self.assertEqual(self.results[-1], ("timeout", 100))
        self.assertEqual(self.pool.waiting, 0)


if __name__ == "__main__":
    unittest.main()
