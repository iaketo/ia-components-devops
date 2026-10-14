from unittest.mock import Mock

import pytest
import requests

from scripts.smoke_test import TestEncoder, PRODUCTS


@pytest.mark.parametrize("key", ["", "dummy", "tu_groq_api_key_aqui"])
def test_missing_groq_key_is_rejected(monkeypatch, key):
    from services.llm import get_client
    monkeypatch.setenv("GROQ_API_KEY", key)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        get_client()


def test_rag_retrieves_without_duplicating_last_product(monkeypatch):
    from services.rag import RAG
    monkeypatch.setattr("services.rag.get_model", lambda: TestEncoder())
    rag = RAG()
    rag.construir_indice(PRODUCTS[:2])
    assert rag.buscar("GPU", k=3).splitlines()[0].startswith("grafica")
    assert len(rag.buscar("GPU", k=3).splitlines()) == 2
    assert rag.buscar("GPU", k=0) == ""
    rag.construir_indice([])
    assert rag.buscar("CPU") == "Índice RAG no construido."


def test_search_without_key_does_not_make_http_request(monkeypatch):
    from services import web_search
    monkeypatch.setattr(web_search, "SERP_API_KEY", "")
    get = Mock()
    monkeypatch.setattr(web_search.requests, "get", get)
    assert "sin SERP_API_KEY" in web_search.buscar_en_google("CPU")
    get.assert_not_called()


def test_search_http_error_is_handled(monkeypatch):
    from services import web_search
    monkeypatch.setattr(web_search, "SERP_API_KEY", "test-fixture")
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("503: https://serpapi.com/search?api_key=private-token")
    monkeypatch.setattr(web_search.requests, "get", Mock(return_value=response))
    result = web_search.buscar_en_google("CPU")
    assert "Error en búsqueda web" in result
    assert "private-token" not in result
    response.json.assert_not_called()
