"""
Filtered Database Log Handler

Goal:
- Keep the existing `core.logger.db_log_handler.DatabaseLogHandler` behavior
  but EXCLUDE noisy/infra logs (especially `backend/common/universal_optimization.py`)
  from being persisted into AuditLogs via Celery `task_add_log`.

Why:
- `UniversalOptimizer` cache invalidation logs can be very chatty.
- Persisting them creates unnecessary DB load and can amplify log/task storms.
"""

from __future__ import annotations

import os
from typing import Iterable, Optional

from core.logger.db_log_handler import DatabaseLogHandler


class FilteredDatabaseLogHandler(DatabaseLogHandler):
    """
    Wrapper around `DatabaseLogHandler` that skips unwanted log records.

    High-signal rule:
    - Skip anything originating from `backend/common/universal_optimization.py`.
    """

    # Fast checks (string prefix) for logger names that should never be persisted.
    # These are typically infrastructure logs or extremely chatty.
    _DENY_LOGGER_PREFIXES: tuple[str, ...] = (
        "cache_invalidation",
        "redis_pool",
        "celery.redirected",
    )

    # Exact logger names to skip (keep minimal and explicit).
    _DENY_LOGGER_NAMES: set[str] = set()

    # Substring match on the record pathname (normalized with "/" separators).
    _DENY_PATH_SUBSTRINGS: tuple[str, ...] = (
        "/backend/common/universal_optimization.py",
        "/common/universal_optimization.py",
        "universal_optimization.py",
    )

    def _should_skip_record(self, record) -> bool:
        # 1) Skip by logger name
        name = getattr(record, "name", "") or ""
        if name in self._DENY_LOGGER_NAMES:
            return True
        for prefix in self._DENY_LOGGER_PREFIXES:
            if name.startswith(prefix):
                return True

        # 2) Skip by source file path (pathname)
        pathname = getattr(record, "pathname", None)
        if not pathname:
            return False

        # Normalize to forward slashes for stable matching across environments.
        path_norm = pathname.replace("\\", "/")
        for needle in self._DENY_PATH_SUBSTRINGS:
            if needle in path_norm:
                return True
        return False

    def emit(self, record):
        # During Django startup (apps not ready yet), persisting logs into DB can
        # deadlock due to re-entrant logging paths inside config/encryption utilities.
        # Example deadlock we observed:
        # - A startup log triggers this handler
        # - `DatabaseLogHandler.emit()` serializes/encrypts → reads config in a worker thread
        # - That worker thread logs, but the main thread is still holding the logging lock
        # To keep startup robust, skip DB persistence until apps are fully ready.
        try:
            from django.apps import apps as django_apps  # local import: safe during early init

            if not getattr(django_apps, "ready", False):
                return
        except Exception:
            # If Django isn't ready/importable yet, never block startup on DB logging.
            return

        # Critical: avoid any work if we know we will skip.
        if self._should_skip_record(record):
            return
        return super().emit(record)



