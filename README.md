# shop

Three small services behind one checkout: `web` calls `orders`, `orders` and `web` call `inventory`, and `inventory`
keeps stock in SQLite behind a bounded connection pool (`shop/pool.py`). Services talk through `shop/rpc.py`: a client
span, a little network time, and failures carried back as HTTP statuses.

Everything runs on `shop/runtime.py`, a single-threaded async runtime with a simulated millisecond clock, so a run with
the same traffic is exactly repeatable. Telemetry (`shop/telemetry.py`) records spans, logs and gauges in
OpenTelemetry's data shapes.

Python 3.12 or newer, standard library only.

```
python3 -m unittest discover -s tests
```
