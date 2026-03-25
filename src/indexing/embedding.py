"""Embedding Generation - Generate embeddings using sentence-transformers."""
from sentence_transformers import SentenceTransformer
from config.settings import EMBEDDING_MODEL


def load_embedding_model():
    """Load the sentence-transformers embedding model."""
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"✓ Embedding model loaded")
    return model


def embed_texts(texts: list, model=None) -> list:
    """
    Generate embeddings for a list of texts.
    
    Args:
        texts: List of text strings
        model: SentenceTransformer model (loads if None)
        
    Returns:
        List of embeddings (numpy arrays converted to lists)
    """
    if model is None:
        model = load_embedding_model()
    
    print(f"Generating embeddings for {len(texts)} texts...")
    embeddings = model.encode(texts, show_progress_bar=True)
    print(f"✓ Generated {len(embeddings)} embeddings")
    
    return embeddings.tolist()


def embed_entities(entities: list, model=None) -> list:
    """
    Generate embeddings for entity labels.
    
    Args:
        entities: List of dicts with 'uri' and 'label' keys
        model: SentenceTransformer model (loads if None)
        
    Returns:
        List of dicts with 'uri', 'label', and 'embedding' keys
    """
    if model is None:
        model = load_embedding_model()
    
    labels = [entity["label"] for entity in entities]
    embeddings = embed_texts(labels, model)
    
    embedded_entities = []
    for entity, embedding in zip(entities, embeddings):
        embedded_entities.append({
            "uri": entity["uri"],
            "label": entity["label"],
            "embedding": embedding
        })
    
    return embedded_entities
