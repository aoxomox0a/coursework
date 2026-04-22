"""Knowledge-graph profiles — endpoint-specific prompt prefixes, one-shot examples, and linking strategy."""
from src.kg_profiles.base import KGProfile, OneShotExample
from src.kg_profiles.introspection import (
    derive_prefixes_from_uris,
    namespace_of,
    profile_from_index,
)

__all__ = [
    "KGProfile",
    "OneShotExample",
    "derive_prefixes_from_uris",
    "namespace_of",
    "profile_from_index",
]
