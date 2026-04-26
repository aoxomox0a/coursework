"""Tests for the profile-driven path of generate_sparql_prompt.

Existing tests in test_prompt.py cover the profile=None (backward-compat) path.
These new tests cover the profile= path end-to-end.
"""
from src.kg_profiles import KGProfile, OneShotExample
from src.sparql.prompt import generate_sparql_prompt


def _orkg_profile() -> KGProfile:
    return KGProfile(
        slug="orkg",
        label="ORKG",
        endpoint_url="https://orkg.org/triplestore",
        prefixes=(
            ("orkgr", "http://orkg.org/orkg/resource/"),
            ("orkgp", "http://orkg.org/orkg/predicate/"),
            ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
        ),
        one_shot_examples=(
            OneShotExample(
                question="What is the research field of paper X?",
                entity_uris=("http://orkg.org/orkg/resource/R123",),
                property_uri="http://orkg.org/orkg/predicate/P30",
                sparql="SELECT ?f WHERE { orkgr:R123 orkgp:P30 ?f }",
            ),
        ),
        query_style_hints=(
            "ORKG predicates are opaque IDs — dereference labels via rdfs:label.",
        ),
    )


def test_profile_prefixes_rendered_as_prefix_declarations():
    p = generate_sparql_prompt(
        "q",
        ["http://orkg.org/orkg/resource/X"],
        "http://orkg.org/orkg/predicate/P",
        profile=_orkg_profile(),
    )
    assert "PREFIX orkgr: <http://orkg.org/orkg/resource/>" in p
    assert "PREFIX orkgp: <http://orkg.org/orkg/predicate/>" in p
    assert "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>" in p


def test_profile_one_shot_injected_verbatim():
    p = generate_sparql_prompt(
        "q",
        ["http://orkg.org/orkg/resource/X"],
        "http://orkg.org/orkg/predicate/P",
        profile=_orkg_profile(),
    )
    assert "What is the research field of paper X?" in p
    assert "SELECT ?f WHERE { orkgr:R123 orkgp:P30 ?f }" in p


def test_profile_style_hints_appear_in_prompt():
    p = generate_sparql_prompt(
        "q",
        ["http://orkg.org/orkg/resource/X"],
        "http://orkg.org/orkg/predicate/P",
        profile=_orkg_profile(),
    )
    assert "ORKG predicates are opaque IDs" in p


def test_profile_drops_legacy_dbpedia_one_shot():
    # The ORKG profile must NOT carry the DBpedia France example that lives in
    # the legacy fallback — otherwise the LLM sees contradictory examples.
    p = generate_sparql_prompt(
        "q",
        ["http://orkg.org/orkg/resource/X"],
        "http://orkg.org/orkg/predicate/P",
        profile=_orkg_profile(),
    )
    assert "France" not in p
    assert "dbo:capital" not in p


def test_profile_empty_one_shots_renders_without_crashing():
    empty_profile = KGProfile(
        slug="bare",
        label="Bare",
        endpoint_url="http://x/sparql",
        prefixes=(("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),),
        one_shot_examples=(),
    )
    p = generate_sparql_prompt(
        "q",
        ["http://ex/A"],
        "http://ex/P",
        profile=empty_profile,
    )
    assert isinstance(p, str) and p
    # The core rules and fence request must still be present
    assert "```sparql" in p
    assert "ONLY" in p.upper()


def test_profile_entity_and_property_uris_still_included():
    p = generate_sparql_prompt(
        "q",
        ["http://orkg.org/orkg/resource/R999"],
        "http://orkg.org/orkg/predicate/P999",
        profile=_orkg_profile(),
    )
    assert "http://orkg.org/orkg/resource/R999" in p
    assert "http://orkg.org/orkg/predicate/P999" in p
