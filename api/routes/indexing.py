"""
API routes for Graph Indexing
"""

import asyncio
import json
from fastapi import APIRouter, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from src.indexing import entities, chroma_storage
from src.indexing.pipeline import run_indexing_pipeline
from src.indexing.indexing_state import (
    get_status,
    is_indexing_in_progress,
    update_status,
    toggle_indexing_state,
    register_sse_client,
    unregister_sse_client,
    broadcast_status_update,
)

router = APIRouter()


class IndexRequest(BaseModel):
    """Request model for indexing."""

    endpoint: str = None
    max_entities: int = None


# create async wrapper to manage the UI state while the background task runs
async def managed_indexing_task(endpoint: str, max_entities: int = None):
    print(f"\n🚀 [managed_indexing_task] Starting for endpoint: {endpoint}")
    toggle_indexing_state(True)
    update_status("Starting indexing...", endpoint)
    try:
        # We must await the async pipeline now!
        print(f"📋 [managed_indexing_task] Running indexing pipeline...")
        await run_indexing_pipeline(
            custom_endpoint=endpoint, status_callback=update_status, max_entities=max_entities
        )
        print(f"✓ [managed_indexing_task] Indexing pipeline completed")
        update_status("✓ Indexing completed successfully!", endpoint)
    except Exception as exc:
        print(f"❌ [managed_indexing_task] Error: {exc}")
        update_status("✗ Indexing failed", endpoint, str(exc))
    finally:
        # Crucial: Ensure the UI knows we finished, even if it crashed
        print(f"🛑 [managed_indexing_task] Marking indexing as complete")
        toggle_indexing_state(False)


@router.post("/index")
def trigger_indexing(request: IndexRequest, background_tasks: BackgroundTasks):
    """
    Trigger the full indexing pipeline.
    If endpoint is already indexed, deletes old data and re-indexes.
    Connects to endpoint, fetches properties/classes/entities, embeds, and stores in ChromaDB.

    Args:
        request: IndexRequest with optional 'endpoint' field

    Returns:
        Status confirmation
    """
    print(f"\n🔍 [/api/index] Endpoint: {request.endpoint}")
    
    if chroma_storage.is_endpoint_indexed(request.endpoint):
        print(f"♻️  [/api/index] Endpoint already indexed - deleting old data and re-indexing...")
        chroma_storage.delete_endpoint_index(request.endpoint)

    if is_indexing_in_progress():
        print(f"⚠️  [/api/index] Indexing already in progress - skipping")
        return {"status": "processing", "message": "Indexing already in progress"}

    print(f"✓ [/api/index] Starting background indexing task...")
    background_tasks.add_task(managed_indexing_task, request.endpoint, request.max_entities)
    return {"status": "processing", "message": "Indexing started in background"}


@router.get("/status")
def get_indexing_status():
    """
    Get current indexing status for real-time UI updates.

    Returns:
        Current status information
    """
    return get_status()


@router.post("/check")
def check_indexed(request: IndexRequest):
    """
    Check if a specific endpoint is indexed.
    
    Args:
        request: IndexRequest with 'endpoint' field
    
    Returns:
        Status and indexing info
    """
    is_indexed = chroma_storage.is_endpoint_indexed(request.endpoint)
    return {
        "status": "success",
        "endpoint": request.endpoint,
        "is_indexed": is_indexed,
        "message": "Indexed" if is_indexed else "Not indexed"
    }


@router.get("/status/stream")
async def stream_indexing_status(endpoint: str):
    """
    Stream indexing status updates via Server-Sent Events (SSE).
    
    Args:
        endpoint: SPARQL endpoint URL to track (query parameter)
    
    Yields:
        JSON status updates when status changes
    """
    # Create queue in async context
    q = asyncio.Queue()
    register_sse_client(endpoint, q)
    
    async def event_generator():
        try:
            # Send initial status
            yield f"data: {json.dumps(get_status())}\n\n"
            
            last_is_indexing = True
            while True:
                try:
                    # Wait for status update with timeout
                    status_update = await asyncio.wait_for(q.get(), timeout=5.0)
                    yield f"data: {json.dumps(status_update)}\n\n"
                    
                    # If indexing just finished (transitioned from True to False), close connection
                    if last_is_indexing and not status_update.get("is_indexing"):
                        print(f"📡 [SSE] Indexing completed, closing stream for {endpoint}")
                        break
                    
                    last_is_indexing = status_update.get("is_indexing", False)
                except asyncio.TimeoutError:
                    # Timeout - keep connection alive but check if still needed
                    if not is_indexing_in_progress():
                        print(f"📡 [SSE] Timeout and no indexing in progress, closing stream")
                        break
                    continue
        finally:
            unregister_sse_client(endpoint, q)
            print(f"📡 [SSE] Stream closed for {endpoint}")
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
