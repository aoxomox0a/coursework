"""FastAPI application for NL-to-SPARQL system."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from api.routes import indexing, sparql, linking
from contextlib import asynccontextmanager
import asyncio
import logging

from src.sparql.llm import http_client
from src.sparql.execution import sparql_client
from config.settings import SPARQL_ENDPOINT
from src.indexing.chroma_storage import is_endpoint_indexed
from api.routes.indexing import managed_indexing_task

logger = logging.getLogger(__name__)


# safely close the global HTTP connection pool on server shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    logger.info("Wakiing up the API...")
    # Disabled: Auto-index on startup. User can trigger from UI instead.
    # if not is_endpoint_indexed(SPARQL_ENDPOINT):
    #     logger.warning(
    #         f"Index missing for {SPARQL_ENDPOINT}. Bob the Builder is on it..."
    #     )
    #     asyncio.create_task(managed_indexing_task(SPARQL_ENDPOINT))
    # else:
    logger.info("System ready - indexing can be triggered from UI")

    yield
    # --- SHUTDOWN ---
    print("Closing LLM connection pool...")
    await http_client.aclose()
    await sparql_client.aclose()


app = FastAPI(
    title="NL-to-SPARQL API",
    description="Convert natural language questions to SPARQL queries",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(indexing.router, prefix="/api")
app.include_router(sparql.router, prefix="/api")
app.include_router(linking.router, prefix="/api")


class IndexRequest(BaseModel):
    endpoint: str = None
    resume: bool = False


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "NL-to-SPARQL API v0.1.0"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    from config.settings import API_HOST, API_PORT

    uvicorn.run(app, host=API_HOST, port=API_PORT)
