"""
Setup and initialize spaCy for NLP tasks.
"""

import spacy
from config.settings import SPACY_MODEL


# global varaible to ghold loaded spacy model in memory
_spacy_instance = None


def load_spacy_model(model_name: str = SPACY_MODEL):
    """
    Load spaCy language model.

    Args:
        model_name: Name of the spaCy model (e.g., 'en_core_web_sm')

    Returns:
        spaCy Language object
    """
    # spacy model cached globally
    global _spacy_instance

    # if not alrady loaded, rrturn existin instance
    if _spacy_instance is not None:
        return _spacy_instance

    try:
        _spacy_instance = spacy.load(model_name)
        return _spacy_instance
    except OSError:
        print(f"Model '{model_name}' not found. Installing...")
        import subprocess

        subprocess.run(["python", "-m", "spacy", "download", model_name])
        _spacy_instance = spacy.load(model_name)
        return _spacy_instance
