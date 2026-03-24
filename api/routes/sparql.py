"""
API routes for SPARQL Generation & Execution
"""
from fastapi import APIRouter
from pydantic import BaseModel
from src.sparql.pipeline import run_sparql_pipeline
from src.linking.pipeline import run_linking_pipeline

router = APIRouter()


class AnswerRequest(BaseModel):
    """Request model for getting answer."""
    question: str


@router.post("/answer")
def get_answer(request: AnswerRequest):
    """
    End-to-end: Link entities, generate SPARQL, execute, and return answer.

    Args:
        request: AnswerRequest with 'question' field

    Returns:
        Final answer string
    """
    # Step 1: Run linking pipeline
    linking_result = run_linking_pipeline(request.question)

    # Step 2: Run SPARQL generation and execution
    answer = run_sparql_pipeline(request.question, linking_result)

    return {
        "status": "success",
        "question": request.question,
        "answer": answer
    }
