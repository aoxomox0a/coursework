"""Entity Fetching - Fetch entities and labels from DBpedia."""

from src.indexing.endpoint import query_sparql
from config.settings import LIMIT_ENTITIES, DEFAULT_MAX_BATCHES
import asyncio


async def get_total_entity_count(sparql_endpoint: str = None) -> int:
    """
    Get the total count of entities in the SPARQL endpoint.

    Args:
        sparql_endpoint: Optional custom SPARQL endpoint URL

    Returns:
        Total count of entities
    """
    from src.indexing.endpoint import query_sparql_custom
    import httpx
    from config.settings import SPARQL_ENDPOINT

    # Try different query approaches to get accurate count
    queries = [
        # Try 1: DISTINCT count (most accurate, but slower)
        """
        SELECT (COUNT(DISTINCT ?entity) as ?count)
        WHERE {
            ?entity rdfs:label ?label .
        }
        """,
        # Try 2: Simple count
        """
        SELECT (COUNT(?entity) as ?count)
        WHERE {
            ?entity rdfs:label ?label .
        }
        """,
    ]

    print("Fetching total entity count (this may take a while for large endpoints)...")

    for attempt, query in enumerate(queries, 1):
        try:
            endpoint = sparql_endpoint if sparql_endpoint else SPARQL_ENDPOINT

            print(f"  Attempt {attempt}...")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    endpoint,
                    params={"query": query, "format": "json"},
                    headers={"User-Agent": "NL-to-SPARQL-Agent/1.0"},
                    timeout=300,  # 5 minutes
                )
                response.raise_for_status()
                results = response.json()

                if "results" in results and "bindings" in results["results"]:
                    bindings = results["results"]["bindings"]
                    if bindings and "count" in bindings[0]:
                        count = int(bindings[0]["count"]["value"])
                        print(f"✓ Total entities: {count:,}")
                        return count
        except Exception as e:
            print(f"  Attempt {attempt} failed: {e}")
            continue

    # If all attempts fail, return 0
    print("⚠ Total entity count unavailable - UI will show 0 progress initially")
    return 0


async def fetch_entities(limit: int = None) -> list:
    """
    Fetch named entities from DBpedia.

    Args:
        limit: Maximum number of entities to fetch (-1 for no limit)

    Returns:
        List of dicts with 'uri' and 'label' keys
    """
    if limit is None:
        limit = LIMIT_ENTITIES

    limit_clause = "" if limit == -1 else f"LIMIT {limit}"

    # Query to fetch entities with labels (all languages)
    query = f"""
    SELECT ?entity ?label
    WHERE {{
        ?entity rdfs:label ?label ;
                rdf:type ?type .
        FILTER (lang(?label) = 'en')
    }}
    {limit_clause}
    """

    print(
        f"Fetching entities from DBpedia (limit: {limit if limit != -1 else 'unlimited'})..."
    )

    results = await query_sparql(query)
    entities = []

    if "results" in results and "bindings" in results["results"]:
        for binding in results["results"]["bindings"]:
            entity = {
                "uri": binding.get("entity", {}).get("value", ""),
                "label": binding.get("label", {}).get("value", ""),
            }
            if entity["uri"] and entity["label"]:
                entities.append(entity)

    print(f"✓ Fetched {len(entities)} entities")
    return entities


async def fetch_properties(limit: int = None) -> list:
    """
    Fetch all properties/predicates from the SPARQL endpoint.

    Args:
        limit: Maximum number of properties to fetch (None for no limit)

    Returns:
        List of dicts with 'uri' and 'label' keys
    """
    limit_clause = "" if limit is None else f"LIMIT {limit}"

    query = f"""
    SELECT DISTINCT ?property ?label
    WHERE {{
        ?property a rdf:Property .
        OPTIONAL {{
            ?property rdfs:label ?label .
            FILTER (lang(?label) = 'en')
        }}
    }}
    {limit_clause}
    """

    print("Fetching properties/predicates...")

    results = await query_sparql(query)
    properties = []

    if "results" in results and "bindings" in results["results"]:
        for binding in results["results"]["bindings"]:
            prop = {
                "uri": binding.get("property", {}).get("value", ""),
                "label": binding.get("label", {}).get("value", ""),
            }
            if prop["uri"]:
                properties.append(prop)

    print(f"✓ Fetched {len(properties)} properties")
    return properties


async def fetch_classes(limit: int = None) -> list:
    """
    Fetch all classes/types from the SPARQL endpoint.

    Args:
        limit: Maximum number of classes to fetch (None for no limit)

    Returns:
        List of dicts with 'uri' and 'label' keys
    """
    limit_clause = "" if limit is None else f"LIMIT {limit}"

    query = f"""
    SELECT DISTINCT ?class ?label
    WHERE {{
        ?class a rdfs:Class .
        OPTIONAL {{ 
            ?class rdfs:label ?label .
            FILTER (lang(?label) = 'en')
        }}
    }}
    {limit_clause}
    """

    print("Fetching classes/types...")

    results = await query_sparql(query)
    classes = []

    if "results" in results and "bindings" in results["results"]:
        for binding in results["results"]["bindings"]:
            cls = {
                "uri": binding.get("class", {}).get("value", ""),
                "label": binding.get("label", {}).get("value", ""),
            }
            if cls["uri"]:
                classes.append(cls)

    print(f"✓ Fetched {len(classes)} classes")
    return classes


async def fetch_sample_triples(limit: int = 10000) -> list:
    """
    Fetch sample triples (relationships) from the SPARQL endpoint.

    Args:
        limit: Maximum number of triples to fetch

    Returns:
        List of dicts with 'subject', 'predicate', 'object' and labels
    """
    query = f"""
    SELECT ?subject ?subjectLabel ?predicate ?predicateLabel ?object ?objectLabel
    WHERE {{
        ?subject ?predicate ?object .
        FILTER(isURI(?object))

        ?subject rdfs:label ?subjectLabel .
        FILTER(lang(?subjectLabel) = 'en')

        ?object rdfs:label ?objectLabel .
        FILTER(lang(?objectLabel) = 'en')

        OPTIONAL {{
            ?predicate rdfs:label ?predicateLabel .
            FILTER(lang(?predicateLabel) = 'en')
        }}
    }}
    LIMIT {limit}
    """

    print(f"Fetching sample triples (limit: {limit})...")

    results = await query_sparql(query)
    triples = []

    if "results" in results and "bindings" in results["results"]:
        for binding in results["results"]["bindings"]:
            triple = {
                "subject": binding.get("subject", {}).get("value", ""),
                "subjectLabel": binding.get("subjectLabel", {}).get("value", ""),
                "predicate": binding.get("predicate", {}).get("value", ""),
                "predicateLabel": binding.get("predicateLabel", {}).get("value", ""),
                "object": binding.get("object", {}).get("value", ""),
                "objectLabel": binding.get("objectLabel", {}).get("value", ""),
            }
            if triple["subject"] and triple["predicate"] and triple["object"]:
                triples.append(triple)

    print(f"✓ Fetched {len(triples)} sample triples")
    return triples


async def fetch_class_entity_mappings(limit: int = None) -> list:
    """
    Fetch mappings of entities to their classes/types.

    Args:
        limit: Maximum number of mappings to fetch (None for no limit)

    Returns:
        List of dicts with entity, entityLabel, class, classLabel
    """
    limit_clause = "" if limit is None else f"LIMIT {limit}"

    query = f"""
    SELECT ?entity ?entityLabel ?class ?classLabel
    WHERE {{
        ?entity rdf:type ?class ;
                rdfs:label ?entityLabel .
        ?class rdfs:label ?classLabel .
    }}
    {limit_clause}
    """

    print("Fetching class-entity mappings...")

    results = await query_sparql(query)
    mappings = []

    if "results" in results and "bindings" in results["results"]:
        for binding in results["results"]["bindings"]:
            mapping = {
                "entity": binding.get("entity", {}).get("value", ""),
                "entityLabel": binding.get("entityLabel", {}).get("value", ""),
                "class": binding.get("class", {}).get("value", ""),
                "classLabel": binding.get("classLabel", {}).get("value", ""),
            }
            if mapping["entity"] and mapping["class"]:
                mappings.append(mapping)

    print(f"✓ Fetched {len(mappings)} class-entity mappings")
    return mappings


async def fetch_entities_batch(
    batch_size: int = 1000, max_batches: int = DEFAULT_MAX_BATCHES
) -> list:
    """
    Fetch entities in batches with pagination.

    Args:
        batch_size: Number of entities per batch
        max_batches: Maximum number of batches (-1 for unlimited)

    Returns:
        List of all entities
    """
    all_entities = []
    offset = 0
    batch_count = 0

    print(f"\n📦 Fetching entities in batches (batch_size: {batch_size}, max_batches: {max_batches})...\n")

    # 1. create list of tasks to run
    tasks = []
    for batch_count in range(max_batches):
        # batch_num = batch_count + 1
        offset = batch_count * batch_size
        query = f"""
        SELECT ?entity ?label
        WHERE {{
            ?entity rdfs:label ?label ;
                    rdf:type ?type .
                    FILTER (lang(?label) = 'en')
        }}
        LIMIT {batch_size}
        OFFSET {offset}
        """
        tasks.append(query_sparql(query))

    # 2. fire all queries at the same time
    print(f"⏳ Downloading {len(tasks)} batches concurrently...\n")
    all_results = await asyncio.gather(*tasks)

    # 3. process returned list and show batch progress
    for batch_idx, results in enumerate(all_results, 1):
        batch_entities_count = 0
        if (
            isinstance(results, dict)
            and "results" in results
            and "bindings" in results["results"]
        ):
            for binding in results["results"]["bindings"]:
                entity = {
                    "uri": binding.get("entity", {}).get("value", ""),
                    "label": binding.get("label", {}).get("value", ""),
                }
                if entity["uri"] and entity["label"]:
                    all_entities.append(entity)
                    batch_entities_count += 1
        
        # Show progress per batch
        if batch_entities_count > 0:
            print(f"  ✓ Batch {batch_idx:3d}: {batch_entities_count:4d} entities (total: {len(all_entities):,})")
        else:
            print(f"  ✗ Batch {batch_idx:3d}: No entities (fetch completed)")

    print(f"\n✓ Fetched {len(all_entities):,} entities total\n")
    return all_entities
