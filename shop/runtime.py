"""A small single-threaded async runtime with a simulated millisecond clock, so a run is exactly repeatable."""

import contextvars
import heapq
import itertools


class Future:
    def __init__(self):
        self.done = False
        self._value = self._error = None
        self._waiter = None

    def resolve(self, value=None):
        self._finish(value, None)

    def fail(self, error):
        self._finish(None, error)

    def _finish(self, value, error):
        if self.done:
            return
        self.done, self._value, self._error = True, value, error
        if self._waiter:
            self._waiter()

    def __await__(self):
        if not self.done:
            yield self
        if self._error is not None:
            raise self._error
        return self._value


class _Sleep:
    def __init__(self, ms):
        self.ms = ms

    def __await__(self):
        yield self


class Runtime:
    def __init__(self):
        self.now = 0
        self._queue = []
        self._order = itertools.count()

    def sleep(self, ms):
        return _Sleep(ms)

    def call_at(self, t, callback):
        heapq.heappush(self._queue, (t, next(self._order), callback))

    def spawn(self, coro, at=None):
        """Start *coro* at time *at* (default now) in its own context."""
        context = contextvars.copy_context()
        self.call_at(self.now if at is None else at, lambda: self._step(coro, context))

    def _step(self, coro, context):
        try:
            awaited = context.run(coro.send, None)
        except StopIteration:
            return
        if isinstance(awaited, _Sleep):
            self.call_at(self.now + awaited.ms, lambda: self._step(coro, context))
        else:
            awaited._waiter = lambda: self.call_at(self.now, lambda: self._step(coro, context))

    def run(self, until):
        while self._queue and self._queue[0][0] <= until:
            self.now, _, callback = heapq.heappop(self._queue)
            callback()
        self.now = until
