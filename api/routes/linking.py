"""
API routes for Entity & Relation Linking
"""
from fastapi import APIRouter
from pydantic import BaseModel
from src.linking.pipeline import run_linking_pipeline

router = APIRouter()


class QuestionRequest(BaseModel):
    """Request model for linking."""
    question: str


@router.post("/link")
def link_entities_and_relations(request: QuestionRequest):
    """
    Extract entities and relations from a question, then link them to the knowledge graph.

    Args:
        request: QuestionRequest with 'question' field

    Returns:
        Linked entities and relations
    """
    result = run_linking_pipeline(request.question)

    return {
        "status": "success",
        "question": result["question"],
        "entities": result["entities"],
        "relation": result["relation"],
        "relation_candidates": result["relation_candidates"]
    }
