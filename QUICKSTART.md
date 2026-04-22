# Quick Start Guide

Get the NL-to-SPARQL indexing system up and running in minutes.

## Prerequisites

- Python 3.10+
- Node.js 16+ (for the web UI)
- uv (Python package manager)

## Setup

### 1. Backend Setup

```bash
# Install Python dependencies
uv sync
```

### 2. Frontend Setup

```bash
# Install JavaScript dependencies
cd ui
npm install
cd ..
```

## Running the System

### Option A: Web UI (Recommended)

**Terminal 1 - Start Backend API:**

```bash
uv run python main.py api
# API running at http://localhost:8000
```

**Terminal 2 - Start Frontend:**

```bash
cd ui
npm run dev
# UI running at http://localhost:3000
```

Open `http://localhost:3000` in your browser, select an endpoint, and click "Index"!

### Option B: Command Line

```bash
# Index with default endpoint (DBpedia)
uv run python main.py index

# Index with custom endpoint via CLI (coming soon)
```

## Testing the System

### Unit Tests

Run the test suite to verify core functionality:

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/sparql/test_pipeline.py
```

### Integration Tests

Test the full system end-to-end:

```bash
# Start the API server in background
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# Run the prompt test script
./scripts/prompt_test.sh

# Stop the background server
kill %1
```

### Manual Testing

1. **Index some entities** using the web UI or CLI
2. **Query the system** via API or web interface
3. **Verify results** in the ChromaDB storage

## Configuration

Edit `.env` to customize:

```env
# Default SPARQL endpoint
SPARQL_ENDPOINT=http://dbpedia.org/sparql

# Where to store indexed embeddings
CHROMA_DB_PATH=./data/chroma_db

# Embedding model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Number of entities to fetch per batch
BATCH_SIZE=100

# Total entities to index (-1 for all)
LIMIT_ENTITIES=10000
```

## What Happens During Indexing

1. ✓ **Connection Test** - Verifies SPARQL endpoint is reachable
2. ✓ **Entity Fetching** - Retrieves all entities and labels from the graph
3. ✓ **Embedding Generation** - Converts text to vector embeddings
4. ✓ **Storage** - Saves embeddings in ChromaDB for similarity search

## Typical File Sizes

- **CHROMA_DB_PATH** - ~100-200MB for 10,000 entities
- **Memory Usage** - ~2-4GB during indexing (depends on batch size)

## Troubleshooting

**"Connection failed" error?**

- Verify the SPARQL endpoint URL is correct
- Check your internet connection
- Try DBpedia directly: `http://dbpedia.org/sparql`

**Port 3000/8000 already in use?**

- Change port for UI: `cd ui && npm run dev -- -p 3001`
- Change port for API: Update `API_PORT` in `.env`

**Slow indexing?**

- Reduce `BATCH_SIZE` in `.env` if out of memory
- Reduce `LIMIT_ENTITIES` for faster testing

**CORS errors in browser?**

- Ensure backend API is running (`uv run python main.py api`)
- Backend CORS is configured in `api/main.py`

## Next Steps

Once entities are indexed:

- Phase 2: Implement entity and relation linking
- Phase 3: Implement SPARQL generation and execution

See `README.md` for detailed documentation.
