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

# craete global client with connnection pooling enabled
http_client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
)


async def call_llm(prompt: str, model: str | None = None) -> str:
    """
    Call Hactar LLM via OpenAI-compatible /chat/completions endpoint.

    Args:
        prompt: The prompt to send to the LLM
        model: Optional model name override. When None, uses LLM_MODEL from
            settings. Hactar exposes multiple models behind the same endpoint
            (Ollama-style); passing a different model name routes to it without
            needing a second client or auth.

    Returns:
        Raw generated text from the LLM, or empty string on failure
    """
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model if model is not None else LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    try:
        # use global client
        response = await http_client.post(
            f"{LLM_ENDPOINT}/chat/completions",
            headers=headers,
            json=payload,
            timeout=300,
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
    # Extract a SPARQL query from LLM response text.
    # returns extracted SPARQL query string, or empty string if none found
    if not response_text:
        return ""

    # regex extraction from fenced code blocl
    match = _SPARQL_FENCE_RE.search(response_text)
    if match:
        return match.group(1).replace("```", "").strip()

    # keyword scan fallback
    kw_match = _SPARQL_KEYWORD_RE.search(response_text)
    if kw_match:
        extracted = response_text[kw_match.start() :].strip()
        return extracted.replace("```", "").strip()

    return ""
