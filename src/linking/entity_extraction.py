"""
Extract entities from natural language questions using spaCy.
"""

from typing import List, Tuple
from src.linking.spacy_setup import load_spacy_model
import torch

# torch.set_num_threads(8)


def extract_entities(question: List[str], nlp=None) -> List[Tuple[str, str]]:
    # Extract named entities from a question.

    if nlp is None:
        nlp = load_spacy_model()

    # disable gradient calculation
    with torch.no_grad():
        docs = list(nlp.pipe(question, batch_size=8))

    all_entities = []
    for doc in docs:
        entities = [
            (ent.text, ent.label_) for ent in doc.ents
        ]  # rely on spacy's default entity recognition
        all_entities.append(entities)

    return all_entities


def extract_noun_phrases(questions: List[str], nlp=None) -> List[List[str]]:
    """
    Extract property/relation candidates for a batch of questions.
    Returns a list of lists, maintaining the exact index mapping to the input questions.
    """
    if nlp is None:
        nlp = load_spacy_model()

    with torch.no_grad():
        doc_stream = nlp.pipe(questions)

    all_candidates = []

    for doc in doc_stream:
        entity_tokens = set()
        for ent in doc.ents:
            for token in ent:
                entity_tokens.add(token.text)

        # 2. Reset the temporary list for THIS specific document only
        valid_candidates = []

        for token in doc:
            if token.text in entity_tokens:
                continue
            if token.pos_ in ["PRON", "AUX"]:
                continue
            if token.pos_ in ["NOUN", "VERB"]:
                word = token.lemma_ if token.pos_ == "VERB" else token.text
                valid_candidates.append(word)

        # 3. Deduplicate this document's candidates and append to the master list
        unique_candidates = list(dict.fromkeys(valid_candidates))
        all_candidates.append(unique_candidates)

    # 4. Return the master list
    return all_candidates
