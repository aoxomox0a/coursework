"""FastAPI application for NL-to-SPARQL system."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from api.routes import indexing, sparql

app = FastAPI(
    title="NL-to-SPARQL API",
    description="Convert natural language questions to SPARQL queries",
    version="0.1.0"
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
