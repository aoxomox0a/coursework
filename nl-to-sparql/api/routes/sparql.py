"""
API routes for SPARQL Generation & Execution — Topic 3.
"""

import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from httpcore import request
from pydantic import BaseModel, Field
from config.settings import SPARQL_ENDPOINT
from src.sparql.pipeline import run_sparql_pipeline
from src.linking.pipeline import run_linking_pipeline
from api.routes.indexing import managed_indexing_task
from src.indexing.chroma_storage import is_endpoint_indexed_count
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
    # tell fastapi to expect an endpoint inside request, otherwise default to SPARQL_ENDPOINT
    endpoint: str = Field(default=SPARQL_ENDPOINT, description="Target endpoint")


class AnswerResponse(BaseModel):
    status: str
    question: str
    answer: str
    sparql_query: Optional[str] = None
    error: str | None = None


class ExplainRequest(BaseModel):
    sparql_query: str = Field(..., min_length=1, description="SPARQL query to convert to natural language")


class ExplainResponse(BaseModel):
    status: str
    sparql_query: str
    question: str
    error: str | None = None


class GenerateSparqlRequest(BaseModel):
    question: str = Field(
        ..., min_length=1, max_length=1000, description="Natural language question"
    )
    # tell fastapi to expect an endpoint inside request, otherwise default to SPARQL_ENDPOINT
    endpoint: str = Field(default=SPARQL_ENDPOINT, description="Target endpoint")


class GenerateSparqlResponse(BaseModel):
    status: str
    question: str
    sparql_query: str
    error: str | None = None


@router.post("/generate-sparql")
async def generate_sparql(
    request: GenerateSparqlRequest, background_tasks: BackgroundTasks
):
    """
    Generate SPARQL query from natural language (without executing).

    If the SPARQL endpoint has not yet been indexed, indexing is triggered
    automatically in the background and a 202 response is returned.

    Args:
        request: GenerateSparqlRequest with 'question' field

    Returns:
        GenerateSparqlResponse with status, question, and SPARQL query
    """
    if is_endpoint_indexed_count(request.endpoint) == 0:
        if is_indexing_in_progress():
            return JSONResponse(
                status_code=202,
                content={
                    "status": "indexing",
                    "message": f"Indexing for {request.endpoint} is already in progress.",
                },
            )
        else:
            # Trigger the background task and return 202
            background_tasks.add_task(managed_indexing_task, request.endpoint)
            return JSONResponse(
                status_code=202,
                content={
                    "status": "indexing",
                    "message": f"Schema indexing started for {request.endpoint}.",
                },
            )

    try:
        linking_result = await asyncio.to_thread(
            run_linking_pipeline, [request.question], request.endpoint
        )
        single_linking_result = linking_result[0]
        result = await run_sparql_pipeline(
            request.question, single_linking_result, endpoint=request.endpoint
        )
    except Exception as exc:
        logger.error(
            "SPARQL generation error for question '%s': %s", request.question, exc
        )
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    if result["status"] == "error":
        return GenerateSparqlResponse(
            status="error",
            question=request.question,
            sparql_query=result.get("sparql_query", ""),
            error=result.get("error_message"),
        )

    return GenerateSparqlResponse(
        status="success",
        question=request.question,
        sparql_query=result.get("sparql_query", ""),
        error=None,
    )


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
    if is_endpoint_indexed_count(request.endpoint) == 0:
        if is_indexing_in_progress():
            return JSONResponse(
                status_code=202,
                content={
                    "status": "indexing",
                    "message": f"Indexing for {request.endpoint} is already in progress.",
                },
            )
        else:
            # Trigger the background task and return 202
            background_tasks.add_task(managed_indexing_task, request.endpoint)
            return JSONResponse(
                status_code=202,
                content={
                    "status": "indexing",
                    "message": f"Schema indexing started for {request.endpoint}.",
                },
            )

    try:
        linking_result = await asyncio.to_thread(
            run_linking_pipeline, [request.question], request.endpoint
        )
        single_linking_dict = linking_result[0]
        result = await run_sparql_pipeline(
            request.question, single_linking_dict, endpoint=request.endpoint
        )
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


@router.post("/generate-nl")
async def generate_nl_from_sparql(request: ExplainRequest):
    """
    Generate natural language question from a SPARQL query.

    Args:
        request: ExplainRequest with 'sparql_query' field

    Returns:
        ExplainResponse with status, sparql_query, and generated question
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
        logger.error(
            "Question generation error for query '%s': %s", request.sparql_query, exc
        )
        return ExplainResponse(
            status="error",
            sparql_query=request.sparql_query,
            question="",
            error=str(exc),
        )
