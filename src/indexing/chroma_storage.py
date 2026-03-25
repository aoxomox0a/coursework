"""ChromaDB Storage - Store and retrieve embeddings from ChromaDB."""
import os
import chromadb
from config.settings import CHROMA_DB_PATH


def initialize_chromadb():
    """Initialize ChromaDB client with persistent storage."""
    # Create data directory if it doesn't exist
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    
    print(f"Initializing ChromaDB (path: {CHROMA_DB_PATH})...")
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    print("✓ ChromaDB initialized")
    
    return client


def get_indexed_count(collection_name: str = "entities") -> int:
    """
    Get the count of entities already indexed in ChromaDB.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Count of indexed entities
    """
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_collection(name=collection_name)
        count = collection.count()
        return count
    except Exception as e:
        print(f"Warning: Could not get indexed count: {e}")
        return 0


def store_entities_in_chroma(entities: list, collection_name: str = "entities"):
    """
    Store embedded entities in ChromaDB.
    
    Args:
        entities: List of dicts with 'uri', 'label', and 'embedding' keys
        collection_name: Name of the collection to store in
    """
    client = initialize_chromadb()
    
    # Get or create collection
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    
    print(f"Storing {len(entities)} entities in ChromaDB collection '{collection_name}'...")
    
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


def query_entities_in_chroma(query_text: str, collection_name: str = "entities", top_k: int = 5):
    """
    Query similar entities from ChromaDB.
    
    Args:
        query_text: Query string
        collection_name: Name of the collection to query
        top_k: Number of top results to return
        
    Returns:
        List of similar entities with scores
    """
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_collection(name=collection_name)
    
    results = collection.query(
        query_texts=[query_text],
        n_results=top_k
    )
    
    return results
