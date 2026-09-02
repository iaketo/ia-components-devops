"""
agent.py
========
Agente principal de análisis de compatibilidad de hardware.

Integra:
  - Herramienta de consulta: RAG semántico sobre catálogo de productos.
  - Herramienta de consulta: búsqueda web (SerpAPI).
  - Herramienta de razonamiento: LLM (Groq llama-3.3-70b-versatile).
  - Memoria de corto plazo: historial conversacional en sesión.
  - Memoria de largo plazo: análisis persistidos en JSON.
  - Planificación: ciclo Plan → Execute → Synthesize antes de responder.

IL2.1 - Agente funcional con herramientas de consulta, escritura y razonamiento.
IL2.2 - Memoria de corto y largo plazo.
IL2.3 - Planificación y toma de decisiones adaptativa.
IL2.4 - Documentado con docstrings y flujo claro.
"""

import os
import requests
from dotenv import load_dotenv

from services.llm import analizar_con_ia, chat_simple
from services.rag import RAG
from services.web_search import buscar_en_google
from memory.memory_manager import MemoryManager
from observability import ObservabilityRecorder

load_dotenv()

API_URL = "https://gmcomponents.onrender.com/backend/products/"


class HardwareAgent:
    """
    Agente de análisis de compatibilidad de hardware para GM Components.

    Arquitectura:
        Usuario → HardwareAgent
                    ├─ Paso 1: Obtener catálogo (API REST)
                    ├─ Paso 2: Construir índice RAG (semántico)
                    ├─ Paso 3: Seleccionar componentes por ID
                    ├─ Paso 4: Planificar análisis (qué herramientas usar)
                    ├─ Paso 5: Ejecutar herramientas (RAG + Web Search)
                    ├─ Paso 6: Sintetizar con LLM
                    └─ Paso 7: Guardar en memoria de largo plazo

    Herramientas disponibles:
        - RAG: recuperación semántica del catálogo.
        - Web Search: validación de componentes en internet.
        - LLM: razonamiento y síntesis final.
    """

    def __init__(self):
        self.observability = ObservabilityRecorder()
        self.memory = MemoryManager()
        self.rag = RAG()
        self.productos: list[dict] = []
        self._catalogo_cargado = False

    # ──────────────────────────────────────────
    # PASO 1: Catálogo
    # ──────────────────────────────────────────
    def cargar_catalogo(self) -> list[dict]:
        """
        Carga el catálogo de productos desde la API de GM Components.

        Returns:
            Lista de productos disponibles.
        """
        try:
            response = requests.get(API_URL, timeout=10)
            self.productos = response.json()
            self.rag.construir_indice(self.productos)
            self._catalogo_cargado = True
            return self.productos
        except Exception as e:
            print(f" Error cargando catálogo: {e}")
            return []

    # ──────────────────────────────────────────
    # PASO 2: Selección de componentes
    # ──────────────────────────────────────────
    def seleccionar_componentes(
        self,
        cpu_id, gpu_id, ram_id, mb_id, case_id
    ) -> tuple:
        """
        Selecciona los componentes por ID desde el catálogo.

        Args:
            cpu_id, gpu_id, ram_id, mb_id, case_id: IDs de los componentes.

        Returns:
            Tupla (cpu, gpu, ram, mb, case) — cada elemento es dict o None.
        """
        cpu = gpu = ram = mb = case = None

        for p in self.productos:
            try:
                pid = int(p["id"])
                cat = p.get("categoria", "").lower()

                if cpu_id and pid == int(cpu_id) and "procesador" in cat:
                    cpu = p
                elif gpu_id and pid == int(gpu_id) and "grafica" in cat:
                    gpu = p
                elif ram_id and pid == int(ram_id) and "ram" in cat:
                    ram = p
                elif mb_id and pid == int(mb_id) and "placa" in cat:
                    mb = p
                elif case_id and pid == int(case_id) and "gabinete" in cat:
                    case = p
            except Exception:
                continue

        return cpu, gpu, ram, mb, case

    # ──────────────────────────────────────────
    # PASO 3: Planificación (IL2.3)
    # ──────────────────────────────────────────
    def _planificar(self, cpu, gpu, ram, mb, case) -> dict:
        """
        Planifica qué herramientas usar según los componentes disponibles.

        Estrategia adaptativa:
            - Si hay CPU y GPU → query de bottleneck CPU vs GPU.
            - Si solo hay CPU → query enfocada en procesador.
            - Si solo hay GPU → query enfocada en gráfica.
            - Siempre usar RAG si hay componentes.
            - Usar web search si hay query válida.

        Returns:
            Dict con el plan: {query, usar_rag, usar_web, pasos}.

        IL2.3 - Planificación adaptativa según condiciones del entorno.
        """
        pasos = []
        query = ""
        usar_rag = bool(self.productos)
        usar_web = True

        cpu_desc = cpu["descripcion"] if cpu else None
        gpu_desc = gpu["descripcion"] if gpu else None

        if cpu_desc and gpu_desc:
            query = f"{cpu_desc} vs {gpu_desc} bottleneck compatibility"
            pasos = [
                "1. Analizar compatibilidad CPU-GPU (posible cuello de botella)",
                "2. Verificar compatibilidad RAM con placa madre",
                "3. Verificar compatibilidad física con gabinete",
                "4. Buscar información de validación en web",
                "5. Sintetizar análisis con LLM"
            ]
        elif cpu_desc:
            query = f"{cpu_desc} performance analysis"
            pasos = [
                "1. Analizar rendimiento del procesador",
                "2. Verificar compatibilidad con componentes disponibles",
                "3. Sintetizar análisis con LLM"
            ]
        elif gpu_desc:
            query = f"{gpu_desc} performance gaming"
            pasos = [
                "1. Analizar rendimiento de la GPU",
                "2. Verificar compatibilidad con componentes disponibles",
                "3. Sintetizar análisis con LLM"
            ]
        else:
            usar_web = False
            pasos = ["1. Analizar componentes disponibles con LLM"]

        return {
            "query": query,
            "usar_rag": usar_rag,
            "usar_web": usar_web and bool(query),
            "pasos": pasos
        }

    # ──────────────────────────────────────────
    # PASO 4: Ejecución principal
    # ──────────────────────────────────────────
    def analizar(
        self,
        cpu_id=None, gpu_id=None, ram_id=None,
        mb_id=None, case_id=None
    ) -> dict:
        """
        Ejecuta el ciclo completo del agente: Plan -> Execute -> Synthesize.

        Ademas registra trazas, duraciones por paso, uso de cache y tamanos de
        contexto para cumplir los requisitos de observabilidad de la Evaluacion 3.
        """
        componentes_ids = {
            "cpu": cpu_id, "gpu": gpu_id, "ram": ram_id,
            "mb": mb_id, "case": case_id
        }
        trace = self.observability.start_trace(
            "analizar_componentes",
            metadata={"componentes_solicitados": componentes_ids}
        )

        try:
            if not self._catalogo_cargado:
                with trace.step("cargar_catalogo"):
                    self.cargar_catalogo()

            with trace.step("seleccionar_componentes"):
                cpu, gpu, ram, mb, case = self.seleccionar_componentes(
                    cpu_id, gpu_id, ram_id, mb_id, case_id
                )

            disponibles = [c for c in [cpu, gpu, ram, mb, case] if c is not None]
            if not disponibles:
                trace.finish(
                    ok=False,
                    error="No se seleccionaron componentes validos.",
                    metrics={"cache_hit": False, "component_count": 0}
                )
                return {
                    "ok": False,
                    "resultado": "No se seleccionaron componentes validos.",
                    "plan": [],
                    "contexto_rag": "",
                    "contexto_web": "",
                    "trace_id": trace.trace_id
                }

            with trace.step("buscar_cache_memoria"):
                analisis_previo = self.memory.buscar_analisis_similar(componentes_ids)
            if analisis_previo:
                trace.finish(
                    ok=True,
                    metrics={
                        "cache_hit": True,
                        "component_count": len(disponibles),
                        "rag_context_chars": 0,
                        "web_context_chars": 0,
                        "response_chars": len(analisis_previo.get("resultado", ""))
                    }
                )
                return {
                    "ok": True,
                    "resultado": analisis_previo["resultado"] + "\n\n_(Recuperado de memoria de largo plazo)_",
                    "plan": ["Recuperado desde cache de memoria de largo plazo"],
                    "contexto_rag": "",
                    "contexto_web": "",
                    "desde_cache": True,
                    "trace_id": trace.trace_id
                }

            with trace.step("planificar"):
                plan = self._planificar(cpu, gpu, ram, mb, case)

            contexto_rag = ""
            contexto_web = ""

            if plan["usar_rag"] and plan["query"]:
                with trace.step("rag_search", query=plan["query"], k=3):
                    contexto_rag = self.rag.buscar(plan["query"], k=3)

            if plan["usar_web"] and plan["query"]:
                with trace.step("web_search", query=plan["query"]):
                    contexto_web = buscar_en_google(plan["query"])

            contexto_final = f"""
====================
RAG (Catalogo semantico)
====================
{contexto_rag or 'Sin datos RAG'}

====================
WEB (Validacion externa)
====================
{contexto_web or 'Sin datos web'}
"""

            with trace.step("llm_sintesis", context_chars=len(contexto_final)):
                resultado = analizar_con_ia(cpu, gpu, ram, mb, case, contexto_final)

            with trace.step("guardar_memoria_largo_plazo"):
                self.memory.guardar_analisis(
                    componentes=componentes_ids,
                    resultado=resultado
                )

            with trace.step("guardar_memoria_corto_plazo"):
                self.memory.agregar_mensaje("user", f"Analizar componentes: {componentes_ids}")
                self.memory.agregar_mensaje("assistant", resultado[:500])

            trace.finish(
                ok=True,
                metrics={
                    "cache_hit": False,
                    "component_count": len(disponibles),
                    "rag_context_chars": len(contexto_rag),
                    "web_context_chars": len(contexto_web),
                    "response_chars": len(resultado),
                    "plan_steps": len(plan["pasos"])
                }
            )

            return {
                "ok": True,
                "resultado": resultado,
                "plan": plan["pasos"],
                "contexto_rag": contexto_rag,
                "contexto_web": contexto_web,
                "componentes": {
                    "cpu": cpu["descripcion"] if cpu else None,
                    "gpu": gpu["descripcion"] if gpu else None,
                    "ram": ram["descripcion"] if ram else None,
                    "mb": mb["descripcion"] if mb else None,
                    "case": case["descripcion"] if case else None,
                },
                "desde_cache": False,
                "trace_id": trace.trace_id
            }
        except Exception as exc:
            trace.finish(ok=False, error=str(exc), metrics={"cache_hit": False})
            raise
    # Chat con memoria de corto plazo (IL2.2)
    # ──────────────────────────────────────────
    def chat(self, mensaje: str) -> str:
        """
        Chat conversacional con memoria de corto plazo.

        Args:
            mensaje: Pregunta del usuario.

        Returns:
            Respuesta del agente.

        IL2.2 - Memoria de corto plazo para continuidad conversacional.
        """
        historial = self.memory.obtener_historial()
        respuesta = chat_simple(mensaje, historial)
        self.memory.agregar_mensaje("user", mensaje)
        self.memory.agregar_mensaje("assistant", respuesta)
        return respuesta


