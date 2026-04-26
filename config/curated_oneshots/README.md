# Curated one-shot examples

Hand-authored few-shot anchors per knowledge-graph slug. Loaded by
`src/kg_profiles/curated.py` and merged into the `KGProfile` returned by
`profile_from_index`.

## Format

One JSON file per slug: `<slug>.json`. The slug is derived from the SPARQL
endpoint URL by `src/indexing/chroma_storage.get_endpoint_slug`. Examples:

- `dbpedia.org/sparql` → `dbpedia.json`
- `orkg.org/triplestore` → `orkg.json`

Each file is a JSON array of objects with these fields:

| Field | Required | Notes |
|---|---|---|
| `question` | yes | Natural-language question shown to the LLM. |
| `entity_uris` | yes (may be `[]`) | URIs the example references. |
| `property_uri` | optional | Main relation URI; `null` or omitted if not applicable. |
| `sparql` | yes | The exemplar SPARQL query. Use full URIs or prefixes consistent with the endpoint. |
| `tags` | optional | Free-form labels (e.g. `factoid`, `aggregate`, `placeholder`). |

## Tags

- `placeholder` — the URIs in this example are unverified guesses; verify
  against the live endpoint before relying on this example.

## Adding a new KG

1. Create `<slug>.json` with at least one example.
2. Mark unverified URIs with the `placeholder` tag.
3. After indexing, the profile derived for that endpoint will pick up the
   one-shots automatically.
