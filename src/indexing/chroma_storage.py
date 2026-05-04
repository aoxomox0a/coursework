"""ChromaDB Storage - Store and retrieve embeddings from ChromaDB."""

import os
import chromadb
from urllib.parse import urlparse
from config.settings import CHROMA_DB_PATH

# Disable telemetry before any client is created (avoids capture() exceptions)
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

_client = None


def get_chroma_client():
    """Return the shared ChromaDB persistent client (process-level singleton)."""
    global _client
    if _client is None:
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return _client


# Internal alias
_get_client = get_chroma_client


def get_endpoint_slug(endpoint: str) -> str:
    """
    Generate a unique slug for an endpoint URL.

    Args:
        endpoint: Full SPARQL endpoint URL

    Returns:
        Slug identifier (e.g., 'dbpedia', 'wikidata')
    """
    if not endpoint:
        return "default"

    # Extract domain from URL
    parsed = urlparse(endpoint)
    domain = parsed.netloc.lower()

    # Map common domains to slugs
    slug_map = {
        "dbpedia.org": "dbpedia",
        "query.wikidata.org": "wikidata",
        "linkedgeodata.org": "linkedgeodata",
        "musicbrainz.org": "musicbrainz",
    }

    # Check for exact matches
    for domain_key, slug in slug_map.items():
        if domain_key in domain:
            return slug

    # Fallback: use domain name without extension
    return domain.split(".")[0]


def get_collection_name(base_name: str, endpoint: str = None) -> str:
    """
    Generate endpoint-specific collection name.

    Args:
        base_name: Base collection name (e.g., 'entities', 'properties')
        endpoint: Optional endpoint URL (if provided, creates endpoint-specific collection)

    Returns:
        Collection name (e.g., 'entities_dbpedia')
    """
    if endpoint:
        slug = get_endpoint_slug(endpoint)
        return f"{base_name}_{slug}"
    return base_name


def initialize_chromadb() -> chromadb.PersistentClient:
    """Initialize ChromaDB client with persistent storage."""
    print(f"Initializing ChromaDB (path: {CHROMA_DB_PATH})...")
    client = _get_client()
    print("✓ ChromaDB initialized")
    return client


def is_endpoint_indexed(endpoint: str = None) -> bool:
    """
    Check whether the given endpoint has already been indexed.

    Uses the `properties` collection as the canonical indicator — it is always
    populated during indexing (unlike `entities` which may be skipped).

    Args:
        endpoint: SPARQL endpoint URL (None → default collection names)

    Returns:
        True if the endpoint has been indexed and the collection is non-empty.
    """
    try:
        client = _get_client()
        existing = {c.name for c in client.list_collections()}
        props_name = get_collection_name("properties", endpoint)
        
        if props_name not in existing:
            print(f"  📭 Collection '{props_name}' does not exist - not indexed yet")
            return False
        
        collection = client.get_collection(name=props_name)
        count = collection.count()
        print(f"  📊 Collection '{props_name}' exists with {count} items")
        
        result = count > 0
        print(f"  → is_indexed: {result}")
        return result
    except Exception as e:
        print(f"  ⚠️  Error checking if indexed: {e}")
        return False


def delete_endpoint_index(endpoint: str) -> bool:
    """
    Delete all ChromaDB collections for a specific endpoint.
    
    Args:
        endpoint: SPARQL endpoint URL
    
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        client = _get_client()
        collections_to_delete = [
            "entities",
            "properties", 
            "classes",
            "sample_triples",
            "class_entity_mappings"
        ]
        
        deleted_count = 0
        for base_name in collections_to_delete:
            collection_name = get_collection_name(base_name, endpoint)
            try:
                client.delete_collection(name=collection_name)
                print(f"  🗑️  Deleted collection '{collection_name}'")
                deleted_count += 1
            except Exception as e:
                # Collection might not exist, that's fine
                pass
        
        print(f"\n✓ Deleted {deleted_count} collections for endpoint: {endpoint}\n")
        return True
    except Exception as e:
        print(f"  ⚠️  Error deleting endpoint index: {e}")
        return False


def get_indexed_count(collection_name: str = "entities", endpoint: str = None) -> int:
    """
    Get the count of entities already indexed in ChromaDB.

    Args:
        collection_name: Base collection name
        endpoint: Optional endpoint URL (if provided, uses endpoint-specific collection)

    Returns:
        Count of indexed entities
    """
    try:
        client = _get_client()

        # Generate endpoint-specific collection name
        final_collection_name = get_collection_name(collection_name, endpoint)

        # Get all collections and check if this one exists
        collections = client.list_collections()
        collection_names = [c.name for c in collections]

        if final_collection_name not in collection_names:
            # Collection doesn't exist yet, silently return 0
            return 0

        collection = client.get_collection(name=final_collection_name)
        count = collection.count()
        return count
    except Exception as e:
        # Only print for actual errors, not for missing collections
        print(f"Warning: Error getting indexed count for {collection_name}: {e}")
        return 0


def get_all_collection_counts(endpoint: str = None) -> dict:
    """
    Get counts from all collections in ChromaDB for a specific endpoint.

    Args:
        endpoint: Optional endpoint URL (if provided, gets endpoint-specific collections)

    Returns:
        Dict with collection names and their counts
    """
    base_collections = [
        "entities",
        "properties",
        "classes",
        "sample_triples",
        "class_entity_mappings",
    ]
    counts = {}

    for base_name in base_collections:
        try:
            counts[base_name] = get_indexed_count(base_name, endpoint=endpoint)
        except:
            counts[base_name] = 0

    return counts


def store_entities_in_chroma(
    entities: list, collection_name: str = "entities", endpoint: str = None
):
    """
    Store embedded entities in ChromaDB.

    Args:
        entities: List of dicts with 'uri', 'label', and 'embedding' keys
        collection_name: Base collection name to store in
        endpoint: Optional endpoint URL (if provided, creates endpoint-specific collection)
    """
    # Skip storing empty lists
    if not entities or len(entities) == 0:
        print(f"Skipping empty collection '{collection_name}' (0 entities)")
        return None

    client = initialize_chromadb()

    # Generate endpoint-specific collection name
    final_collection_name = get_collection_name(collection_name, endpoint)

    # Get or create collection
    collection = client.get_or_create_collection(
        name=final_collection_name, metadata={"hnsw:space": "cosine"}
    )

    print(
        f"Storing {len(entities)} entities in ChromaDB collection '{final_collection_name}'..."
    )

    # Prepare data for ChromaDB
    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for i, entity in enumerate(entities):
        ids.append(f"entity_{i}")
        embeddings.append(entity["embedding"])
        documents.append(entity["label"])
        metadatas.append({"uri": entity["uri"], "label": entity["label"]})

    # Add in chunks — ChromaDB rejects batches larger than ~5461
    _CHROMA_MAX_BATCH = 5000
    for start in range(0, len(ids), _CHROMA_MAX_BATCH):
        end = start + _CHROMA_MAX_BATCH
        collection.add(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )

    print(f"✓ Stored {len(entities)} entities in ChromaDB")
    return collection


def query_entities_in_chroma(
    query_text: str,
    collection_name: str = "entities",
    endpoint: str = None,
    top_k: int = 5,
):
    """
    Query similar entities from ChromaDB.

    Args:
        query_text: Query string
        collection_name: Base collection name to query
        endpoint: Optional endpoint URL (if provided, queries endpoint-specific collection)
        top_k: Number of top results to return

    Returns:
        List of similar entities with scores
    """
    # client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    # use shared client
    client = _get_client()

    # Generate endpoint-specific collection name
    final_collection_name = get_collection_name(collection_name, endpoint)

    collection = client.get_collection(name=final_collection_name)

    results = collection.query(query_texts=[query_text], n_results=top_k)

    return results


# Pool size before fusion. Pull a wider net from each scorer so RRF has
# enough overlap to reward items that both scorers like.
_HYBRID_POOL = 20


def _dense_query(
    scoped_name: str, query_text: str, n: int
) -> list[dict]:
    """Dense (Chroma) retrieval, formatted as {uri, label, score} dicts."""
    client = _get_client()
    collection = client.get_collection(name=scoped_name)
    raw = collection.query(query_texts=[query_text], n_results=n)

    if not raw or not raw.get("metadatas") or not raw["metadatas"]:
        return []

    out: list[dict] = []
    metadatas = raw["metadatas"][0]
    distances = raw["distances"][0] if raw.get("distances") else [0] * len(metadatas)
    for metadata, distance in zip(metadatas, distances):
        similarity = 1 / (1 + distance) if distance > 0 else 1.0
        out.append(
            {
                "uri": metadata.get("uri", ""),
                "label": metadata.get("label", ""),
                "score": similarity,
            }
        )
    return out


def query_candidates(
    query_text: str,
    collection_name: str,
    endpoint: str = None,
    top_k: int = 5,
    hybrid: bool = True,
) -> list[dict]:
    """
    Similarity search against an endpoint-scoped collection, returning formatted
    {uri, label, score} candidates. Shared helper for entity / relation linking.

    By default uses hybrid retrieval (dense embeddings ⊕ BM25, fused via RRF):
    this surfaces terse-label predicates (e.g. ORKG's `HAS_DATASET`) that
    MiniLM alone buries under verbose user-contributed predicates and
    empty-label system entries. Falls back to dense-only on any BM25 error so
    callers never get a worse-than-baseline result.

    Args:
        query_text: Text to embed and search with.
        collection_name: Base collection name (e.g. "entities", "properties").
        endpoint: Optional SPARQL endpoint URL — selects the endpoint-scoped collection.
        top_k: Maximum number of candidates to return.
        hybrid: When True (default), fuse dense + BM25 via RRF.

    Returns:
        List of {"uri", "label", "score"} dicts; empty list if no matches.
        ``score`` is the dense cosine similarity in dense-only mode and the
        RRF score in hybrid mode (the two scales are NOT comparable; treat
        ``score`` as a within-call ranking signal only).
    """
    scoped_name = get_collection_name(collection_name, endpoint)

    if not hybrid:
        return _dense_query(scoped_name, query_text, top_k)

    # Hybrid path: pull a pool from each scorer, fuse by RRF, take top_k.
    dense_hits = _dense_query(scoped_name, query_text, _HYBRID_POOL)

    try:
        from src.indexing.bm25_index import get_bm25_index
        from src.indexing.hybrid_retrieval import reciprocal_rank_fusion

        bm25 = get_bm25_index(scoped_name)
        bm25_hits = bm25.query(query_text, top_n=_HYBRID_POOL)

        dense_ranked = [(h["uri"], h["label"]) for h in dense_hits]
        lexical_ranked = [(h.uri, h.label) for h in bm25_hits]
        fused = reciprocal_rank_fusion([dense_ranked, lexical_ranked])
    except Exception:
        # BM25 build/query failure: silently fall back to dense-only so we
        # never regress below the pre-hybrid baseline.
        return dense_hits[:top_k]

    return [
        {"uri": h.uri, "label": h.label, "score": h.score}
        for h in fused[:top_k]
    ]
