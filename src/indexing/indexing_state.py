"""
Shared indexing state and background indexing trigger.

Centralises mutable state so both the indexing route and the SPARQL route
can check / update indexing progress without importing from each other.
"""

import threading
import logging

logger = logging.getLogger(__name__)

_status: dict = {
    "is_indexing": False,
    "current_step": "",
    "endpoint": "",
    "error": None,
}
_lock = threading.Lock()


def toggle_indexing_state(is_active: bool):
    """Safely toggle the indexing status lock for the UI."""
    with _lock:
        _status["is_indexing"] = is_active


def update_status(step: str, endpoint: str = None, error: str = None) -> None:
    with _lock:
        _status["current_step"] = step
        if endpoint is not None:
            _status["endpoint"] = endpoint
        if error is not None:
            _status["error"] = error


def get_status() -> dict:
    with _lock:
        return dict(_status)


def is_indexing_in_progress() -> bool:
    with _lock:
        return _status["is_indexing"]
