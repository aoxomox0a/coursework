# Quick Start

## Install

```bash
# Frontend dependencies  
cd ui && npm install && cd ..
```

Dependencies are managed by `uv` — no need to manually install.

## Run

**Terminal 1 — Backend:**
```bash
uv run python main.py api
```

**Terminal 2 — Frontend:**
```bash
cd ui && npm run dev
```

Open `http://localhost:3000`.

## Use it

1. Choose a SPARQL endpoint
2. Click **Index** 
3. Once done, ask a question
4. Get results back

## Config

Edit `.env`:

```env
SPARQL_ENDPOINT=http://dbpedia.org/sparql
LLM_ENDPOINT=http://your-llm-server
LLM_MODEL=mistral-7b-instruct
```

## Endpoints available

Try these out of the box:
- **DBpedia** — Large knowledge graph
- **Wikidata** — Linked open data
- **Custom** — Paste any SPARQL endpoint URL

## Problems?

- **"Connection failed"?** Check the endpoint URL and your internet
- **Port already in use?** Run on different port: `npm run dev -- -p 3001`
- **Backend not responding?** Ensure `python main.py api` is running

**Slow indexing?**
- Reduce `BATCH_SIZE` in `.env` if out of memory
- Reduce `LIMIT_ENTITIES` for faster testing

**CORS errors in browser?**
- Ensure backend API is running (`python main.py api`)
- Backend CORS is configured in `api/main.py`

## Next Steps

Once entities are indexed:
- Phase 2: Implement entity and relation linking
- Phase 3: Implement SPARQL generation and execution

See `README.md` for detailed documentation.
