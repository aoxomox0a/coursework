"""
API routes for Graph Indexing
"""
from fastapi import APIRouter
from pydantic import BaseModel
from src.indexing.pipeline import run_indexing_pipeline
from src.indexing import entities, chroma_storage

router = APIRouter()


class IndexRequest(BaseModel):
    """Request model for indexing."""
    endpoint: str = None
    resume: bool = False


class ProgressRequest(BaseModel):
    """Request model for progress info."""
    endpoint: str


@router.post("/index")
def trigger_indexing(request: IndexRequest):
    """
    Trigger the full indexing pipeline.
    Connects to endpoint, fetches properties/classes/entities, embeds, and stores in ChromaDB.

    Args:
        request: IndexRequest with optional 'endpoint' and 'resume' fields

    Returns:
        Status message
    """
    success = run_indexing_pipeline(
        custom_endpoint=request.endpoint,
        resume=request.resume
    )

    if success:
        return {
            "status": "success",
            "message": "Indexing pipeline completed successfully"
        }
    else:
        return {
            "status": "error",
            "message": "Indexing pipeline failed"
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
