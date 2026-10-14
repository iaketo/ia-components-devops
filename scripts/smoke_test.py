"""Comprueba UI, FAISS, análisis y memoria; --live exige servicios reales."""
import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Fixtures exclusivas del smoke test, nunca datos de producción.
PRODUCTS = [
    {"id": 44, "categoria": "procesador", "nombre": "CPU", "descripcion": "CPU gaming DDR4"},
    {"id": 1, "categoria": "grafica", "nombre": "GPU", "descripcion": "GPU gaming GDDR6"},
    {"id": 18, "categoria": "ram", "nombre": "RAM", "descripcion": "RAM DDR4"},
    {"id": 19, "categoria": "placa", "nombre": "Placa", "descripcion": "Placa DDR4"},
    {"id": 29, "categoria": "gabinete", "nombre": "Gabinete", "descripcion": "Gabinete ATX"},
]


class TestEncoder:
    """Encoder determinista; el índice FAISS y el código RAG son reales."""
    def encode(self, texts, **kwargs):
        import numpy as np
        words = ("cpu", "gpu", "ram", "placa", "gabinete", "gaming")
        return np.array([[float(w in text.lower()) for w in words] for text in texts], dtype="float32")


def check_ui():
    from streamlit.testing.v1 import AppTest
    app_path = str(Path(__file__).resolve().parents[1] / "app.py")
    app = AppTest.from_file(app_path, default_timeout=120).run()
    if app.exception:
        raise RuntimeError("La interfaz presentó una excepción")
    expected = ["Analizar Carrito", "Chat con el Agente", "Memoria", "Observabilidad", "Arquitectura"]
    if app.radio[0].options != expected:
        raise RuntimeError("La navegación no coincide con las páginas esperadas")
    for page in expected:
        app.radio[0].set_value(page).run()
        if app.exception:
            raise RuntimeError(f"Falló la página {page}")


def run(live=False):
    if live:
        from services.llm import get_client
        get_client()
    with tempfile.TemporaryDirectory() as data_dir, ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, {"APP_DATA_DIR": data_dir}))
        import memory.memory_manager as memory
        from observability.tracing import ObservabilityRecorder
        stack.enter_context(patch.object(memory, "MEMORY_FILE", os.path.join(data_dir, "memory.json")))
        recorder = ObservabilityRecorder(
            os.path.join(data_dir, "traces.jsonl"), os.path.join(data_dir, "summary.json")
        )
        if not live:
            response = Mock()
            response.json.return_value = PRODUCTS
            stack.enter_context(patch("agent.requests.get", return_value=response))
            stack.enter_context(patch("services.rag.get_model", return_value=TestEncoder()))
            client = Mock()
            client.chat.completions.create.return_value.choices = [
                Mock(message=Mock(content="Análisis de prueba: compatibilidad DDR4 verificada."))
            ]
            stack.enter_context(patch("services.llm.get_client", return_value=client))
            stack.enter_context(patch("agent.buscar_en_google", return_value="Contexto web de prueba"))

        from agent import HardwareAgent
        stack.enter_context(patch("agent.ObservabilityRecorder", return_value=recorder))
        agent = HardwareAgent()
        products = agent.cargar_catalogo()
        if not products or not agent._catalogo_cargado:
            raise RuntimeError("No se pudo cargar el catálogo e inicializar RAG")
        context = agent.rag.buscar("CPU gaming", k=min(3, len(products)))
        if not context or context == "Índice RAG no construido.":
            raise RuntimeError("RAG no devolvió contexto")
        categories = {"cpu_id": "procesador", "gpu_id": "grafica", "ram_id": "ram",
                      "mb_id": "placa", "case_id": "gabinete"}
        selection = {
            key: next((p["id"] for p in products if category in p.get("categoria", "").lower()), None)
            for key, category in categories.items()
        }
        result = agent.analizar(**selection)
        if not result["ok"] or not result["resultado"].strip():
            raise RuntimeError("El agente no produjo un análisis")
        if not agent.analizar(**selection).get("desde_cache"):
            raise RuntimeError("La memoria no recuperó el análisis")
        if not agent.chat("¿Qué significa DDR4?").strip():
            raise RuntimeError("El chat devolvió una respuesta vacía")

        check_ui()
        print("Smoke test aprobado:", "servicios reales" if live else "servicios externos simulados")
        print("Catálogo, FAISS, análisis, cache, chat y cinco páginas verificados")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Exige red y GROQ_API_KEY reales")
    args = parser.parse_args()
    try:
        run(live=args.live)
    except Exception as exc:
        # Los errores HTTP pueden incluir tokens en URLs; no imprimir mensajes.
        print("Smoke test fallido:", type(exc).__name__, file=sys.stderr)
        raise SystemExit(1) from None
