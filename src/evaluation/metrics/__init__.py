"""Funnel metrics for SPARQL query evaluation.

The funnel runs in this order; each stage gates the next:
  1. syntax        — query parses with rdflib
  2. executable    — endpoint accepts and returns a result (any bindings, even empty)
  3. execution_match — generated bindings match gold bindings (set equality, var-name independent)
  4. algebra       — corroborative structural match (Task #3 part 2)
"""
from src.evaluation.metrics.algebra import (
    AlgebraMatchResult,
    AlgebraMatchStatus,
    evaluate_algebra_match,
)
from src.evaluation.metrics.executable import (
    ExecutableResult,
    ExecutableStatus,
    evaluate_executable,
)
from src.evaluation.metrics.execution_match import (
    ExecutionMatchResult,
    evaluate_execution_match,
)
from src.evaluation.metrics.syntax import SyntaxResult, evaluate_syntax

__all__ = [
    "SyntaxResult",
    "evaluate_syntax",
    "ExecutableResult",
    "ExecutableStatus",
    "evaluate_executable",
    "ExecutionMatchResult",
    "evaluate_execution_match",
    "AlgebraMatchResult",
    "AlgebraMatchStatus",
    "evaluate_algebra_match",
]
