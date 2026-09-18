"""A shared request deadline for lock waits and provider calls."""

from contextlib import contextmanager
from contextvars import ContextVar
import math
import os
import platform
import queue
import threading
import time

_deadline = ContextVar("request_deadline", default=None)
_platform_lock = threading.Lock()


def configure_windows_runtime():
    """Bound Python's optional WMI probe before Torch/SDK platform detection.

    Python 3.12 uses WMI for platform details and already falls back to native
    Windows APIs on OSError. A broken WMI service must not freeze inference.
    The private hook is guarded for Python versions without this implementation.
    """
    if os.name != "nt":
        return
    with _platform_lock:
        probe = getattr(platform, "_wmi_query", None)
        if probe is None or getattr(probe, "_bounded_lecture_probe", False):
            return
        unavailable = threading.Event()
        probe_lock = threading.Lock()

        def bounded_probe(*arguments):
            with probe_lock:
                if unavailable.is_set():
                    raise OSError("WMI platform probe unavailable")
                replies = queue.Queue(maxsize=1)
                def run():
                    try:
                        replies.put((True, probe(*arguments)))
                    except Exception as error:
                        replies.put((False, error))
                threading.Thread(target=run, daemon=True).start()
                try:
                    success, value = replies.get(timeout=0.25)
                except queue.Empty as error:
                    unavailable.set()
                    raise OSError("WMI platform probe timed out") from error
                if not success:
                    raise value
                return value

        bounded_probe._bounded_lecture_probe = True
        platform._wmi_query = bounded_probe


def configured_timeout(name, default):
    try:
        value = float(os.getenv(name, str(default)))
        return value if math.isfinite(value) and value > 0 else default
    except (ValueError, TypeError):
        return default


def remaining_timeout(maximum):
    deadline = _deadline.get()
    remaining = maximum if deadline is None else min(maximum, deadline - time.monotonic())
    if remaining <= 0:
        raise TimeoutError("Request deadline exceeded")
    return remaining


@contextmanager
def request_deadline(seconds):
    end = time.monotonic() + seconds
    previous = _deadline.get()
    token = _deadline.set(min(end, previous) if previous is not None else end)
    try:
        yield
    finally:
        _deadline.reset(token)


@contextmanager
def bounded_lock(lock):
    deadline = _deadline.get()
    acquired = lock.acquire() if deadline is None else lock.acquire(timeout=remaining_timeout(3600))
    if not acquired:
        raise TimeoutError("Request queue wait exceeded deadline")
    try:
        yield
    finally:
        lock.release()
