"""Funnel stage 1 — SPARQL syntax validity via rdflib's parser."""
from dataclasses import dataclass

from src.sparql.validation import is_valid_sparql


@dataclass(frozen=True)
class SyntaxResult:
    valid: bool
    error: str


def evaluate_syntax(query: str) -> SyntaxResult:
    """Return a SyntaxResult capturing whether ``query`` parses with rdflib."""
    valid, error = is_valid_sparql(query)
    return SyntaxResult(valid=valid, error=error)
