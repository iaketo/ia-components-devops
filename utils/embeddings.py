"""
utils/embeddings.py
===================
Utilidades para generación de embeddings de texto.
Centraliza el modelo para evitar cargas múltiples.
"""

from sentence_transformers import SentenceTransformer
from functools import lru_cache


@lru_cache(maxsize=1)
def get_model():
    """Carga y comparte el modelo solo cuando se necesitan embeddings."""
    return SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str):
    """
    Genera el embedding de un texto.

    Args:
        text: Texto a embeder.

    Returns:
        Vector numpy del embedding.
    """
    return get_model().encode(text)


def embed_batch(texts: list[str]):
    """
    Genera embeddings para una lista de textos.

    Args:
        texts: Lista de textos.

    Returns:
        Array numpy de embeddings.
    """
    return get_model().encode(texts, show_progress_bar=False)
