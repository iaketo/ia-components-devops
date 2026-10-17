"""Pruebas aisladas de memoria, sin consumir APIs ni modificar datos reales."""
from unittest.mock import patch

from memory.memory_manager import MemoryManager


def test_short_term_limits_last_ten_messages(tmp_path):
    with patch("memory.memory_manager.MEMORY_FILE", str(tmp_path / "memory.json")):
        memory = MemoryManager()
        for index in range(12):
            memory.agregar_mensaje("user", f"message-{index}")
        messages = memory.obtener_historial()
        assert len(messages) == 10
        assert messages[0]["content"] == "message-2"
        memory.limpiar_corto_plazo()
        assert memory.obtener_historial() == []


def test_long_term_persists_and_finds_most_recent(tmp_path):
    with patch("memory.memory_manager.MEMORY_FILE", str(tmp_path / "memory.json")):
        memory = MemoryManager()
        memory.guardar_analisis({"cpu": 44}, "compatible", puntaje=90)
        memory.guardar_analisis({"cpu": 44}, "updated", puntaje=95)
        loaded = MemoryManager()
        assert len(loaded.obtener_historial_largo()) == 2
        assert loaded.buscar_analisis_similar({"cpu": 44})["resultado"] == "updated"
        assert loaded.buscar_analisis_similar({"gpu": 1}) is None
        assert loaded.resumen()["largo_plazo_analisis"] == 2


def test_corrupt_memory_file_falls_back_to_empty(tmp_path):
    file = tmp_path / "memory.json"
    file.write_text("{broken json", encoding="utf-8")
    with patch("memory.memory_manager.MEMORY_FILE", str(file)):
        assert MemoryManager().obtener_historial_largo() == []
