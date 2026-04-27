"""Indexing Pipeline - Orchestrate the entity indexing workflow."""

from src.indexing import endpoint, entities, embedding, chroma_storage, discovery
from config.settings import BATCH_SIZE, LIMIT_ENTITIES
import asyncio
from typing import Dict


async def run_indexing_pipeline(
    custom_endpoint: str = None, status_callback=None, max_entities: int = None
) -> Dict:
    """
    Execute the complete indexing pipeline:
    1. Test SPARQL endpoint connection
    2. Fetch schema (properties, classes)
    3. Fetch entities from DBpedia
    4. Fetch relationships (sample triples, mappings)
    5. Generate embeddings
    6. Store in ChromaDB

    Args:
        custom_endpoint: Optional custom SPARQL endpoint URL
        status_callback: Optional callback function to receive status updates
        max_entities: Optional maximum number of entities to fetch

    Returns:
        Dict with status and indexed counts, or False on error
    """

    def send_status(message: str):
        """Send status update to callback if provided."""
        print(message)
        if status_callback:
            status_callback(message, custom_endpoint)

    # Set custom endpoint if provided
    if custom_endpoint:
        endpoint.set_endpoint(custom_endpoint)

    print("\n" + "=" * 60)
    print("INDEXING PIPELINE - NL-to-SPARQL System")
    print("=" * 60)

    # Step 1: Test endpoint connection
    send_status("▸ Testing SPARQL endpoint connection...")
    if not await endpoint.test_connection():
        send_status("✗ Failed to connect to SPARQL endpoint")
        raise ConnectionError(
            f"Cannot reach SPARQL endpoint at {custom_endpoint or 'default'}"
        )

    # Step 1b: Probe endpoint conventions (label predicate, typing, language tags)
    active_endpoint = endpoint.get_endpoint()
    send_status("▸ Probing endpoint conventions (label predicate, typing)...")
    profile = await discovery.discover_profile(active_endpoint)
    discovery.save_profile(profile)
    send_status(
        f"  ↳ label={profile.label_predicate.rsplit('#', 1)[-1]}, "
        f"properties={profile.property_typing}, classes={profile.class_typing}, "
        f"lang={'en' if profile.has_language_tags else 'untagged'}"
    )

    prop_type_uri = discovery.property_type_uri_for(profile.property_typing)
    class_type_uri = discovery.class_type_uri_for(profile.class_typing)

    # Step 2: Fetch schema (properties and classes)
    send_status("▸ Fetching schema properties...")
    fetched_properties = await entities.fetch_properties(
        property_type_uri=prop_type_uri,
        label_predicate=profile.label_predicate,
        require_lang_en=profile.has_language_tags,
    )

    send_status("▸ Fetching schema classes...")
    fetched_classes = await entities.fetch_classes(
        class_type_uri=class_type_uri,
        label_predicate=profile.label_predicate,
        require_lang_en=profile.has_language_tags,
    )

    # Step 3: Fetch entities (respect max_entities parameter or LIMIT_ENTITIES from config)
    send_status("▸ Fetching entities from SPARQL endpoint...")
    import math

    # Use max_entities parameter if provided, otherwise use config
    entity_limit = max_entities if max_entities is not None else LIMIT_ENTITIES

    required_batches = (
        max(1, math.ceil(entity_limit / BATCH_SIZE)) if entity_limit > 0 else None
    )
    fetched_entities = await entities.fetch_entities_batch(
        batch_size=BATCH_SIZE,
        max_batches=required_batches,
        label_predicate=profile.label_predicate,
        require_lang_en=profile.has_language_tags,
    )
    if entity_limit > 0:
        fetched_entities = fetched_entities[:entity_limit]

    if not fetched_entities:
        send_status("⊘ No entities fetched, continuing with schema only...")
        fetched_entities = []

    # Step 4: Fetch relationships
    send_status("▸ Fetching relationships (skipped for testing)")
    sample_triples = []
    class_entity_mappings = []

    # Step 5: Generate embeddings
    send_status("▸ Loading embedding model and generating embeddings...")
    model = embedding.load_embedding_model()

    # offload SentenceTransformer math so it doesn't block the asynchronous loop
    embedded_entities = (
        await asyncio.to_thread(embedding.embed_entities, fetched_entities, model)
        if fetched_entities
        else []
    )
    embedded_properties = await asyncio.to_thread(
        embedding.embed_entities, fetched_properties, model
    )
    embedded_classes = await asyncio.to_thread(
        embedding.embed_entities, fetched_classes, model
    )

    # Step 6: Store in ChromaDB
    if embedded_entities:
        send_status("▸ Storing entities in ChromaDB...")
        await asyncio.to_thread(
            chroma_storage.store_entities_in_chroma,
            embedded_entities,
            collection_name="entities",
            endpoint=custom_endpoint,
        )

    send_status("▸ Storing properties in ChromaDB...")
    await asyncio.to_thread(
        chroma_storage.store_entities_in_chroma,
        embedded_properties,
        collection_name="properties",
        endpoint=custom_endpoint,
    )

    send_status("▸ Storing classes in ChromaDB...")
    await asyncio.to_thread(
        chroma_storage.store_entities_in_chroma,
        embedded_classes,
        collection_name="classes",
        endpoint=custom_endpoint,
    )

    # Summary
    print("\n" + "=" * 60)
    print("✓ INDEXING PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Indexed {len(fetched_entities)} entities")
    print(f"Indexed {len(fetched_properties)} properties")
    print(f"Indexed {len(fetched_classes)} classes")
    print(f"Stored in: {chroma_storage.CHROMA_DB_PATH}")
    print()

    return {
        "entities": len(embedded_entities),
        "properties": len(embedded_properties),
        "classes": len(embedded_classes),
    }


if __name__ == "__main__":
    from config.settings import SPARQL_ENDPOINT

    asyncio.run(run_indexing_pipeline(custom_endpoint=SPARQL_ENDPOINT))
