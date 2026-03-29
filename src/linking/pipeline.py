"""
Linking Pipeline: Orchestrate entity and relation linking.
"""

from src.linking import entity_extraction, entity_linking, relation_linking, spacy_setup
from typing import List


def run_linking_pipeline(question: str):
    # 1. Setup spaCy
    # 2. Extract entities and noun phrases
    # 3. Link entities to URIs
    # 4. Link relations to properties

    print(f"Starting Linking Pipeline...")
    print(f"Question: {question}\n")

    # Step 1: Setup spaCy
    print("1. Loading spaCy model...")
    nlp = spacy_setup.load_spacy_model()
    print("✓ spaCy loaded")

    # Step 2: Extract entities — wrap in list for spaCy batch API, then flatten
    print("\n2. Extracting entities and noun phrases...")
    extracted_entities_batch = entity_extraction.extract_entities([question], nlp)
    noun_phrases_batch = entity_extraction.extract_noun_phrases([question], nlp)

    flat_entities = [ent for doc_ents in extracted_entities_batch for ent in doc_ents]
    flat_noun_phrases = noun_phrases_batch[0] if noun_phrases_batch else []

    print(f"✓ Extracted {len(flat_entities)} named entities and {len(flat_noun_phrases)} noun phrases")
    print(f"  Named entities: {flat_entities}")
    print(f"  Noun phrases: {flat_noun_phrases}")

    # Step 3: Link entities
    print("\n3. Linking entities to URIs...")
    linking_results = entity_linking.link_entities(flat_noun_phrases)
    entity_uris = entity_linking.disambiguate_entities(linking_results)
    print(f"✓ Linked {len(entity_uris)} entities")
    for item in entity_uris:
        print(f"  {item['entity']} -> {item['uri']} (confidence: {item['confidence']:.2f})")

    # Step 4: Link relations
    print("\n4. Finding relation candidates...")
    relation_candidates = relation_linking.find_relation_candidates(question, top_k=3)
    selected_relation = relation_linking.select_relation(relation_candidates)
    print(f"✓ Found {len(relation_candidates)} property candidates")
    if selected_relation:
        print(f"  Selected: {selected_relation['label']} ({selected_relation['uri']})")

    result = {
        "question": question,
        "entities": entity_uris,
        "relation": selected_relation,
        "relation_candidates": relation_candidates,
    }

    print("\n✓ Linking Pipeline Completed Successfully!")
    return result


if __name__ == "__main__":
    # run_linking_pipeline expects a single str, not a list
    test_question = "Who directed the movie Inception released in 2010?"
    # test_question = "Who is the author of The Great Gatsby?"
    result = run_linking_pipeline(test_question)
