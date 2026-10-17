"""Pruebas de búsqueda con simulación HTTP; no se utilizan claves reales."""
from unittest.mock import Mock, patch

from services import web_search


def test_fallback_without_api_key():
    with patch.object(web_search, "SERP_API_KEY", ""):
        result = web_search.buscar_en_google("compatibilidad DDR5")
    assert "sin SERP_API_KEY" in result
    assert "compatibilidad DDR5" in result


def test_search_respects_result_limit():
    response = Mock()
    response.json.return_value = {
        "organic_results": [
            {"snippet": "primero"},
            {"snippet": "segundo"},
            {"snippet": "tercero"},
        ]
    }
    with patch.object(web_search, "SERP_API_KEY", "fake-key"), patch.object(
        web_search.requests, "get", return_value=response
    ) as request:
        result = web_search.buscar_en_google("motherboard", num_resultados=2)
    assert result == "primero\nsegundo"
    assert request.call_args.kwargs["timeout"] == 10


def test_search_handles_network_failure():
    with patch.object(web_search, "SERP_API_KEY", "fake-key"), patch.object(
        web_search.requests, "get", side_effect=RuntimeError("network unavailable")
    ):
        result = web_search.buscar_en_google("GPU")
    assert "Error en búsqueda web" in result
