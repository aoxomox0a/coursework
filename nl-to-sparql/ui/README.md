# Frontend (Next.js)

React + Next.js UI for the NL-to-SPARQL system.

## Setup

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

(Backend should be running with `uv run python main.py api`)

## Main features

- **Endpoint selector** — Choose from predefined endpoints or add custom URLs
- **Real-time indexing** — Stream status updates while the backend processes data
- **Query builder** — Three workflows:
  - Natural language → SPARQL query
  - SPARQL → English explanation
  - Natural language → Direct answer
- **Error handling** — Shows backend errors to help debug

## How it talks to the backend

- `POST /api/check` — Check if endpoint is indexed
- `POST /api/index` — Start indexing (background task)
- `GET /api/status/stream` — Stream progress updates (SSE)
- `POST /api/generate-sparql` — NL → SPARQL
- `POST /api/generate-nl` — SPARQL → explanation
- `POST /api/answer` — NL → answer

## Key components

- **QueryTranslator.jsx** — Main component with all workflows
- **StatusBox.jsx** — Global status message display
- **StatusContext.js** — Shared state for status updates
- **CSS Modules** — Component-scoped styling
