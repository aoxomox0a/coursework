"""
API routes for SPARQL Generation & Execution — Topic 3.
"""

import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from config.settings import SPARQL_ENDPOINT
from src.sparql.pipeline import run_sparql_pipeline
from src.linking.pipeline import run_linking_pipeline
from src.indexing.chroma_storage import is_endpoint_indexed
from src.indexing.indexing_state import (
    is_indexing_in_progress,
    trigger_background_indexing,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class AnswerRequest(BaseModel):
    question: str = Field(
        ..., min_length=1, max_length=1000, description="Natural language question"
    )


class AnswerResponse(BaseModel):
    status: str
    question: str
    answer: str
    error: str | None = None


@router.post("/answer")
async def get_answer(request: AnswerRequest):
    """
    End-to-end NL-to-SPARQL: link entities, generate SPARQL, execute, return answer.

    If the SPARQL endpoint has not yet been indexed, indexing is triggered
    automatically in the background and a 202 response is returned — the
    client should retry after a few minutes.

    Args:
        request: AnswerRequest with 'question' field (non-empty string)

    Returns:
        AnswerResponse with status, question, answer, and optional error
    """
    if not is_endpoint_indexed(SPARQL_ENDPOINT):
        if is_indexing_in_progress():
            return JSONResponse(
                status_code=202,
                content={
                    "status": "indexing",
                    "message": "Endpoint indexing is in progress. Please retry in a few minutes.",
                },
            )
        logger.info(
            "Endpoint %s not indexed — triggering auto-indexing", SPARQL_ENDPOINT
        )
        trigger_background_indexing(SPARQL_ENDPOINT)
        return JSONResponse(
            status_code=202,
            content={
                "status": "indexing",
                "message": (
                    "Endpoint not indexed yet. Indexing started automatically. "
                    "Please retry in a few minutes."
                ),
            },
        )

    try:
        linking_result = run_linking_pipeline(request.question)
        result = await run_sparql_pipeline(request.question, linking_result)
    except Exception as exc:
        logger.error("Pipeline error for question '%s': %s", request.question, exc)
        return JSONResponse(status_code=500, content={"detail": str(exc)})

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
        error=None,
    )
