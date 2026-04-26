"""
Endpoint introspection — probe a SPARQL endpoint for its label predicate,
typing conventions, and language-tag usage. Results are persisted as a
JSON sidecar so downstream stages (profile-from-index, linking) can read
a single source of truth instead of re-probing.
"""
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

from src.indexing.chroma_storage import get_endpoint_slug

logger = logging.getLogger(__name__)

# Ranked label predicates — the probe picks the one with the highest count.
LABEL_PREDICATES: tuple[str, ...] = (
    "http://www.w3.org/2000/01/rdf-schema#label",
    "http://www.w3.org/2004/02/skos/core#prefLabel",
    "http://xmlns.com/foaf/0.1/name",
    "http://purl.org/dc/terms/title",
    "http://schema.org/name",
)

# Ordered fallback chain for property typing.
PROPERTY_TYPINGS: tuple[str, ...] = (
    "rdf_property",
    "owl_object_property",
    "owl_datatype_property",
    "untyped_fallback",
)

CLASS_TYPINGS: tuple[str, ...] = (
    "rdfs_class",
    "owl_class",
    "untyped_fallback",
)

_PROPERTY_TYPE_URIS: dict[str, str] = {
    "rdf_property": "http://www.w3.org/1999/02/22-rdf-syntax-ns#Property",
    "owl_object_property": "http://www.w3.org/2002/07/owl#ObjectProperty",
    "owl_datatype_property": "http://www.w3.org/2002/07/owl#DatatypeProperty",
}

_CLASS_TYPE_URIS: dict[str, str] = {
    "rdfs_class": "http://www.w3.org/2000/01/rdf-schema#Class",
    "owl_class": "http://www.w3.org/2002/07/owl#Class",
}

# Runtime-mutable so tests can redirect the sidecar directory.
PROFILES_DIR: Path = Path("data/profiles")

QueryFn = Callable[[str, str | None], Awaitable[dict]]


@dataclass(frozen=True)
class DiscoveredProfile:
    endpoint_url: str
    slug: str
    label_predicate: str
    property_typing: str
    class_typing: str
    has_language_tags: bool
    probed_at: str


async def _default_query_fn(query: str, endpoint: str | None = None) -> dict:
    # Lazy import to keep discovery importable without the endpoint module
    # pulling in httpx/connection state at import time.
    from src.indexing.endpoint import query_sparql_custom

    if endpoint is None:
        return {}
    return await query_sparql_custom(query, endpoint)


async def _count(query_fn: QueryFn, endpoint: str, query: str) -> int:
    try:
        result = await query_fn(query, endpoint)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return 0
        return int(bindings[0].get("n", {}).get("value", "0"))
    except Exception as exc:
        logger.warning("probe COUNT query failed: %s", exc)
        return 0


async def _ask(query_fn: QueryFn, endpoint: str, query: str) -> bool:
    try:
        result = await query_fn(query, endpoint)
        return bool(result.get("boolean", False))
    except Exception as exc:
        logger.warning("probe ASK query failed: %s", exc)
        return False


async def probe_label_predicate(
    endpoint: str,
    query_fn: QueryFn | None = None,
) -> str:
    """Return the fully-qualified URI of the most-populated label predicate on this endpoint."""
    fn = query_fn or _default_query_fn
    best_uri = LABEL_PREDICATES[0]
    best_count = 0
    for uri in LABEL_PREDICATES:
        q = (
            "SELECT (COUNT(?s) AS ?n) WHERE { "
            f"{{ SELECT ?s WHERE {{ ?s <{uri}> ?o }} LIMIT 10000 }} "
            "}"
        )
        n = await _count(fn, endpoint, q)
        if n > best_count:
            best_count = n
            best_uri = uri
    return best_uri


async def probe_property_typing(
    endpoint: str,
    query_fn: QueryFn | None = None,
) -> str:
    """Return the first property-typing convention that has any instance on the endpoint."""
    fn = query_fn or _default_query_fn
    for typing in PROPERTY_TYPINGS:
        if typing == "untyped_fallback":
            continue
        type_uri = _PROPERTY_TYPE_URIS[typing]
        if await _ask(fn, endpoint, f"ASK {{ ?p a <{type_uri}> }}"):
            return typing
    return "untyped_fallback"


async def probe_class_typing(
    endpoint: str,
    query_fn: QueryFn | None = None,
) -> str:
    """Return the first class-typing convention that has any instance on the endpoint."""
    fn = query_fn or _default_query_fn
    for typing in CLASS_TYPINGS:
        if typing == "untyped_fallback":
            continue
        type_uri = _CLASS_TYPE_URIS[typing]
        if await _ask(fn, endpoint, f"ASK {{ ?c a <{type_uri}> }}"):
            return typing
    return "untyped_fallback"


async def probe_has_language_tags(
    endpoint: str,
    label_predicate: str,
    query_fn: QueryFn | None = None,
) -> bool:
    """Return True if any label under this predicate carries an @en language tag."""
    fn = query_fn or _default_query_fn
    q = f'ASK {{ ?s <{label_predicate}> ?l FILTER(lang(?l) = "en") }}'
    return await _ask(fn, endpoint, q)


async def discover_profile(
    endpoint: str,
    query_fn: QueryFn | None = None,
) -> DiscoveredProfile:
    """Run all probes and return a snapshot of the endpoint's conventions."""
    label = await probe_label_predicate(endpoint, query_fn)
    prop_typing = await probe_property_typing(endpoint, query_fn)
    class_typing = await probe_class_typing(endpoint, query_fn)
    has_lang = await probe_has_language_tags(endpoint, label, query_fn)
    return DiscoveredProfile(
        endpoint_url=endpoint,
        slug=get_endpoint_slug(endpoint),
        label_predicate=label,
        property_typing=prop_typing,
        class_typing=class_typing,
        has_language_tags=has_lang,
        probed_at=datetime.now(tz=timezone.utc).isoformat(),
    )


def property_type_uri_for(typing: str) -> str | None:
    """Translate a property-typing slug to its URI; None for the untyped fallback."""
    return _PROPERTY_TYPE_URIS.get(typing)


def class_type_uri_for(typing: str) -> str | None:
    """Translate a class-typing slug to its URI; None for the untyped fallback."""
    return _CLASS_TYPE_URIS.get(typing)


def profile_path_for(endpoint: str) -> Path:
    """Filesystem path for the persisted sidecar of this endpoint."""
    return PROFILES_DIR / f"{get_endpoint_slug(endpoint)}.json"


def save_profile(profile: DiscoveredProfile) -> None:
    """Persist the profile to its sidecar path, creating parent dirs as needed."""
    path = profile_path_for(profile.endpoint_url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(profile), indent=2))


def load_profile(endpoint: str) -> DiscoveredProfile | None:
    """Load the persisted sidecar for this endpoint, or None if absent."""
    path = profile_path_for(endpoint)
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    return DiscoveredProfile(**raw)
