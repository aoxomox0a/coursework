"""Entity Fetching - Fetch entities and labels from DBpedia."""
import json
import os
from src.indexing.endpoint import query_sparql
from config.settings import LIMIT_ENTITIES


CHECKPOINT_FILE = "./data/indexing_checkpoint.json"


def load_checkpoint():
    """Load checkpoint data if it exists."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load checkpoint: {e}")
    return None


def save_checkpoint(offset: int, batch_count: int, total_entities: int):
    """Save checkpoint data."""
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    checkpoint = {
        "offset": offset,
        "batch_count": batch_count,
        "total_entities": total_entities
    }
    try:
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint, f)
    except Exception as e:
        print(f"Warning: Could not save checkpoint: {e}")


def clear_checkpoint():
    """Delete checkpoint file to start fresh."""
    try:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
    except Exception as e:
        print(f"Warning: Could not clear checkpoint: {e}")


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


def fetch_entities_batch(batch_size: int = 1000, max_batches: int = None, resume: bool = False) -> list:
    """
    Fetch entities in batches with pagination.
    
    Args:
        batch_size: Number of entities per batch
        max_batches: Maximum number of batches (-1 for unlimited)
        resume: If True, resume from last checkpoint; if False, start from 0
        
    Returns:
        List of all entities
    """
    all_entities = []
    offset = 0
    batch_count = 0
    
    # Load checkpoint if resume is True
    if resume:
        checkpoint = load_checkpoint()
        if checkpoint:
            offset = checkpoint["offset"]
            batch_count = checkpoint["batch_count"]
            print(f"Resuming from checkpoint: offset={offset}, batch_count={batch_count}")
        else:
            print("No checkpoint found. Starting from 0.")
    else:
        # Clear checkpoint if not resuming
        clear_checkpoint()
    
    print(f"Fetching entities in batches (batch_size: {batch_size}, starting offset: {offset})...")
    
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
        
        # Save checkpoint after each batch
        save_checkpoint(offset + batch_size, batch_count + 1, len(all_entities))
        
        if len(batch_entities) < batch_size:
            break
        
        offset += batch_size
        batch_count += 1
        
        if max_batches and batch_count >= max_batches:
            break
    
    print(f"✓ Fetched {len(all_entities)} entities total")
    return all_entities
