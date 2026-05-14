# NL-to-SPARQL

Ask questions in natural language, get answers from knowledge graphs.

## What it does

- **Index** — Convert a knowledge graph into searchable embeddings
- **Link** — Extract entities and relations from questions  
- **Generate** — Build SPARQL queries from linked concepts
- **Execute** — Run queries and return results in plain English

## Quick Start

### Backend

```bash
uv run python main.py api
```

Runs on `http://localhost:8000`.

### Frontend

```bash
cd ui && npm install
npm run dev
```

Open `http://localhost:3000`.

## How to use

1. Select a SPARQL endpoint (DBpedia, Wikidata, or custom URL)
2. Click **Index** to process the knowledge graph
3. Once indexed, ask questions in natural language
4. Get SPARQL queries and results back

## What you need

- Python 3.10+
- Node.js 18+
- `uv` (Python package manager)
- `.env` configured with LLM and SPARQL endpoints

```env
SPARQL_ENDPOINT=http://dbpedia.org/sparql
LLM_ENDPOINT=your_llm_server
LLM_MODEL=mistral-7b-instruct
```

## Key endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/index` | Index a knowledge graph |
| `GET /api/status/stream` | Stream indexing progress (SSE) |
| `POST /api/generate-sparql` | NL → SPARQL query |
| `POST /api/generate-nl` | SPARQL → English explanation |
| `POST /api/answer` | NL question → SPARQL → answer |

## Architecture

```
ui/                    # React/Next.js frontend
api/                   # FastAPI routes
src/
  ├── indexing/        # ChromaDB + embeddings
  ├── linking/         # Entity & relation extraction
  └── sparql/          # SPARQL generation & execution
```

## Environment variables

```env
# Knowledge graph
SPARQL_ENDPOINT=http://dbpedia.org/sparql

# LLM for SPARQL generation
LLM_ENDPOINT=http://localhost:8001
LLM_MODEL=mistral-7b-instruct

# Storage
CHROMA_DB_PATH=./data/chroma_db

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

## Dependencies

- **FastAPI** — API server
- **Chromadb** — Vector embeddings storage  
- **sentence-transformers** — Text embeddings
- **spaCy** — Named entity recognition
- **httpx** — Async HTTP client for LLM & SPARQL calls
- **React 18** / **Next.js 14** — Frontend

## Useful links

- [Architecture Decision Records](docs/adr/) — Design docs
- [System Context](docs/architecture/system-context.puml) — High-level diagram
