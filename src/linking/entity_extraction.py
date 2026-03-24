"""
Extract entities from natural language questions using spaCy.
"""
from typing import List, Tuple
from src.linking.spacy_setup import load_spacy_model


def extract_entities(question: str, nlp=None) -> List[Tuple[str, str]]:
    """
    Extract named entities from a question.

    Args:
        question: Natural language question
        nlp: spaCy Language object (loads default if None)

    Returns:
        List of tuples: (entity_text, entity_label)
    """
    if nlp is None:
        nlp = load_spacy_model()

    doc = nlp(question)
    entities = [(ent.text, ent.label_) for ent in doc.ents]

    return entities


def extract_noun_phrases(question: str, nlp=None) -> List[str]:
    """
    Extract noun phrases which are good candidates for entity linking.

    Args:
        question: Natural language question
        nlp: spaCy Language object (loads default if None)

    Returns:
        List of noun phrase strings
    """
    if nlp is None:
        nlp = load_spacy_model()

    doc = nlp(question)
    noun_phrases = [chunk.text for chunk in doc.noun_chunks]

    return noun_phrases
