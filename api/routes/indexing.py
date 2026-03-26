"""
API routes for Graph Indexing
"""
from fastapi import APIRouter
from pydantic import BaseModel
import threading
from src.indexing.pipeline import run_indexing_pipeline
from src.indexing import entities, chroma_storage

router = APIRouter()

# Global status tracking for real-time updates
indexing_status = {
    'is_indexing': False,
    'current_step': '',
    'endpoint': '',
    'error': None
}
status_lock = threading.Lock()


def update_status(step: str, endpoint: str = None, error: str = None):
    """Update global indexing status."""
    with status_lock:
        indexing_status['current_step'] = step
        if endpoint:
            indexing_status['endpoint'] = endpoint
        if error:
            indexing_status['error'] = error


class IndexRequest(BaseModel):
    """Request model for indexing."""
    endpoint: str = None


class ProgressRequest(BaseModel):
    """Request model for progress info."""
    endpoint: str


def run_indexing_background(endpoint: str):
    """Run indexing pipeline in background with status updates."""
    try:
        with status_lock:
            indexing_status['is_indexing'] = True
            indexing_status['error'] = None
        
        result = run_indexing_pipeline(
            custom_endpoint=endpoint,
            status_callback=update_status
        )
        
        if result and isinstance(result, dict):
            update_status('✓ Indexing completed successfully!', endpoint)
        else:
            update_status('✗ Indexing pipeline failed', endpoint, 'Unknown error')
    except Exception as e:
        update_status('✗ Indexing failed', endpoint, str(e))
    finally:
        with status_lock:
            indexing_status['is_indexing'] = False


@router.post("/index")
def trigger_indexing(request: IndexRequest):
    """
    Trigger the full indexing pipeline.
    Connects to endpoint, fetches properties/classes/entities, embeds, and stores in ChromaDB.

    Args:
        request: IndexRequest with optional 'endpoint' field

    Returns:
        Status confirmation and initial counts
    """
    # Start indexing in background thread
    thread = threading.Thread(
        target=run_indexing_background,
        args=(request.endpoint,),
        daemon=True
    )
    thread.start()
    
    return {
        "status": "processing",
        "message": "Indexing started in background"
    }


@router.get("/status")
def get_indexing_status():
    """
    Get current indexing status for real-time UI updates.
    
    Returns:
        Current status information
    """
    with status_lock:
        return {
            "is_indexing": indexing_status['is_indexing'],
            "current_step": indexing_status['current_step'],
            "endpoint": indexing_status['endpoint'],
            "error": indexing_status['error']
        }


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
