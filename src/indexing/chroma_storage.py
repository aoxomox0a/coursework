"""ChromaDB Storage - Store and retrieve embeddings from ChromaDB."""
import os
import chromadb
from urllib.parse import urlparse
from config.settings import CHROMA_DB_PATH


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
    return domain.split('.')[0]


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


def initialize_chromadb():
    """Initialize ChromaDB client with persistent storage."""
    # Create data directory if it doesn't exist
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    
    print(f"Initializing ChromaDB (path: {CHROMA_DB_PATH})...")
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    print("✓ ChromaDB initialized")
    
    return client


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
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        
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
    base_collections = ["entities", "properties", "classes", "sample_triples", "class_entity_mappings"]
    counts = {}
    
    for base_name in base_collections:
        try:
            counts[base_name] = get_indexed_count(base_name, endpoint=endpoint)
        except:
            counts[base_name] = 0
    
    return counts


def store_entities_in_chroma(entities: list, collection_name: str = "entities", endpoint: str = None):
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
        name=final_collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    
    print(f"Storing {len(entities)} entities in ChromaDB collection '{final_collection_name}'...")
    
    # Prepare data for ChromaDB
    ids = []
    embeddings = []
    documents = []
    metadatas = []
    
    for i, entity in enumerate(entities):
        ids.append(f"entity_{i}")
        embeddings.append(entity["embedding"])
        documents.append(entity["label"])
        metadatas.append({
            "uri": entity["uri"],
            "label": entity["label"]
        })
    
    # Add to collection
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    
    print(f"✓ Stored {len(entities)} entities in ChromaDB")
    return collection


def query_entities_in_chroma(query_text: str, collection_name: str = "entities", endpoint: str = None, top_k: int = 5):
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
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # Generate endpoint-specific collection name
    final_collection_name = get_collection_name(collection_name, endpoint)
    
    collection = client.get_collection(name=final_collection_name)
    
    results = collection.query(
        query_texts=[query_text],
        n_results=top_k
    )
    
    return results
