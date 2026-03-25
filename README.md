# Natural Language to SPARQL (NL-to-SPARQL)

Convert natural language questions into SPARQL queries to automatically retrieve answers from knowledge graphs.

## Overview

This system translates natural language questions to formal SPARQL queries through a 3-phase pipeline:

1. **Indexing** — Index knowledge graph data (properties, classes, entities) into vector embeddings
2. **Linking** — Extract and link entities and relations from questions
3. **SPARQL** — Generate SPARQL from linked entities, validate, execute, and format results

## Project Structure

```
nl-to-sparql/
├── config/                 # Configuration management
│   ├── settings.py        # Load environment variables (endpoint URLs, API keys)
│
├── src/                   # Core business logic
│   ├── indexing/          # Graph indexing pipeline
│   │   ├── endpoint.py    # Connect to SPARQL endpoint
│   │   ├── embedding.py   # Embed labels with sentence-transformers
│   │   ├── entities.py    # Fetch entities from knowledge graph
│   │   ├── chroma_storage.py # Store embeddings in ChromaDB
│   │   └── pipeline.py    # Orchestrate indexing
│   │
│   ├── linking/           # Entity & relation linking (Phase 2 - TBD)
│   └── sparql/            # SPARQL generation (Phase 3 - TBD)
│
├── api/                   # FastAPI REST endpoints
│   └── main.py           # FastAPI app setup + /api/index endpoint
│
├── ui/                    # React/Next.js web interface
│   ├── components/        # React components
│   ├── pages/            # Next.js pages
│   ├── styles/           # CSS modules
│   ├── package.json      # JavaScript dependencies
│   └── next.config.js    # Next.js configuration
│
├── main.py              # CLI entry point
├── requirements.txt     # Python dependencies
├── .env                 # Configuration
└── .gitignore          # Git ignore patterns
```

## Installation

### 1. Clone and setup

```bash
cd nl-to-sparql
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 3. Configure environment

Edit `.env` with your settings:

```env
SPARQL_ENDPOINT=http://your-endpoint:port/sparql
LLM_API_KEY=your_huggingface_key
LLM_ENDPOINT=your_llm_endpoint_url
```

## Usage

### Via Web UI (Recommended)

Start both the backend and frontend:

**Terminal 1 - Backend API:**
```bash
python main.py api
```

**Terminal 2 - Frontend UI:**
```bash
cd ui
npm install  # First time only
npm run dev
```

Open `http://localhost:3000` in your browser and:
1. **Select endpoint** - Choose from predefined endpoints (DBpedia, Wikidata, Localhost) or paste a custom URL
2. **Click Index** - Start the indexing pipeline
3. **Monitor progress** - Watch the real-time status updates and indicators
4. **Verify result** - Check success/error status with detailed feedback

### Via CLI

```bash
# Run indexing pipeline
python main.py index

# Start API server
python main.py api
```

### Via API

Start the server:
```bash
python main.py api
```

Then make requests:

```bash
# Index knowledge graph (accepts optional custom endpoint)
curl -X POST http://localhost:8000/api/index \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "http://dbpedia.org/sparql"}'
```

## Component Details

### Indexing Pipeline

**Goal:** Index knowledge graph entities, properties, and classes as vector embeddings.

**Workflow:**
1. Connect to SPARQL endpoint with test query
2. Fetch all properties (predicates) and classes from the graph
3. Embed labels using `sentence-transformers`
4. Fetch named entities from the graph
5. Store all embeddings in ChromaDB for similarity search

**Key Files:**
- `src/indexing/endpoint.py` — SPARQL connection
- `src/indexing/properties.py` — SPARQL queries to fetch properties and classes
- `src/indexing/embedding.py` — Embedding generation
- `src/indexing/entities.py` — Entity fetching
- `src/indexing/pipeline.py` — Orchestrates the full flow

### Linking Pipeline

**Goal:** Extract and disambiguate entities and relations from a natural language question.

**Workflow:**
1. Load spaCy NLP model for NER
2. Extract named entities and noun phrases from question
3. Query ChromaDB to find matching entity URIs (with confidence scores)
4. Embed the question and find similar properties in ChromaDB
5. Return linked entities and candidate relations

**Key Files:**
- `src/linking/entity_extraction.py` — spaCy-based NER
- `src/linking/entity_linking.py` — Match entities to URIs
- `src/linking/relation_linking.py` — Match relations to properties
- `src/linking/pipeline.py` — Orchestrates the full flow

### SPARQL Pipeline

**Goal:** Generate valid SPARQL queries and execute them on the endpoint.

**Workflow:**
1. Create an LLM prompt with the question, linked entities, and properties
2. Call LLM (HuggingFace, Replicate, or custom) to generate SPARQL
3. Validate SPARQL syntax
4. If invalid, retry with a fix prompt
5. Execute the query on the SPARQL endpoint
6. Format results as human-readable text

**Key Files:**
- `src/sparql/prompt.py` — LLM prompt templates
- `src/sparql/llm.py` — LLM API calls
- `src/sparql/validation.py` — SPARQL syntax validation
- `src/sparql/execution.py` — Query execution and formatting
- `src/sparql/pipeline.py` — Orchestrates the full flow

## Configuration

### Environment Variables (`.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `SPARQL_ENDPOINT` | SPARQL endpoint URL | `http://localhost:8890/sparql` |
| `CHROMA_DB_PATH` | Path to ChromaDB persistent storage | `./data/chroma_db` |
| `EMBEDDING_MODEL` | Sentence-transformers model | `sentence-transformers/all-MiniLM-L6-v2` |
| `SPACY_MODEL` | spaCy model name | `en_core_web_sm` |
| `LLM_API_KEY` | LLM provider API key | From HuggingFace |
| `LLM_ENDPOINT` | LLM API endpoint URL | HuggingFace inference URL |
| `LLM_MODEL` | LLM model name | `mistral-7b` |
| `API_HOST` | API server host | `0.0.0.0` |
| `API_PORT` | API server port | `8000` |

## Workflow Example

```
User Question: "Who directed Inception?"
       ↓
[Indexing: Already indexed]
       ↓
[Linking]
  - Extract: ["Inception" (MOVIE), "directed"]
  - Link entity: "Inception" → http://dbpedia.org/resource/Inception
  - Link relation: "directed" → http://dbpedia.org/property/director
       ↓
[SPARQL]
  - LLM generates: SELECT ?director WHERE { ?inception rdf:label "Inception" . ?inception dbpedia:director ?director }
  - Execute on endpoint
  - Format: "Christopher Nolan"
```

## Dependencies

- **FastAPI** — REST API framework
- **spaCy** — Named entity recognition
- **sentence-transformers** — Text embedding
- **ChromaDB** — Vector database
- **requests** — HTTP client for SPARQL queries
- **python-dotenv** — Environment variable management

## Next Steps

- Configure your SPARQL endpoint in `.env`
- Run `python main.py index` to index your knowledge graph
- Test with sample questions using `python main.py answer "your question"`
- Deploy API with `python main.py api` or use Docker

## License

MIT
