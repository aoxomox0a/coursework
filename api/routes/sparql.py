"""
API routes for SPARQL Generation & Execution — Topic 3.
"""

import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from config.settings import SPARQL_ENDPOINT
from src.sparql.pipeline import run_sparql_pipeline
from src.linking.pipeline import run_linking_pipeline
from api.routes.indexing import managed_indexing_task
from src.indexing.chroma_storage import is_endpoint_indexed
from src.indexing.indexing_state import (
    is_indexing_in_progress,
)
from src.sparql.llm import call_llm
from src.sparql.prompt import generate_sparql_explanation_prompt
import asyncio

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
    sparql_query: Optional[str] = None
    error: str | None = None


class ExplainRequest(BaseModel):
    sparql_query: str = Field(
        ..., min_length=1, description="SPARQL query to explain"
    )


class ExplainResponse(BaseModel):
    status: str
    sparql_query: str
    question: str
    error: str | None = None


@router.post("/answer")
async def get_answer(request: AnswerRequest, background_tasks: BackgroundTasks):
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
        status_msg = (
            "Endpoint indexing is currently in progress."
            if is_indexing_in_progress()
            else "Endpoint index is missing or failed to initialize on startup."
        )
        logger.warning(
            f"Query rejected: Index unavailable for {SPARQL_ENDPOINT}. State: {status_msg}"
        )
        return JSONResponse(
            status_code=202 if is_indexing_in_progress else 503,
            content={
                "status": "indexing" if is_indexing_in_progress() else "error",
                "message": f"{status_msg} Please try again later.",
            },
        )

    try:
        linking_result = await asyncio.to_thread(run_linking_pipeline, request.question)
        single_linking_result = linking_result[0]
        result = await run_sparql_pipeline(request.question, single_linking_result)
    except Exception as exc:
        logger.error("Pipeline error for question '%s': %s", request.question, exc)
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    if result["status"] == "error":
        return AnswerResponse(
            status="error",
            question=request.question,
            answer="",
            sparql_query=result.get("sparql_query"),
            error=result.get("error_message"),
        )

    return AnswerResponse(
        status="success",
        question=request.question,
        answer=result["answer"],
        sparql_query=result.get("sparql_query"),
        error=None,
    )


@router.post("/explain")
async def explain_sparql(request: ExplainRequest):
    """
    Recover the original natural language question from a SPARQL query.

    Args:
        request: ExplainRequest with 'sparql_query' field

    Returns:
        ExplainResponse with status, sparql_query, and original question
    """
    try:
        prompt = generate_sparql_explanation_prompt(request.sparql_query)
        question = await call_llm(prompt)

        if not question:
            return ExplainResponse(
                status="error",
                sparql_query=request.sparql_query,
                question="",
                error="LLM failed to generate question",
            )

        return ExplainResponse(
            status="success",
            sparql_query=request.sparql_query,
            question=question.strip(),
            error=None,
        )

    except Exception as exc:
        logger.error("Question generation error for query '%s': %s", request.sparql_query, exc)
        return ExplainResponse(
            status="error",
            sparql_query=request.sparql_query,
            question="",
            error=str(exc),
        )
