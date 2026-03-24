"""Indexing Pipeline - Orchestrate the entity indexing workflow."""
from src.indexing import endpoint, entities, embedding, chroma_storage
from config.settings import BATCH_SIZE, LIMIT_ENTITIES


def run_indexing_pipeline(custom_endpoint: str = None, resume: bool = False):
    """
    Execute the complete indexing pipeline:
    1. Test SPARQL endpoint connection
    2. Fetch entities from DBpedia
    3. Generate embeddings
    4. Store in ChromaDB

    Args:
        custom_endpoint: Optional custom SPARQL endpoint URL
        resume: If True, resume from checkpoint; if False, start from 0
    """
    # Set custom endpoint if provided
    if custom_endpoint:
        endpoint.set_endpoint(custom_endpoint)

    print("\n" + "="*60)
    print("INDEXING PIPELINE - NL-to-SPARQL System")
    print("="*60)
    
    # Step 1: Test endpoint connection
    print("\n[Step 1] Testing SPARQL Endpoint Connection")
    print("-" * 60)
    if not endpoint.test_connection():
        print("✗ Failed to connect to SPARQL endpoint. Aborting.")
        return False
    
    # Step 2: Fetch entities
    print("\n[Step 2] Fetching Entities from DBpedia")
    print("-" * 60)
    fetched_entities = entities.fetch_entities_batch(
        batch_size=BATCH_SIZE,
        max_batches=None,
        resume=resume
    )
    
    if not fetched_entities:
        print("✗ No entities fetched. Aborting.")
        return False
    
    # Step 3: Generate embeddings
    print("\n[Step 3] Generating Text Embeddings")
    print("-" * 60)
    model = embedding.load_embedding_model()
    embedded_entities = embedding.embed_entities(fetched_entities, model)
    
    # Step 4: Store in ChromaDB
    print("\n[Step 4] Storing in ChromaDB")
    print("-" * 60)
    chroma_storage.store_entities_in_chroma(embedded_entities, collection_name="entities")
    
    # Summary
    print("\n" + "="*60)
    print("✓ INDEXING PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*60)
    print(f"Indexed {len(embedded_entities)} entities")
    print(f"Stored in: {chroma_storage.CHROMA_DB_PATH}")
    print()
    
    return True


if __name__ == "__main__":
    run_indexing_pipeline()
