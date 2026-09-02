"""
services/rag.py
===============
Sistema RAG (Retrieval-Augmented Generation) con FAISS + SentenceTransformers.
Construye un índice vectorial sobre el catálogo de productos y permite
búsqueda semántica para enriquecer el contexto del LLM.

IL2.1 - Herramienta de consulta semántica.
IL2.4 - Recuperación de contexto semántico para continuidad del flujo.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# Modelo de embeddings liviano y eficiente
_model = SentenceTransformer("all-MiniLM-L6-v2")


class RAG:
    """
    Motor de búsqueda semántica sobre el catálogo de productos.

    Flujo:
        1. construir_indice(productos) → genera embeddings y los indexa en FAISS
        2. buscar(query, k)           → recupera los k productos más relevantes
    """

    def __init__(self):
        self.textos: list[str] = []
        self.index = None

    def construir_indice(self, productos: list[dict]) -> None:
        """
        Construye el índice FAISS a partir del catálogo de productos.

        Args:
            productos: Lista de dicts con campos 'categoria', 'nombre', 'descripcion'.
        """
        self.textos = [
            f"{p.get('categoria', '')} {p.get('nombre', '')} {p.get('descripcion', '')}"
            for p in productos
        ]

        embeddings = _model.encode(self.textos, show_progress_bar=False)
        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(embeddings, dtype="float32"))

    def buscar(self, query: str, k: int = 3) -> str:
        """
        Realiza búsqueda semántica en el índice.

        Args:
            query: Texto de consulta.
            k: Número de resultados a retornar.

        Returns:
            String con los k resultados más relevantes.
        """
        if self.index is None or not self.textos:
            return "Índice RAG no construido."

        query_embedding = _model.encode([query], show_progress_bar=False)
        _, indices = self.index.search(
            np.array(query_embedding, dtype="float32"), k
        )

        resultados = [self.textos[i] for i in indices[0] if i < len(self.textos)]
        return "\n".join(resultados)
