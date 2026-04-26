"""Frozen dataclasses describing a knowledge-graph profile and its one-shot examples."""
from dataclasses import dataclass, field
from typing import Literal

LinkStrategy = Literal["ner", "noun_chunks"]


@dataclass(frozen=True)
class OneShotExample:
    """A curated question / SPARQL pair shown as a few-shot anchor to the generator LLM."""

    question: str
    entity_uris: tuple[str, ...]
    property_uri: str | None
    sparql: str
    tags: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class KGProfile:
    """Endpoint-specific configuration for prompt assembly and the linking strategy."""

    slug: str
    label: str
    endpoint_url: str
    prefixes: tuple[tuple[str, str], ...]
    one_shot_examples: tuple[OneShotExample, ...]
    label_predicate: str = "rdfs:label"
    link_strategy: LinkStrategy = "ner"
    query_style_hints: tuple[str, ...] = ()
