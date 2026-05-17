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
- `.env` configured — see [Environment variables](#environment-variables) below

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
  ├── sparql/          # SPARQL generation & execution
  ├── evaluation/      # Offline pipeline evaluation
  └── kg_profiles/     # Per-endpoint configuration & few-shot examples
config/
  └── curated_oneshots/  # Hand-authored Q/SPARQL examples per endpoint
tests/                 # Full test suite (mirrors src/)
docs/
  └── adr/             # Architecture Decision Records
```

## Module documentation

| Module | README | Description |
|--------|--------|-------------|
| `src/` | [src/README.md](src/README.md) | Pipeline overview and module connections |
| `src/indexing/` | [src/indexing/README.md](src/indexing/README.md) | Knowledge graph indexing into ChromaDB |
| `src/linking/` | [src/linking/README.md](src/linking/README.md) | Entity & relation extraction and linking |
| `src/sparql/` | [src/sparql/README.md](src/sparql/README.md) | SPARQL generation, validation, and execution |
| `src/evaluation/` | [src/evaluation/README.md](src/evaluation/README.md) | Offline evaluation framework and metrics |
| `src/kg_profiles/` | [src/kg_profiles/README.md](src/kg_profiles/README.md) | Per-endpoint profiles and one-shot examples |
| `api/` | [api/README.md](api/README.md) | FastAPI routes and HTTP interface |
| `ui/` | [ui/README.md](ui/README.md) | React/Next.js frontend |
| `tests/` | [tests/README.md](tests/README.md) | Test suite structure and how to run tests |
| `config/curated_oneshots/` | [config/curated_oneshots/README.md](config/curated_oneshots/README.md) | Format and instructions for few-shot examples |

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

- [Architecture Decision Records](docs/adr/) — Design decisions and rationale
- [System Context diagram](docs/architecture/system-context.puml) — High-level component view
- [QUICKSTART.md](QUICKSTART.md) — Step-by-step first-run guide
