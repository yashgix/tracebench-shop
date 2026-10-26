"""Spans, logs and gauges in OpenTelemetry's data shapes, kept in memory for the exporter."""

import contextvars
from contextlib import contextmanager

from .rpc import ServiceError

_current = contextvars.ContextVar("span", default=None)


class Telemetry:
    def __init__(self, runtime, rng):
        self.runtime, self._rng = runtime, rng
        self.spans, self.logs, self.gauges = [], [], []

    @contextmanager
    def span(self, service, name, kind="server", **attributes):
        parent = _current.get()
        span = {"trace_id": parent["trace_id"] if parent else f"{self._rng.getrandbits(128):032x}",
                "span_id": f"{self._rng.getrandbits(64):016x}", "parent_span_id": parent["span_id"] if parent else None,
                "service": service, "name": name, "kind": kind, "start_ms": self.runtime.now, "end_ms": None,
                "status": "OK", "attributes": attributes}
        token = _current.set(span)
        try:
            yield span
        except ServiceError as exc:
            span["attributes"]["http.status_code"] = exc.status
            if exc.status >= 500:
                span["status"] = "ERROR"
            raise
        except Exception as exc:
            span["status"], span["attributes"]["exception.type"] = "ERROR", type(exc).__name__
            raise
        finally:
            _current.reset(token)
            span["end_ms"] = self.runtime.now
            self.spans.append(span)

    def log(self, service, severity, body):
        span = _current.get()
        self.logs.append({"time_ms": self.runtime.now, "service": service, "severity": severity, "body": body,
                          "trace_id": span["trace_id"] if span else None, "span_id": span["span_id"] if span else None})

    def gauge(self, service, name, value):
        self.gauges.append({"time_ms": self.runtime.now, "service": service, "name": name, "value": value})
