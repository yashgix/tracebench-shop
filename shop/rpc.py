"""Calls between services: a client span, network time, and failures carried back as HTTP statuses."""

NETWORK_MS = 1


class ServiceError(Exception):
    """A request failed with an HTTP status."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


async def call(runtime, telemetry, caller, target, name, handler, *args):
    with telemetry.span(caller, f"{target} {name}", kind="client", **{"peer.service": target}):
        await runtime.sleep(NETWORK_MS)
        try:
            result = await handler(*args)
        except Exception as exc:  # only the status and message cross the network
            raise ServiceError(getattr(exc, "status", 500), str(exc)) from None
        finally:
            await runtime.sleep(NETWORK_MS)
        return result
