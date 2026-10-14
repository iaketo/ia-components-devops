import os
from unittest.mock import Mock

import pytest

from scripts.smoke_test import PRODUCTS, TestEncoder


@pytest.fixture
def hardware_agent(monkeypatch, tmp_path):
    import agent
    import memory.memory_manager as memory
    from observability import ObservabilityRecorder
    response = Mock()
    response.json.return_value = PRODUCTS
    monkeypatch.setattr(agent.requests, "get", Mock(return_value=response))
    monkeypatch.setattr("services.rag.get_model", lambda: TestEncoder())
    monkeypatch.setattr(memory, "MEMORY_FILE", str(tmp_path / "memory.json"))
    monkeypatch.setattr(agent, "ObservabilityRecorder", lambda: ObservabilityRecorder(
        str(tmp_path / "traces.jsonl"), str(tmp_path / "summary.json")
    ))
    return agent.HardwareAgent()
