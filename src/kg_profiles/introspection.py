"""
Derive a KGProfile from the indexed state of a SPARQL endpoint.

Step D of the evaluation-framework refactor. Rather than registering profiles
by slug with hardcoded prefixes and one-shots, the profile is now DERIVED from:
  1. The persisted discovery sidecar (written by src/indexing/discovery.py at
     indexing time): label predicate, property/class typing, language tags.
  2. The actual URIs present in the endpoint-scoped ChromaDB collections
     (properties, classes): their namespace roots become the prefix aliases.

One-shot examples are left empty here — synthetic one-shots are Step E's job.
"""
from typing import Iterable

from src.indexing.chroma_storage import get_chroma_client, get_collection_name
from src.indexing.discovery import load_profile as _load_discovery_profile
from src.kg_profiles.base import KGProfile
from src.kg_profiles.curated import load_curated_one_shots

# Stable alias -> namespace table for widely used vocabularies. When a URI
# namespace matches one of these, the alias is used verbatim instead of a
# generated ns0/ns1 placeholder.
WELL_KNOWN_PREFIXES: dict[str, str] = {
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "schema": "http://schema.org/",
    "dbo": "http://dbpedia.org/ontology/",
    "dbr": "http://dbpedia.org/resource/",
    "dbp": "http://dbpedia.org/property/",
    "orkgr": "http://orkg.org/orkg/resource/",
    "orkgp": "http://orkg.org/orkg/predicate/",
    "orkgc": "http://orkg.org/orkg/class/",
    "wd": "http://www.wikidata.org/entity/",
    "wdt": "http://www.wikidata.org/prop/direct/",
}

_NAMESPACE_TO_ALIAS: dict[str, str] = {ns: alias for alias, ns in WELL_KNOWN_PREFIXES.items()}


def namespace_of(uri: str) -> str:
    """Return a URI's namespace prefix — up to and including the final '#' or '/'."""
    if "#" in uri:
        return uri.rsplit("#", 1)[0] + "#"
    if "/" in uri:
        return uri.rsplit("/", 1)[0] + "/"
    return uri


def derive_prefixes_from_uris(uris: Iterable[str]) -> tuple[tuple[str, str], ...]:
    """Discover unique namespaces in ``uris`` and emit (alias, namespace) tuples.

    Well-known namespaces get their conventional alias (rdfs, dbo, orkgp, ...);
    anything else gets a generated ``ns0``, ``ns1``, ... aliased by first-
    occurrence order so the resulting tuple is stable across runs given the
    same input ordering.
    """
    seen_namespaces: list[str] = []
    for uri in uris:
        if not uri:
            continue
        ns = namespace_of(uri)
        if ns and ns not in seen_namespaces:
            seen_namespaces.append(ns)

    prefixes: list[tuple[str, str]] = []
    numeric_counter = 0
    for ns in seen_namespaces:
        alias = _NAMESPACE_TO_ALIAS.get(ns)
        if alias is None:
            alias = f"ns{numeric_counter}"
            numeric_counter += 1
        prefixes.append((alias, ns))
    return tuple(prefixes)


def _to_short_form(uri: str, prefixes: tuple[tuple[str, str], ...]) -> str:
    """Render ``uri`` as ``alias:local`` if its namespace is in ``prefixes``, else verbatim."""
    for alias, ns in prefixes:
        if uri.startswith(ns):
            return f"{alias}:{uri[len(ns):]}"
    return uri


def _fetch_uris_from_chroma(collection_name: str, endpoint: str) -> list[str]:
    """Read all distinct URIs present in an endpoint-scoped ChromaDB collection."""
    try:
        client = get_chroma_client()
        scoped = get_collection_name(collection_name, endpoint)
        collection = client.get_collection(name=scoped)
        data = collection.get()
    except Exception:
        return []
    return [m.get("uri", "") for m in (data.get("metadatas") or []) if m.get("uri")]


def profile_from_index(endpoint: str) -> KGProfile:
    """Build a KGProfile for ``endpoint`` from its discovery sidecar + indexed URIs.

    Raises:
        FileNotFoundError: if the discovery sidecar for this endpoint is
            absent (meaning indexing has not been run yet).
    """
    discovered = _load_discovery_profile(endpoint)
    if discovered is None:
        from src.indexing.discovery import profile_path_for

        raise FileNotFoundError(
            f"No discovery sidecar at {profile_path_for(endpoint)} — "
            "run the indexing pipeline before deriving a profile."
        )

    property_uris = _fetch_uris_from_chroma("properties", endpoint)
    class_uris = _fetch_uris_from_chroma("classes", endpoint)

    combined = list(property_uris) + list(class_uris) + [discovered.label_predicate]
    prefixes = derive_prefixes_from_uris(combined)
    short_label_predicate = _to_short_form(discovered.label_predicate, prefixes)

    return KGProfile(
        slug=discovered.slug,
        label=discovered.slug.replace("_", " ").title(),
        endpoint_url=discovered.endpoint_url,
        prefixes=prefixes,
        one_shot_examples=load_curated_one_shots(discovered.slug),
        label_predicate=short_label_predicate,
    )
