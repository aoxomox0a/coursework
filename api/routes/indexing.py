"""
API routes for Graph Indexing
"""
from fastapi import APIRouter
from pydantic import BaseModel
from src.indexing import entities, chroma_storage
from src.indexing.indexing_state import (
    get_status,
    is_indexing_in_progress,
    trigger_background_indexing,
)

router = APIRouter()


class IndexRequest(BaseModel):
    """Request model for indexing."""
    endpoint: str = None


class ProgressRequest(BaseModel):
    """Request model for progress info."""
    endpoint: str


@router.post("/index")
def trigger_indexing(request: IndexRequest):
    """
    Trigger the full indexing pipeline.
    Skips silently if the endpoint has already been indexed.
    Connects to endpoint, fetches properties/classes/entities, embeds, and stores in ChromaDB.

    Args:
        request: IndexRequest with optional 'endpoint' field

    Returns:
        Status confirmation
    """
    if chroma_storage.is_endpoint_indexed(request.endpoint):
        return {"status": "already_indexed", "message": "Endpoint already indexed — skipping"}

    if is_indexing_in_progress():
        return {"status": "processing", "message": "Indexing already in progress"}

    trigger_background_indexing(request.endpoint)
    return {"status": "processing", "message": "Indexing started in background"}


@router.get("/status")
def get_indexing_status():
    """
    Get current indexing status for real-time UI updates.

    Returns:
        Current status information
    """
    return get_status()


@router.post("/counts")
def get_collection_counts(request: ProgressRequest):
    """
    Get current counts from all ChromaDB collections for a specific endpoint.
    
    Args:
        request: ProgressRequest with 'endpoint' field
    
    Returns:
        Current indexed counts
    """
    try:
        chroma_counts = chroma_storage.get_all_collection_counts(endpoint=request.endpoint)
        return {
            "status": "success",
            "counts": {
                "entities": chroma_counts.get("entities", 0),
                "properties": chroma_counts.get("properties", 0),
                "classes": chroma_counts.get("classes", 0),
                "sample_triples": chroma_counts.get("sample_triples", 0),
                "class_entity_mappings": chroma_counts.get("class_entity_mappings", 0)
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "counts": {
                "entities": 0,
                "properties": 0,
                "classes": 0,
                "sample_triples": 0,
                "class_entity_mappings": 0
            }
        }


@router.post("/progress")
def get_progress(request: ProgressRequest):
    """
    Get indexing progress: total entities and currently indexed count.
    
    Args:
        request: ProgressRequest with 'endpoint' field
        
    Returns:
        Total entities, indexed count, and progress percentage
    """
    try:
        # Get total count from SPARQL endpoint
        total_count = entities.get_total_entity_count(request.endpoint)
        print("/progress f{total_count} entities found at endpoint {request.endpoint}")
        
        # Get current count from ChromaDB
        try:
            indexed_count = chroma_storage.get_indexed_count()
        except:
            indexed_count = 0
        
        progress = 0
        if total_count > 0:
            progress = int((indexed_count / total_count) * 100)
        
        return {
            "status": "success",
            "total": total_count,
            "indexed": indexed_count,
            "progress": progress
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "total": 0,
            "indexed": 0,
            "progress": 0
        }
