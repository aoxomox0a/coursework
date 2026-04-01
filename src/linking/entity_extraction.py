"""
Extract entities from natural language questions using spaCy.
"""

from typing import List, Tuple
import spacy


def extract_entities(doc: spacy.tokens.Doc) -> List[Tuple[str, str]]:
    return [(ent.text, ent.label_) for ent in doc.ents]


def extract_noun_phrases(doc: spacy.tokens.Doc) -> List[str]:
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
