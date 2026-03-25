"""
Setup and initialize spaCy for NLP tasks.
"""
import spacy
from config.settings import SPACY_MODEL


def load_spacy_model(model_name: str = SPACY_MODEL):
    """
    Load spaCy language model.

    Args:
        model_name: Name of the spaCy model (e.g., 'en_core_web_sm')

    Returns:
        spaCy Language object
    """
    try:
        nlp = spacy.load(model_name)
        return nlp
    except OSError:
        print(f"Model '{model_name}' not found. Installing...")
        import subprocess
        subprocess.run(["python", "-m", "spacy", "download", model_name])
        return spacy.load(model_name)
