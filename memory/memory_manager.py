"""
memory/memory_manager.py
========================
Sistema de memoria para el agente con dos niveles:

- Memoria de corto plazo (SHORT): historial de conversación en sesión.
- Memoria de largo plazo (LONG): análisis previos guardados en archivo JSON.

IL2.2 - Configura procesos de memoria de contenido.
IL2.4 - Recuperación de contexto semántico para continuidad de tareas.
"""

import json
import os
from datetime import datetime
from typing import Optional


MEMORY_FILE = os.path.join(os.path.dirname(__file__), "long_term_memory.json")


class MemoryManager:
    """
    Gestor de memoria de corto y largo plazo para el agente.

    Arquitectura:
        - short_term: lista de mensajes {role, content} de la sesión actual.
        - long_term:  lista de análisis previos persistidos en JSON.
    """

    def __init__(self):
        self.short_term: list[dict] = []  # Memoria de corto plazo (sesión)
        self.long_term: list[dict] = self._cargar_largo_plazo()

    # ──────────────────────────────────────────
    # CORTO PLAZO
    # ──────────────────────────────────────────
    def agregar_mensaje(self, role: str, content: str) -> None:
        """
        Agrega un mensaje al historial de corto plazo.

        Args:
            role: 'user' o 'assistant'.
            content: Contenido del mensaje.
        """
        self.short_term.append({"role": role, "content": content})

        # Limitar a los últimos 10 mensajes para no sobrecargar el contexto
        if len(self.short_term) > 10:
            self.short_term = self.short_term[-10:]

    def obtener_historial(self) -> list[dict]:
        """Retorna el historial de corto plazo actual."""
        return self.short_term.copy()

    def limpiar_corto_plazo(self) -> None:
        """Limpia el historial de la sesión actual."""
        self.short_term = []

    # ──────────────────────────────────────────
    # LARGO PLAZO
    # ──────────────────────────────────────────
    def guardar_analisis(
        self,
        componentes: dict,
        resultado: str,
        puntaje: Optional[int] = None
    ) -> None:
        """
        Persiste un análisis en la memoria de largo plazo.

        Args:
            componentes: Dict con los IDs/nombres de los componentes analizados.
            resultado: Texto del análisis generado por el LLM.
            puntaje: Puntaje de compatibilidad (0-100).
        """
        entrada = {
            "timestamp": datetime.now().isoformat(),
            "componentes": componentes,
            "resultado": resultado,
            "puntaje": puntaje
        }

        self.long_term.append(entrada)
        self._guardar_largo_plazo()

    def obtener_historial_largo(self, limite: int = 5) -> list[dict]:
        """
        Retorna los últimos análisis guardados.

        Args:
            limite: Número máximo de análisis a retornar.

        Returns:
            Lista de análisis recientes.
        """
        return self.long_term[-limite:] if self.long_term else []

    def buscar_analisis_similar(self, componentes: dict) -> Optional[dict]:
        """
        Busca en la memoria de largo plazo un análisis previo con los mismos componentes.

        Args:
            componentes: Dict con los componentes a buscar.

        Returns:
            El análisis previo si existe, None si no.
        """
        for entrada in reversed(self.long_term):
            if entrada.get("componentes") == componentes:
                return entrada
        return None

    def limpiar_largo_plazo(self) -> None:
        """Limpia toda la memoria de largo plazo."""
        self.long_term = []
        if os.path.exists(MEMORY_FILE):
            os.remove(MEMORY_FILE)

    # ──────────────────────────────────────────
    # PERSISTENCIA
    # ──────────────────────────────────────────
    def _cargar_largo_plazo(self) -> list[dict]:
        """Carga la memoria de largo plazo desde el archivo JSON."""
        if not os.path.exists(MEMORY_FILE):
            return []
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _guardar_largo_plazo(self) -> None:
        """Guarda la memoria de largo plazo en el archivo JSON."""
        try:
            os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.long_term, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Error guardando memoria: {e}")

    def resumen(self) -> dict:
        """Retorna un resumen del estado de la memoria."""
        return {
            "corto_plazo_mensajes": len(self.short_term),
            "largo_plazo_analisis": len(self.long_term),
            "ultimo_analisis": self.long_term[-1]["timestamp"] if self.long_term else None
        }
