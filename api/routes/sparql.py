"""
API routes for SPARQL Generation & Execution — Topic 3.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.sparql.pipeline import run_sparql_pipeline
from src.linking.pipeline import run_linking_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


class AnswerRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="Natural language question")


class AnswerResponse(BaseModel):
    status: str
    question: str
    answer: str
    error: str | None = None


@router.post("/answer", response_model=AnswerResponse)
def get_answer(request: AnswerRequest) -> AnswerResponse:
    """
    End-to-end NL-to-SPARQL: link entities, generate SPARQL, execute, return answer.

    Args:
        request: AnswerRequest with 'question' field (non-empty string)

    Returns:
        AnswerResponse with status, question, answer, and optional error
    """
    try:
        linking_result = run_linking_pipeline(request.question)
        result = run_sparql_pipeline(request.question, linking_result)
    except Exception as exc:
        logger.error("Pipeline error for question '%s': %s", request.question, exc)
        raise HTTPException(status_code=500, detail=str(exc))

    if result["status"] == "error":
        return AnswerResponse(
            status="error",
            question=request.question,
            answer="",
            error=result.get("error_message"),
        )

    return AnswerResponse(
        status="success",
        question=request.question,
        answer=result["answer"],
    )
