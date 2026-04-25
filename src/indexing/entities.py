"""Entity Fetching — Fetch entities, properties and classes from a SPARQL endpoint.

Optional kwargs on the fetch functions allow callers (typically the indexing
pipeline) to inject endpoint-discovered conventions (label predicate, typing,
language tags). Default values preserve the original DBpedia-targeted behavior.
"""

import asyncio
import httpx

from src.indexing.endpoint import query_sparql
from config.settings import LIMIT_ENTITIES, DEFAULT_MAX_BATCHES

_DEFAULT_LABEL_PREDICATE = "http://www.w3.org/2000/01/rdf-schema#label"
_DEFAULT_PROPERTY_TYPE_URI = "http://www.w3.org/1999/02/22-rdf-syntax-ns#Property"
_DEFAULT_CLASS_TYPE_URI = "http://www.w3.org/2000/01/rdf-schema#Class"


def _lang_filter(var: str, require_lang_en: bool) -> str:
    return f"FILTER (lang(?{var}) = 'en')" if require_lang_en else ""


async def get_total_entity_count(sparql_endpoint: str = None) -> int:
    """
    Get the total count of entities in the SPARQL endpoint.

    Args:
        sparql_endpoint: Optional custom SPARQL endpoint URL

    Returns:
        Total count of entities
    """
    from src.indexing.endpoint import query_sparql_custom
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


async def fetch_entities(
    limit: int = None,
    label_predicate: str = _DEFAULT_LABEL_PREDICATE,
    require_lang_en: bool = True,
) -> list:
    """
    Fetch named entities from the SPARQL endpoint.

    Args:
        limit: Maximum number of entities to fetch (-1 for no limit)
        label_predicate: Fully-qualified URI of the label predicate to use.
        require_lang_en: Keep the FILTER(lang(?label)='en') clause when True.

    Returns:
        List of dicts with 'uri' and 'label' keys
    """
    if limit is None:
        limit = LIMIT_ENTITIES

    limit_clause = "" if limit == -1 else f"LIMIT {limit}"

    query = f"""
    SELECT ?entity ?label
    WHERE {{
        ?entity <{label_predicate}> ?label ;
                rdf:type ?type .
        {_lang_filter("label", require_lang_en)}
    }}
    {limit_clause}
    """

    print(f"Fetching entities (limit: {limit if limit != -1 else 'unlimited'})...")

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


async def fetch_properties(
    limit: int = None,
    property_type_uri: str | None = _DEFAULT_PROPERTY_TYPE_URI,
    label_predicate: str = _DEFAULT_LABEL_PREDICATE,
    require_lang_en: bool = True,
) -> list:
    """
    Fetch all properties/predicates from the SPARQL endpoint.

    Args:
        limit: Maximum number of properties to fetch (None for no limit)
        property_type_uri: Fully-qualified URI used to identify properties
            (e.g. rdf:Property, owl:ObjectProperty). Pass None to discover
            properties by their use in triples (?s ?property ?o).
        label_predicate: Label predicate to use for the OPTIONAL label fetch.
        require_lang_en: Keep the English language filter on labels when True.

    Returns:
        List of dicts with 'uri' and 'label' keys
    """
    limit_clause = "" if limit is None else f"LIMIT {limit}"

    if property_type_uri is None:
        # Untyped fallback: discover properties from their use in triples.
        query = f"""
        SELECT DISTINCT ?property ?label
        WHERE {{
            ?s ?property ?o .
            OPTIONAL {{
                ?property <{label_predicate}> ?label .
                {_lang_filter("label", require_lang_en)}
            }}
        }}
        {limit_clause}
        """
    else:
        query = f"""
        SELECT DISTINCT ?property ?label
        WHERE {{
            ?property a <{property_type_uri}> .
            OPTIONAL {{
                ?property <{label_predicate}> ?label .
                {_lang_filter("label", require_lang_en)}
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


async def fetch_classes(
    limit: int = None,
    class_type_uri: str | None = _DEFAULT_CLASS_TYPE_URI,
    label_predicate: str = _DEFAULT_LABEL_PREDICATE,
    require_lang_en: bool = True,
) -> list:
    """
    Fetch all classes/types from the SPARQL endpoint.

    Args:
        limit: Maximum number of classes to fetch (None for no limit)
        class_type_uri: Fully-qualified URI used to identify classes
            (e.g. rdfs:Class, owl:Class). Pass None to discover classes
            from type assertions (?s a ?class).
        label_predicate: Label predicate to use for the OPTIONAL label fetch.
        require_lang_en: Keep the English language filter on labels when True.

    Returns:
        List of dicts with 'uri' and 'label' keys
    """
    limit_clause = "" if limit is None else f"LIMIT {limit}"

    if class_type_uri is None:
        query = f"""
        SELECT DISTINCT ?class ?label
        WHERE {{
            ?s a ?class .
            OPTIONAL {{
                ?class <{label_predicate}> ?label .
                {_lang_filter("label", require_lang_en)}
            }}
        }}
        {limit_clause}
        """
    else:
        query = f"""
        SELECT DISTINCT ?class ?label
        WHERE {{
            ?class a <{class_type_uri}> .
            OPTIONAL {{
                ?class <{label_predicate}> ?label .
                {_lang_filter("label", require_lang_en)}
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
    batch_size: int = 1000,
    max_batches: int = DEFAULT_MAX_BATCHES,
    label_predicate: str = _DEFAULT_LABEL_PREDICATE,
    require_lang_en: bool = True,
) -> list:
    """
    Fetch entities in parallel batches with pagination.

    Args:
        batch_size: Number of entities per batch
        max_batches: Maximum number of batches (-1 for unlimited)
        label_predicate: Fully-qualified URI of the label predicate.
        require_lang_en: Keep the English-only FILTER on labels when True.

    Returns:
        List of all entities
    """
    all_entities = []

    print(
        f"\n📦 Fetching entities in batches (batch_size: {batch_size}, max_batches: {max_batches})...\n"
    )
    semaphore = asyncio.Semaphore(10)  # wikidata strict about concurrent requests

    # Wrap the entire batching process in ONE shared connection pool

    async with httpx.AsyncClient(follow_redirects=True) as shared_client:

        async def fetch_with_limit(q: str):
            async with semaphore:
                # pass shared client to endpoint logic
                return await query_sparql(q, client=shared_client)

        tasks = []
        for batch_count in range(max_batches):
            offset = batch_count * batch_size
            query = f"""
            SELECT ?entity ?label
            WHERE {{
                ?entity <{label_predicate}> ?label ;
                        rdf:type ?type .
                {_lang_filter("label", require_lang_en)}
            }}
            LIMIT {batch_size}
            OFFSET {offset}
            """
            tasks.append(fetch_with_limit(query))

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
            print(
                f"  ✓ Batch {batch_idx:3d}: {batch_entities_count:4d} entities (total: {len(all_entities):,})"
            )
        else:
            print(f"  ✗ Batch {batch_idx:3d}: No entities (fetch completed)")

    print(f"\n✓ Fetched {len(all_entities):,} entities total\n")
    return all_entities
