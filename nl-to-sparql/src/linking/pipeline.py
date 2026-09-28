"""
Linking Pipeline: Orchestrate entity and relation linking.
"""

from config.settings import SPARQL_ENDPOINT
from src.linking import entity_extraction, entity_linking, relation_linking, spacy_setup
from typing import List, Dict
import torch
import logging

# Initialize the logger for this specific module
logger = logging.getLogger(__name__)


def run_linking_pipeline(questions: List[str], endpoint: str = None) -> List[Dict]:
    if endpoint is None:
        from config.settings import SPARQL_ENDPOINT
        endpoint = SPARQL_ENDPOINT
    
    logger.debug("Starting Linking Pipeline...")
    logger.debug(f"Question: {questions}")

    # pass string into list is single string
    if isinstance(questions, str):
        questions = [questions]

    logger.debug("1. Loading spaCy model...")
    nlp = spacy_setup.load_spacy_model()
    result = []

    with torch.no_grad():
        for doc in nlp.pipe(questions, batch_size=8):
            # Union NER + noun phrases + noun chunks for endpoint-agnostic coverage.
            # ADR 0001 showed noun chunks give 100% coverage on ORKG-domain questions
            # where NER alone covers only 60%.
            extracted_entities = entity_extraction.extract_entities(doc)
            noun_phrases = entity_extraction.extract_noun_phrases(doc)
            noun_chunks = entity_extraction.extract_noun_chunks(doc)

            entity_strings = entity_extraction.combine_candidates(
                extracted_entities, noun_phrases, noun_chunks
            )
            linking_results = entity_linking.link_entities(
                entity_strings, endpoint=endpoint
            )
            entity_uris = entity_linking.disambiguate_entities(linking_results)

            # top_k=10 gives the SPARQL prompt downstream more lexical breadth:
            # under hybrid retrieval, terse-label predicates (HAS_DATASET /
            # HAS_BENCHMARK / …) often surface at rank 5-9, so a tight top-3
            # would drop them again.
            relation_candidates = relation_linking.find_relation_candidates(
                doc.text, top_k=10, endpoint=endpoint
            )
            selected_relation = relation_linking.select_relation(relation_candidates)
            logger.debug(f"✓ Found {len(relation_candidates)} property candidates")
            if selected_relation:
                logger.debug(
                    f"  Selected: {selected_relation['label']} ({selected_relation['uri']})"
                )

            result.append(
                {
                    "question": doc.text,
                    "entities": entity_uris,
                    "relation": selected_relation,
                    "relation_candidates": relation_candidates,
                }
            )

    logger.debug("✓ Linking Pipeline Completed Successfully!")
    return result


if __name__ == "__main__":
    # run_linking_pipeline expects a single str, not a list
    # Because we run this directly, let's turn debug logs on just for testing
    logging.basicConfig(level=logging.DEBUG)

    test_questions = [
        "Who directed the movie Inception released in 2010?",
        "Who directed Inception?",
        "Who wrote The Great Gatsby?",
        "What is the capital of France?",
        "When was Barack Obama born?",
        "Where is the Eiffel Tower located?",
    ]
    # test_question = "Who is the author of The Great Gatsby?"
    result = run_linking_pipeline(test_questions)

