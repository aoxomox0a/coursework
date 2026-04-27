"""Funnel stage 4 — Algebra Match between gold and generated SPARQL queries.

Pragmatic, corroborative metric (NOT a gating signal — Execution Match remains
primary). The canonicalisation done here covers:

  - alpha-equivalence: variables (and blank nodes) are renumbered ``?v0, ?v1, …``
    in BFS order so two queries that differ only in variable names compare equal.
  - BGP triple ordering: triples inside a Basic Graph Pattern are sorted by their
    canonical (subject, predicate, object) tuple.
  - SPARQL prefix expansion: handled for free by ``rdflib.prepareQuery`` —
    ``rdf:type`` and ``<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>``
    canonicalise identically.

What we deliberately DO NOT canonicalise (out of scope for ORKG, where
Execution Match is the primary signal):

  - commutative operand reordering for Join/Union beyond what's encoded
    in BGP triple sorting (full operator-level reordering needs a fixpoint
    rewrite that is its own ~200 LOC project, planner Section 4).
  - filter expression normalisation (constant folding, commutative-op sorting).
  - property-path equivalences (``foaf:knows/foaf:knows`` vs explicit join).
  - aggregate equivalences (``COUNT(DISTINCT ?x)`` in different positions).

When the canonicaliser hits a node shape it doesn't know how to process,
the result reports ``PARSE_LIMITATION`` rather than crashing — the funnel
report can then break those out separately.
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from rdflib import BNode, Literal, URIRef, Variable
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parserutils import CompValue

logger = logging.getLogger(__name__)


class AlgebraMatchStatus(str, Enum):
    COMPARED = "compared"
    GOLD_PARSE_ERROR = "gold_parse_error"
    GENERATED_PARSE_ERROR = "generated_parse_error"
    PARSE_LIMITATION = "parse_limitation"


@dataclass(frozen=True)
class AlgebraMatchResult:
    match: bool
    status: AlgebraMatchStatus
    error: str
    reason: str


# Internal node-tag wrappers — strings keep the canonical form hashable for
# direct equality, and tag prefixes keep different terminal types disjoint.
def _term(node: Any, var_map: dict) -> tuple:
    """Canonicalise an RDF term (Variable, URIRef, Literal, BNode)."""
    if isinstance(node, Variable):
        if node not in var_map:
            var_map[node] = f"?v{len(var_map)}"
        return ("Var", var_map[node])
    if isinstance(node, URIRef):
        return ("URI", str(node))
    if isinstance(node, Literal):
        return (
            "Lit",
            str(node),
            str(node.datatype) if node.datatype is not None else "",
            node.language or "",
        )
    if isinstance(node, BNode):
        # Treat blank nodes like existential variables — alpha-renamed too.
        if node not in var_map:
            var_map[node] = f"?b{len(var_map)}"
        return ("BNode", var_map[node])
    return ("RawTerm", str(node))


def _canonicalise(node: Any, var_map: dict) -> Any:
    """Recursively canonicalise an algebra node (CompValue, list, or term)."""
    if isinstance(node, (Variable, URIRef, Literal, BNode)):
        return _term(node, var_map)

    if isinstance(node, CompValue):
        name = node.name
        # BGP gets special treatment: sort the triple list.
        if name == "BGP":
            triples = list(node.get("triples", []))
            normalised = [
                tuple(_canonicalise(part, var_map) for part in triple)
                for triple in triples
            ]
            normalised.sort()
            return ("BGP", tuple(normalised))

        # Generic case: walk the keys deterministically.
        children = []
        for key in sorted(node.keys()):
            if key.startswith("_"):  # internal bookkeeping, not part of the algebra
                continue
            children.append((key, _canonicalise(node[key], var_map)))
        return (name, tuple(children))

    if isinstance(node, (list, tuple)):
        return tuple(_canonicalise(item, var_map) for item in node)

    if isinstance(node, dict):
        items = sorted(node.items(), key=lambda kv: str(kv[0]))
        return tuple((str(k), _canonicalise(v, var_map)) for k, v in items)

    # Fall-through: stringify (covers ints, query forms, etc.).
    return ("Raw", str(node))


def _normalize_query(query: str) -> Any:
    """Parse + extract algebra + canonicalise. Each call gets a fresh var_map
    so two queries are renumbered independently, which is the desired behaviour
    for cross-query comparison (each side gets ?v0, ?v1, … in its own walk order).
    """
    algebra = prepareQuery(query).algebra
    var_map: dict = {}
    return _canonicalise(algebra, var_map)


def evaluate_algebra_match(gold_query: str, generated_query: str) -> AlgebraMatchResult:
    """Compare gold and generated queries at the algebra level.

    Parse errors on either side surface as a non-COMPARED status so the
    reporter can deprioritise those cases without conflating them with
    real structural divergence.
    """
    try:
        gold_canon = _normalize_query(gold_query)
    except Exception as exc:
        logger.debug("gold parse error: %s", exc)
        return AlgebraMatchResult(
            match=False,
            status=AlgebraMatchStatus.GOLD_PARSE_ERROR,
            error=str(exc),
            reason="gold query failed to parse",
        )

    try:
        gen_canon = _normalize_query(generated_query)
    except Exception as exc:
        logger.debug("generated parse error: %s", exc)
        return AlgebraMatchResult(
            match=False,
            status=AlgebraMatchStatus.GENERATED_PARSE_ERROR,
            error=str(exc),
            reason="generated query failed to parse",
        )

    if gold_canon == gen_canon:
        return AlgebraMatchResult(
            match=True,
            status=AlgebraMatchStatus.COMPARED,
            error="",
            reason="",
        )
    return AlgebraMatchResult(
        match=False,
        status=AlgebraMatchStatus.COMPARED,
        error="",
        reason="canonical algebra trees differ",
    )
