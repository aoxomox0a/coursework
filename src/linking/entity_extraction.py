"""
Extract entities from natural language questions using spaCy.
"""

from typing import List, Tuple


def extract_entities(doc) -> List[Tuple[str, str]]:
    return [(ent.text, ent.label_) for ent in doc.ents]


def extract_noun_phrases(doc) -> List[str]:
    """
    Extracts relation candidates for a single spaCy Doc. Returns a flat list of strings.
    """

    entity_tokens = {token.text for ent in doc.ents for token in ent}

    # 2. Reset the temporary list for THIS specific document only
    valid_candidates = []

    for token in doc:
        if token.text in entity_tokens or token.pos_ in ["PRON", "AUX"]:
            continue
        if token.pos_ in ["NOUN", "VERB"]:
            word = token.lemma_ if token.pos_ == "VERB" else token.text
            valid_candidates.append(word)

    return list(dict.fromkeys(valid_candidates))


def extract_noun_chunks(doc) -> List[str]:
    """
    Return spaCy noun-chunk spans as raw text (e.g. 'the GAD dataset').

    Complements extract_noun_phrases (token-level) with multi-word spans —
    the ORKG-domain empirical check (ADR 0001) showed 100% coverage with
    chunks where NER alone only covered 60%.
    """
    return [chunk.text for chunk in doc.noun_chunks]


def combine_candidates(
    entities: List[Tuple[str, str]],
    noun_phrases: List[str],
    noun_chunks: List[str] | None = None,
) -> List[str]:
    """
    Union candidate surface forms from NER, noun phrases, and noun chunks.
    Deduplicates while preserving first-occurrence order so NER signals stay
    highest-priority when the linker consumes this list.
    """
    combined = [e[0] for e in entities] + list(noun_phrases) + list(noun_chunks or [])
    return list(dict.fromkeys(combined))
