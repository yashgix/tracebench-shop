"""A bounded connection pool: at most `size` connections; a caller waits up to `timeout_ms` for a free one."""

from collections import deque

from .runtime import Future


class PoolTimeout(Exception):
    pass


class Pool:
    def __init__(self, runtime, connect, size, timeout_ms):
        self.runtime, self._connect = runtime, connect
        self.size, self.timeout_ms = size, timeout_ms
        self._idle, self._waiters = deque(), deque()
        self.opened = self.in_use = 0

    def acquire(self):
        future = Future()
        if self._idle or self.opened < self.size:
            self._hand_out(future)
        else:
            self._waiters.append(future)
            self.runtime.call_at(self.runtime.now + self.timeout_ms, lambda: self._expire(future))
        return future

    def release(self, connection):
        self.in_use -= 1
        self._idle.append(connection)
        while self._waiters:
            waiter = self._waiters.popleft()
            if not waiter.done:
                self._hand_out(waiter)
                return

    def _hand_out(self, future):
        if not self._idle:
            self._idle.append(self._connect())
            self.opened += 1
        self.in_use += 1
        future.resolve(self._idle.popleft())

    def _expire(self, future):
        if not future.done:
            future.fail(PoolTimeout(f"no connection free within {self.timeout_ms} ms ({self.in_use}/{self.size} in use)"))

    @property
    def waiting(self):
        return sum(1 for waiter in self._waiters if not waiter.done)
