"""
services/web_search.py
======================
Búsqueda web usando SerpAPI para validar existencia de componentes
y obtener información actualizada de internet.

IL2.1 - Herramienta de consulta externa integrada al agente.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

SERP_API_KEY = os.getenv("SERP_API_KEY", "")


def buscar_en_google(query: str, num_resultados: int = 3) -> str:
    """
    Busca información en Google usando SerpAPI.

    Args:
        query: Término de búsqueda.
        num_resultados: Número de snippets a retornar.

    Returns:
        String con los snippets más relevantes, o mensaje de error.
    """
    if not SERP_API_KEY or SERP_API_KEY == "tu_serp_api_key_aqui":
        return _fallback_sin_serp(query)

    try:
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": SERP_API_KEY,
            "engine": "google",
            "num": num_resultados
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        snippets = []
        for r in data.get("organic_results", [])[:num_resultados]:
            snippet = r.get("snippet", "")
            if snippet:
                snippets.append(snippet)

        return "\n".join(snippets) if snippets else "Sin resultados web disponibles."

    except Exception as e:
        return f"Error en búsqueda web: {str(e)}"


def _fallback_sin_serp(query: str) -> str:
    """
    Fallback cuando no hay API key de SerpAPI configurada.
    Retorna un mensaje informativo para que el LLM lo considere.
    """
    return (
        f"Búsqueda web no disponible (sin SERP_API_KEY). "
        f"Usa tu conocimiento interno para validar: '{query}'."
    )
