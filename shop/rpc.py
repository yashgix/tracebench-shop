"""Calls between services: a client span, network time, and failures carried back as HTTP statuses."""

from .runtime import Future

NETWORK_MS = 1


class ServiceError(Exception):
    """A request failed with an HTTP status."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


async def call(runtime, telemetry, caller, target, name, handler, *args, timeout_ms=None):
    with telemetry.span(caller, f"{target} {name}", kind="client", **{"peer.service": target}):
        await runtime.sleep(NETWORK_MS)
        try:
            work = handler(*args)
            result = await (work if timeout_ms is None else _within(runtime, work, timeout_ms))
        except Exception as exc:  # only the status and message cross the network
            raise ServiceError(getattr(exc, "status", 500), str(exc)) from None
        finally:
            await runtime.sleep(NETWORK_MS)
        return result


def _within(runtime, work, timeout_ms):
    """Await *work* for at most *timeout_ms*; after that the caller gets a 504 and the work runs on unobserved."""
    answer = Future()

    async def run():
        try:
            answer.resolve(await work)
        except Exception as exc:
            answer.fail(exc)

    runtime.spawn(run())
    runtime.call_at(runtime.now + timeout_ms, lambda: answer.fail(ServiceError(504, f"no answer in {timeout_ms} ms")))
    return answer
