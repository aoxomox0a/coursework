"""
Call LLM for SPARQL generation via Hactar (OpenAI-compatible /chat/completions endpoint).
"""

import logging
import re

import httpx

from config.settings import LLM_API_KEY, LLM_ENDPOINT, LLM_MODEL

logger = logging.getLogger(__name__)

_SPARQL_FENCE_RE = re.compile(r"```(?:sparql)?\s*\n?(.*?)```", re.DOTALL)
_SPARQL_KEYWORD_RE = re.compile(
    r"\b(PREFIX|SELECT|CONSTRUCT|ASK|DESCRIBE)\b", re.IGNORECASE
)


async def call_llm(prompt: str) -> str:
    """
    Call Hactar LLM via OpenAI-compatible /chat/completions endpoint.

    Args:
        prompt: The prompt to send to the LLM

    Returns:
        Raw generated text from the LLM, or empty string on failure
    """
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{LLM_ENDPOINT}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )

            if response.status_code == 200:
                try:
                    return response.json()["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as exc:
                    logger.error(
                        "Unexpected LLM response shape: %s — body: %.200s",
                        exc,
                        response.text,
                    )
                    return ""

            logger.error(
                "LLM returned status %d: %s", response.status_code, response.text[:200]
            )
            return ""

        except httpx.TimeoutException:
            logger.error("LLM request timed out")
            return ""
        except httpx.RequestError as exc:
            logger.error("LLM HTTP error: %s", exc)
            return ""
        except Exception as exc:
            logger.error("Unexpected error calling LLM: %s", exc)
            return ""


def extract_sparql_from_response(response_text: str) -> str:
    """
    Extract a SPARQL query from LLM response text.

    Tries two strategies in order:
    1. Regex extraction from ```sparql ... ``` or ``` ... ``` fences.
    2. Fallback: keyword scan from first PREFIX/SELECT/CONSTRUCT/ASK/DESCRIBE line.

    Args:
        response_text: Raw text returned by the LLM

    Returns:
        Extracted SPARQL query string, or empty string if none found
    """
    if not response_text:
        return ""

    # Strategy 1: fenced code block
    match = _SPARQL_FENCE_RE.search(response_text)
    if match:
        return match.group(1).strip()

    # Strategy 2: keyword scan fallback
    kw_match = _SPARQL_KEYWORD_RE.search(response_text)
    if kw_match:
        return response_text[kw_match.start() :].strip()

    return ""
