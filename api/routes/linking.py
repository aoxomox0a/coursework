"""
API routes for Entity & Relation Linking
"""

from fastapi import APIRouter
from pydantic import BaseModel
from src.linking.pipeline import run_linking_pipeline

router = APIRouter()


class QuestionRequest(BaseModel):
    """Request model for linking."""

    # keep this
    question: str
    endpoint: str


@router.post("/link")
def link_entities_and_relations(request: QuestionRequest):
    """
    Extract entities and relations from a question, then link them to the knowledge graph.

    Args:
        request: QuestionRequest with 'question' field

    Returns:
        Linked entities and relations
    """
    question = request.question
    # create list
    batch_input = [question]
    full_result = run_linking_pipeline(batch_input, request.endpoint)

    result = full_result[0]

    return {
        "status": "success",
        "question": result["question"],
        "entities": result["entities"],
        "relation": result["relation"],
        "relation_candidates": result["relation_candidates"],
    }
