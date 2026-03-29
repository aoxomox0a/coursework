"""
Linking Pipeline: Orchestrate entity and relation linking.
"""

from src.linking import entity_extraction, entity_linking, relation_linking, spacy_setup
from typing import List, Dict
import torch


def run_linking_pipeline(questions: List[str]) -> List[Dict]:
    print(f"Starting Linking Pipeline...")
    print(f"Question: {questions}\n")

    print("1. Loading spaCy model...")
    nlp = spacy_setup.load_spacy_model()
    result = []

    with torch.no_grad():
        for doc in nlp.pipe(questions, batch_size=8):
            # entities not used atm for some reason
            extracted_entities = entity_extraction.extract_entities(doc)
            noun_phrases = entity_extraction.extract_noun_phrases(doc)

            linking_results = entity_linking.link_entities(noun_phrases)
            entity_uris = entity_linking.disambiguate_entities(linking_results)

            relation_candidates = relation_linking.find_relation_candidates(
                doc.text, top_k=3
            )
            selected_relation = relation_linking.select_relation(relation_candidates)
            print(f"✓ Found {len(relation_candidates)} property candidates")
            if selected_relation:
                print(
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

    print("\n✓ Linking Pipeline Completed Successfully!")
    return result


if __name__ == "__main__":
    # run_linking_pipeline expects a single str, not a list
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
