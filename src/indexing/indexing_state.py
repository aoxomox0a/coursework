"""
Shared indexing state and background indexing trigger.

Centralises mutable state so both the indexing route and the SPARQL route
can check / update indexing progress without importing from each other.
"""

import threading
import logging
import asyncio

logger = logging.getLogger(__name__)

_status: dict = {
    "is_indexing": False,
    "current_step": "",
    "endpoint": "",
    "error": None,
}
_lock = threading.Lock()


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


def trigger_background_indexing(endpoint: str) -> None:
    """
    Start the full indexing pipeline in a background thread.
    No-op if indexing is already running.
    """
    from src.indexing.pipeline import (
        run_indexing_pipeline,
    )  # lazy — avoids circular import

    with _lock:
        if _status["is_indexing"]:
            return
        _status["is_indexing"] = True
        _status["error"] = None
        _status["endpoint"] = endpoint or ""

    def _run() -> None:
        try:
            asyncio.run(
                run_indexing_pipeline(
                    custom_endpoint=endpoint, status_callback=update_status
                )
            )
            update_status("✓ Indexing completed successfully!", endpoint)
        except Exception as exc:
            update_status("✗ Indexing failed", endpoint, str(exc))
            logger.error("Background indexing failed for %s: %s", endpoint, exc)
        finally:
            with _lock:
                _status["is_indexing"] = False

    threading.Thread(target=_run, daemon=True).start()
