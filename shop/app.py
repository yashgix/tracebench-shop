"""Wires the three services together over one runtime and one telemetry sink."""

from . import db
from .inventory import Inventory
from .orders import Orders
from .web import Web


class Shop:
    def __init__(self, runtime, telemetry, db_name, stock):
        self.runtime, self.telemetry = runtime, telemetry
        self.connect = db.connector(db_name)
        self.keeper = db.create(self.connect, stock)
        self.inventory = Inventory(runtime, telemetry, self.connect)
        self.orders = Orders(runtime, telemetry, self.inventory)
        self.web = Web(runtime, telemetry, self.orders, self.inventory)
