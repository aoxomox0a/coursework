"""
Load hand-authored one-shot examples for a KG slug.

Curated examples live as JSON lists under ``config/curated_oneshots/<slug>.json``.
They are OPTIONAL: when a slug has no curated file the loader returns an empty
tuple, and the profile falls back to whatever synthetic one-shots (if any) the
indexing pipeline produced.

The JSON schema per entry:

    {
      "question":      "...",                 # required
      "entity_uris":   ["<uri>", ...],         # required (may be empty)
      "property_uri":  "<uri>" | null,         # optional, default null
      "sparql":        "...",                  # required
      "tags":          ["factoid", ...]        # optional, default []
    }
"""
import json
from pathlib import Path

from src.kg_profiles.base import OneShotExample

# Shipped under config/ (not data/, which is gitignored) so curated files are
# versioned with the code.
CURATED_DIR: Path = Path("config/curated_oneshots")


def curated_path_for(slug: str) -> Path:
    """Filesystem path where the curated one-shot file for ``slug`` lives."""
    return CURATED_DIR / f"{slug}.json"


def _to_one_shot(raw: dict) -> OneShotExample:
    if not isinstance(raw, dict):
        raise ValueError(f"Expected object per curated entry, got {type(raw).__name__}")
    return OneShotExample(
        question=raw["question"],
        entity_uris=tuple(raw.get("entity_uris", ())),
        property_uri=raw.get("property_uri"),
        sparql=raw["sparql"],
        tags=frozenset(raw.get("tags", ())),
    )


def load_curated_one_shots(slug: str) -> tuple[OneShotExample, ...]:
    """Return the curated one-shot examples for ``slug``, or an empty tuple if absent."""
    path = curated_path_for(slug)
    if not path.exists():
        return ()

    raw = path.read_text()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed curated-oneshot JSON at {path}: {exc}") from exc

    if not isinstance(parsed, list):
        raise ValueError(
            f"Curated-oneshot file {path} must be a JSON array at its root; "
            f"got {type(parsed).__name__}."
        )

    return tuple(_to_one_shot(item) for item in parsed)
