import itertools
import random

from shop.app import Shop
from shop.runtime import Runtime
from shop.telemetry import Telemetry

_names = itertools.count()


def shop(stock=None):
    runtime = Runtime()
    telemetry = Telemetry(runtime, random.Random(1))
    return Shop(runtime, telemetry, f"test-{next(_names)}", stock or {"sku-1": 3})


def run(runtime, coro, until=60_000):
    """Run *coro* to completion on *runtime* and return its result."""
    box = {}

    async def wrapper():
        box["value"] = await coro

    runtime.spawn(wrapper())
    runtime.run(runtime.now + until)
    return box["value"]
