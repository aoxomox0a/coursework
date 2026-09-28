# `api/` — FastAPI Application Layer

## What it does

This package is the HTTP interface between the frontend and the core pipeline modules in `src/`. It defines the FastAPI application, mounts the CORS middleware, and registers all route handlers. Business logic stays in `src/` — the API layer only handles request parsing, response formatting, and background task management.

## Files

| File | Role |
|------|------|
| `main.py` | Creates the FastAPI `app`, registers routers, manages HTTP client lifecycle (startup/shutdown) |
| `routes/indexing.py` | `POST /api/index`, `GET /api/status/stream` (SSE), `POST /api/check` |
| `routes/sparql.py` | `POST /api/generate-sparql`, `POST /api/generate-nl`, `POST /api/answer` |
| `routes/linking.py` | Internal linking route (used for debugging) |

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/check` | Check if an endpoint has been indexed; returns `{ "indexed": bool }` |
| `POST` | `/api/index` | Start background indexing for an endpoint; returns `202 Accepted` immediately |
| `GET` | `/api/status/stream` | Server-Sent Events stream of indexing progress messages |
| `POST` | `/api/generate-sparql` | NL question → SPARQL query |
| `POST` | `/api/generate-nl` | SPARQL query → English explanation |
| `POST` | `/api/answer` | NL question → full pipeline → NL answer |

## Background indexing

`POST /api/index` starts a background `asyncio.Task`. The `indexing_state` module in `src/indexing/` tracks whether indexing is running, so subsequent calls to `/api/check` and the SSE stream can report live progress without polling the database.

## How to run

```bash
uv run python main.py api
```

Runs on `http://localhost:8000`. The frontend at `http://localhost:3000` sends requests to this server.

## CORS

CORS is configured to allow `http://localhost:3000` (Next.js dev server). Adjust `allow_origins` in `main.py` for production deployments.
