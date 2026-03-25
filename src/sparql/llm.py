"""
Call LLM for SPARQL generation.
"""
import requests
from config.settings import LLM_ENDPOINT, LLM_API_KEY, LLM_MODEL


def call_llm(prompt: str) -> str:
    """
    Call external LLM (HuggingFace, Replicate, or custom endpoint).

    Args:
        prompt: The prompt to send to LLM

    Returns:
        Generated SPARQL query string
    """
    try:
        # Example for HuggingFace Inference API
        headers = {"Authorization": f"Bearer {LLM_API_KEY}"}

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 500,
                "temperature": 0.1,  # Low temperature for deterministic output
            }
        }

        response = requests.post(
            LLM_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            # Extract generated text (format varies by provider)
            generated = result[0].get("generated_text", "")
            # Remove prompt from response
            sparql_query = generated.replace(prompt, "").strip()
            return sparql_query
        else:
            print(f"LLM Error: {response.status_code}")
            return ""

    except Exception as e:
        print(f"Error calling LLM: {e}")
        return ""


def extract_sparql_from_response(response_text: str) -> str:
    """
    Extract SPARQL query from LLM response.
    Handles cases where LLM returns extra text.

    Args:
        response_text: Raw response from LLM

    Returns:
        Extracted SPARQL query
    """
    # Look for SELECT, CONSTRUCT, ASK, DESCRIBE keywords
    lines = response_text.split("\n")
    sparql_lines = []
    in_query = False

    for line in lines:
        upper_line = line.upper().strip()
        if upper_line.startswith(("SELECT", "CONSTRUCT", "ASK", "DESCRIBE", "PREFIX")):
            in_query = True

        if in_query:
            sparql_lines.append(line)

    return "\n".join(sparql_lines)
