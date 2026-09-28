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

# SSE event queues for streaming status updates (per endpoint)
_sse_queues: dict[str, list] = {}
_sse_lock = threading.Lock()


def toggle_indexing_state(is_active: bool):
    """Safely toggle the indexing status lock for the UI."""
    with _lock:
        _status["is_indexing"] = is_active
    
    # Broadcast the state change to SSE clients
    endpoint = _status.get("endpoint")
    if endpoint:
        broadcast_status_update(endpoint)


def update_status(step: str, endpoint: str = "", error: str = "") -> None:
    with _lock:
        _status["current_step"] = step
        if endpoint is not None:
            _status["endpoint"] = endpoint
        if error is not None:
            _status["error"] = error
    
    # Broadcast update to SSE clients if endpoint is set
    if endpoint:
        broadcast_status_update(endpoint)


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


def register_sse_client(endpoint: str, q: asyncio.Queue) -> None:
    """Register a new SSE client queue for an endpoint."""
    with _sse_lock:
        if endpoint not in _sse_queues:
            _sse_queues[endpoint] = []
        _sse_queues[endpoint].append(q)


def unregister_sse_client(endpoint: str, q: asyncio.Queue) -> None:
    """Unregister an SSE client for an endpoint."""
    with _sse_lock:
        if endpoint in _sse_queues and q in _sse_queues[endpoint]:
            _sse_queues[endpoint].remove(q)


def broadcast_status_update(endpoint: str) -> None:
    """Broadcast current status to all SSE clients for an endpoint."""
    status = get_status()
    with _sse_lock:
        if endpoint in _sse_queues:
            for q in _sse_queues[endpoint]:
                try:
                    # Use put_nowait for asyncio.Queue
                    q.put_nowait(status)
                except asyncio.QueueFull:
                    pass
