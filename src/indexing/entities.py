"""Entity Fetching - Fetch entities and labels from DBpedia."""
from src.indexing.endpoint import query_sparql
from config.settings import LIMIT_ENTITIES


def get_total_entity_count(sparql_endpoint: str = None) -> int:
    """
    Get the total count of entities in the SPARQL endpoint.
    
    Args:
        sparql_endpoint: Optional custom SPARQL endpoint URL
        
    Returns:
        Total count of entities
    """
    from src.indexing.endpoint import query_sparql_custom
    import requests
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
            response = requests.get(
                endpoint,
                params={"query": query, "format": "json"},
                headers={'User-Agent': 'NL-to-SPARQL-Agent/1.0'},
                timeout=300  # 5 minutes
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


def fetch_entities(limit: int = None) -> list:
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
    }}
    {limit_clause}
    """
    
    print(f"Fetching entities from DBpedia (limit: {limit if limit != -1 else 'unlimited'})...")
    
    results = query_sparql(query)
    entities = []
    
    if "results" in results and "bindings" in results["results"]:
        for binding in results["results"]["bindings"]:
            entity = {
                "uri": binding.get("entity", {}).get("value", ""),
                "label": binding.get("label", {}).get("value", "")
            }
            if entity["uri"] and entity["label"]:
                entities.append(entity)
    
    print(f"✓ Fetched {len(entities)} entities")
    return entities


def fetch_properties(limit: int = None) -> list:
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
        OPTIONAL {{ ?property rdfs:label ?label . }}
    }}
    {limit_clause}
    """
    
    print("Fetching properties/predicates...")
    
    results = query_sparql(query)
    properties = []
    
    if "results" in results and "bindings" in results["results"]:
        for binding in results["results"]["bindings"]:
            prop = {
                "uri": binding.get("property", {}).get("value", ""),
                "label": binding.get("label", {}).get("value", "")
            }
            if prop["uri"]:
                properties.append(prop)
    
    print(f"✓ Fetched {len(properties)} properties")
    return properties


def fetch_classes(limit: int = None) -> list:
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
        OPTIONAL {{ ?class rdfs:label ?label . }}
    }}
    {limit_clause}
    """
    
    print("Fetching classes/types...")
    
    results = query_sparql(query)
    classes = []
    
    if "results" in results and "bindings" in results["results"]:
        for binding in results["results"]["bindings"]:
            cls = {
                "uri": binding.get("class", {}).get("value", ""),
                "label": binding.get("label", {}).get("value", "")
            }
            if cls["uri"]:
                classes.append(cls)
    
    print(f"✓ Fetched {len(classes)} classes")
    return classes


def fetch_sample_triples(limit: int = 10000) -> list:
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
        ?subject ?predicate ?object ;
                 rdfs:label ?subjectLabel .
        ?object rdfs:label ?objectLabel .
        OPTIONAL {{ ?predicate rdfs:label ?predicateLabel . }}
        FILTER(isResource(?object))
    }}
    LIMIT {limit}
    """
    
    print(f"Fetching sample triples (limit: {limit})...")
    
    results = query_sparql(query)
    triples = []
    
    if "results" in results and "bindings" in results["results"]:
        for binding in results["results"]["bindings"]:
            triple = {
                "subject": binding.get("subject", {}).get("value", ""),
                "subjectLabel": binding.get("subjectLabel", {}).get("value", ""),
                "predicate": binding.get("predicate", {}).get("value", ""),
                "predicateLabel": binding.get("predicateLabel", {}).get("value", ""),
                "object": binding.get("object", {}).get("value", ""),
                "objectLabel": binding.get("objectLabel", {}).get("value", "")
            }
            if triple["subject"] and triple["predicate"] and triple["object"]:
                triples.append(triple)
    
    print(f"✓ Fetched {len(triples)} sample triples")
    return triples


def fetch_class_entity_mappings(limit: int = None) -> list:
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
    
    results = query_sparql(query)
    mappings = []
    
    if "results" in results and "bindings" in results["results"]:
        for binding in results["results"]["bindings"]:
            mapping = {
                "entity": binding.get("entity", {}).get("value", ""),
                "entityLabel": binding.get("entityLabel", {}).get("value", ""),
                "class": binding.get("class", {}).get("value", ""),
                "classLabel": binding.get("classLabel", {}).get("value", "")
            }
            if mapping["entity"] and mapping["class"]:
                mappings.append(mapping)
    
    print(f"✓ Fetched {len(mappings)} class-entity mappings")
    return mappings


def fetch_entities_batch(batch_size: int = 1000, max_batches: int = None) -> list:
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
    
    print(f"Fetching entities in batches (batch_size: {batch_size})...")
    
    while True:
        batch_num = batch_count + 1
        query = f"""
        SELECT ?entity ?label
        WHERE {{
            ?entity rdfs:label ?label ;
                    rdf:type ?type .
        }}
        LIMIT {batch_size}
        OFFSET {offset}
        """
        
        results = query_sparql(query)
        
        if "results" not in results or "bindings" not in results["results"]:
            break
            
        bindings = results["results"]["bindings"]
        if not bindings:
            break
        
        batch_entities = []
        for binding in bindings:
            entity = {
                "uri": binding.get("entity", {}).get("value", ""),
                "label": binding.get("label", {}).get("value", "")
            }
            if entity["uri"] and entity["label"]:
                batch_entities.append(entity)
        
        all_entities.extend(batch_entities)
        print(f"  Batch {batch_num}: {len(batch_entities)} entities (total: {len(all_entities)})")
        
        if len(batch_entities) < batch_size:
            break
        
        offset += batch_size
        batch_count += 1
        
        if max_batches and batch_count >= max_batches:
            break
    
    print(f"✓ Fetched {len(all_entities)} entities total")
    return all_entities
