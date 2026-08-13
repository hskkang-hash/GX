"""
Thread request/user context propagation utilities.

Why:
- Many parts of the system rely on `core.middleware.refresh_token.get_current_request()`
  (thread-local) to determine current user for:
  - BaseModel.save() auto-populating created_by/modified_by/group
  - CustomManagerGroup permission filtering
When we spawn background threads from a request (e.g. `threading.Thread` in views),
the new thread does NOT automatically have the request in thread-local storage.

This module installs a small monkey-patch so that any new `threading.Thread`
created inside a request context automatically gets a lightweight request object
with the same `user` set in the child thread for the duration of that thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import threading


@dataclass
class _ThreadRequest:
    """
    Minimal request-like object to satisfy code paths that only need `request.user`.
    """
    user: Any
    GET: dict = None
    META: dict = None
    method: str = "THREAD"

    def __post_init__(self):
        if self.GET is None:
            self.GET = {}
        if self.META is None:
            self.META = {"REMOTE_ADDR": "127.0.0.1"}


def install_thread_request_propagation() -> None:
    """
    Install global patch to propagate request.user context into new threads.

    Behavior:
    - When a Thread is instantiated, capture current request's user (if any).
    - When the Thread runs, if the child thread has no existing thread_local.request,
      set a lightweight request with captured user for the duration of the thread.
    - Always restore previous thread_local.request after thread finishes.

    Safety:
    - Idempotent: can be called multiple times.
    - Does NOT overwrite an explicitly seeded thread_local.request in the child thread.
    """
    if getattr(threading, "_gx_request_propagation_installed", False):
        return

    # Import inside to avoid import-time side-effects during app loading.
    from core.middleware.refresh_token import get_current_request, thread_local

    _orig_init = threading.Thread.__init__
    _orig_run = threading.Thread.run

    def _patched_init(self, *args, **kwargs):  # type: ignore[no-redef]
        parent_request = None
        parent_user = None
        try:
            parent_request = get_current_request()
            parent_user = getattr(parent_request, "user", None) if parent_request else None
        except Exception:
            parent_user = None

        # Store only the user to avoid sharing real request object across threads.
        setattr(self, "_gx_parent_user", parent_user)
        return _orig_init(self, *args, **kwargs)

    def _patched_run(self, *args, **kwargs):  # type: ignore[no-redef]
        previous_request: Optional[Any] = getattr(thread_local, "request", None)
        seeded = False
        try:
            # Respect explicit context seeding: only set if missing.
            if previous_request is None:
                parent_user = getattr(self, "_gx_parent_user", None)
                if parent_user is not None:
                    thread_local.request = _ThreadRequest(parent_user)
                    seeded = True
            return _orig_run(self, *args, **kwargs)
        finally:
            # Restore/cleanup
            try:
                if seeded:
                    if previous_request is None:
                        if hasattr(thread_local, "request"):
                            delattr(thread_local, "request")
                    else:
                        thread_local.request = previous_request
            except Exception:
                pass

    threading.Thread.__init__ = _patched_init  # type: ignore[assignment]
    threading.Thread.run = _patched_run  # type: ignore[assignment]
    setattr(threading, "_gx_request_propagation_installed", True)


