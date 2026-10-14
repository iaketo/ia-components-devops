from unittest.mock import Mock

import pytest
import requests

from observability import load_traces


def test_catalog_and_selection(hardware_agent):
    products = hardware_agent.cargar_catalogo()
    assert len(products) == 5
    assert hardware_agent._catalogo_cargado
    selected = hardware_agent.seleccionar_componentes(44, 1, 18, 19, 29)
    assert [p["id"] for p in selected] == [44, 1, 18, 19, 29]
    assert hardware_agent.seleccionar_componentes(1, None, None, None, None)[0] is None


@pytest.mark.parametrize("data", [{"error": "unavailable"}, [], ["invalid product"]])
def test_invalid_catalog_is_rejected(hardware_agent, monkeypatch, data):
    response = Mock()
    response.json.return_value = data
    monkeypatch.setattr("agent.requests.get", Mock(return_value=response))
    assert hardware_agent.cargar_catalogo() == []
    assert not hardware_agent._catalogo_cargado
    assert hardware_agent.rag.index is None


def test_catalog_http_failure_clears_stale_state(hardware_agent, monkeypatch):
    hardware_agent.cargar_catalogo()
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("503")
    monkeypatch.setattr("agent.requests.get", Mock(return_value=response))
    assert hardware_agent.cargar_catalogo() == []
    response.json.assert_not_called()
    assert hardware_agent.productos == []
    assert not hardware_agent._catalogo_cargado


def test_invalid_ids_do_not_call_llm(hardware_agent, monkeypatch):
    llm = Mock()
    monkeypatch.setattr("agent.analizar_con_ia", llm)
    result = hardware_agent.analizar(cpu_id=999)
    assert not result["ok"]
    llm.assert_not_called()
    assert not load_traces(hardware_agent.observability.traces_file)[0]["ok"]


def test_analysis_persists_and_second_call_uses_cache(hardware_agent, monkeypatch):
    llm = Mock(return_value="Compatibilidad verificada")
    web = Mock(return_value="Información de prueba")
    monkeypatch.setattr("agent.analizar_con_ia", llm)
    monkeypatch.setattr("agent.buscar_en_google", web)
    result = hardware_agent.analizar(cpu_id=44, gpu_id=1)
    assert result["ok"]
    assert result["contexto_rag"]
    assert "Información de prueba" in llm.call_args.args[-1]
    assert len(hardware_agent.memory.long_term) == 1
    assert len(hardware_agent.memory.short_term) == 2
    assert hardware_agent.analizar(cpu_id=44, gpu_id=1)["desde_cache"]
    llm.assert_called_once()
    web.assert_called_once()
    traces = load_traces(hardware_agent.observability.traces_file)
    assert len(traces) == 2
    assert traces[-1]["metrics"]["cache_hit"]


def test_llm_failure_is_recorded_without_saving_success(hardware_agent, monkeypatch):
    monkeypatch.setattr("agent.buscar_en_google", Mock(return_value=""))
    monkeypatch.setattr("agent.analizar_con_ia", Mock(side_effect=RuntimeError("LLM unavailable")))
    with pytest.raises(RuntimeError):
        hardware_agent.analizar(cpu_id=44)
    assert hardware_agent.memory.long_term == []
    trace = load_traces(hardware_agent.observability.traces_file)[0]
    assert not trace["ok"]
    assert trace["error"] == "LLM unavailable"


def test_chat_preserves_conversation(hardware_agent, monkeypatch):
    llm = Mock(return_value="Respuesta")
    monkeypatch.setattr("agent.chat_simple", llm)
    hardware_agent.chat("Primera pregunta")
    hardware_agent.chat("Segunda pregunta")
    assert llm.call_args.args[1] == [
        {"role": "user", "content": "Primera pregunta"},
        {"role": "assistant", "content": "Respuesta"},
    ]
    assert len(hardware_agent.memory.short_term) == 4
