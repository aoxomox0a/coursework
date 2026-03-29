"""
Configuration settings for NL-to-SPARQL system.
Read from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Endpoint Configuration
SPARQL_ENDPOINT = os.getenv("SPARQL_ENDPOINT", "http://localhost:8890/sparql")

# ChromaDB Configuration
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")

# Embedding Model Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# spaCy Model Configuration
SPACY_MODEL = os.getenv("SPACY_MODEL", "en_core_web_trf")

# LLM Configuration
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral-7b")

# Validate required LLM settings at import time (fail fast rather than silently)
if not LLM_API_KEY:
    import warnings
    warnings.warn("LLM_API_KEY is not set — LLM calls will fail", RuntimeWarning, stacklevel=1)
if not LLM_ENDPOINT:
    import warnings
    warnings.warn("LLM_ENDPOINT is not set — LLM calls will fail", RuntimeWarning, stacklevel=1)

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

# Indexing Configuration
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))
LIMIT_ENTITIES = int(os.getenv("LIMIT_ENTITIES", "10000"))  # -1 for no limit
