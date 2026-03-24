"""
SPARQL Pipeline: Orchestrate SPARQL generation and execution.
"""
from src.sparql import prompt, llm, validation, execution


def run_sparql_pipeline(question: str, linking_result: dict) -> str:
    """
    Execute the complete SPARQL generation & execution pipeline:
    1. Generate LLM prompt
    2. Call LLM to generate SPARQL
    3. Validate syntax
    4. Retry if invalid (fix attempt)
    5. Execute query
    6. Format results

    Args:
        question: Original natural language question
        linking_result: Output from linking pipeline

    Returns:
        Final answer string
    """
    print("Starting SPARQL Pipeline...\n")

    entities = linking_result.get("entities", [])
    relation = linking_result.get("relation", {})
    relation_candidates = linking_result.get("relation_candidates", [])

    entity_uris = [e.get("uri") for e in entities if e.get("uri")]
    property_uri = relation.get("uri", "")

    # Step 1: Generate prompt
    print("1. Generating LLM prompt...")
    sparql_prompt = prompt.generate_sparql_prompt(
        question=question,
        entity_uris=entity_uris,
        property_uri=property_uri,
        related_properties=relation_candidates
    )
    print("✓ Prompt generated")

    # Step 2: Call LLM
    print("\n2. Calling LLM to generate SPARQL query...")
    generated_query = llm.call_llm(sparql_prompt)
    generated_query = llm.extract_sparql_from_response(generated_query)
    print(f"✓ Generated query:\n{generated_query}\n")

    # Step 3: Validate syntax
    print("3. Validating SPARQL syntax...")
    is_valid, error_msg = validation.is_valid_sparql(generated_query)

    if not is_valid:
        print(f"✗ Syntax error: {error_msg}")

        # Step 4: Retry with fix prompt
        print("\n4. Attempting to fix query...")
        fix_prompt = prompt.generate_fix_sparql_prompt(question, generated_query, error_msg)
        fixed_query = llm.call_llm(fix_prompt)
        fixed_query = llm.extract_sparql_from_response(fixed_query)
        print(f"✓ Fixed query:\n{fixed_query}\n")

        is_valid, error_msg = validation.is_valid_sparql(fixed_query)
        if not is_valid:
            print(f"✗ Still invalid: {error_msg}")
            return f"Failed to generate valid SPARQL query. Last error: {error_msg}"

        generated_query = fixed_query

    print("✓ Query is valid")

    # Step 5: Execute query
    print("\n5. Executing query on endpoint...")
    answer = execution.execute_and_format(generated_query)
    print("✓ Query executed")

    print("\n6. Final Answer:")
    print(answer)

    print("\n✓ SPARQL Pipeline Completed Successfully!")
    return answer


if __name__ == "__main__":
    # Example usage
    test_question = "Who is the author of The Great Gatsby?"
    test_linking_result = {
        "question": test_question,
        "entities": [{"uri": "http://example.com/TheGreatGatsby", "confidence": 0.95}],
        "relation": {"uri": "http://example.com/hasAuthor", "label": "hasAuthor"},
        "relation_candidates": []
    }

    answer = run_sparql_pipeline(test_question, test_linking_result)
