"""
app.py — Interfaz Streamlit del Agente GM Components
=====================================================
Interfaz principal del agente de análisis de compatibilidad de hardware.
Permite seleccionar componentes, analizar compatibilidad y chatear con el agente.

IL2.1 - Integra herramientas de consulta, escritura y razonamiento.
IL2.2 - Visualiza memoria de corto y largo plazo.
IL2.3 - Muestra el plan de ejecución del agente.
IL2.4 - Documentado con docstrings y flujo claro.
"""

import os
import sys
import streamlit as st
from dotenv import load_dotenv
from observability import load_traces, summarize_traces

# Asegurar que el path incluye el directorio del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv(override=True)

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GM Components — Agente IA",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────
# CSS PERSONALIZADO
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600&display=swap');

:root {
    --bg: #0a0a0f;
    --surface: #12121a;
    --surface2: #1a1a26;
    --accent: #7c3aed;
    --accent2: #06b6d4;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --text: #e2e8f0;
    --muted: #64748b;
    --border: #1e1e2e;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

.stApp { background-color: var(--bg) !important; }

h1, h2, h3 { font-family: 'Space Mono', monospace !important; }

.main-title {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #7c3aed, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.25rem;
}

.subtitle {
    color: var(--muted);
    font-size: 0.9rem;
    margin-bottom: 2rem;
}

.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
}

.plan-step {
    background: var(--surface2);
    border-left: 3px solid var(--accent);
    padding: 0.5rem 1rem;
    margin: 0.3rem 0;
    border-radius: 0 8px 8px 0;
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
}

.component-tag {
    display: inline-block;
    background: var(--surface2);
    border: 1px solid var(--accent);
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    margin: 0.2rem;
    font-size: 0.8rem;
    color: var(--accent2);
}

.result-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    white-space: pre-wrap;
    font-family: 'DM Sans', sans-serif;
    line-height: 1.7;
}

.cache-badge {
    background: var(--success);
    color: white;
    border-radius: 4px;
    padding: 0.1rem 0.5rem;
    font-size: 0.75rem;
    font-family: 'Space Mono', monospace;
}

.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #5b21b6) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    padding: 0.5rem 1.5rem !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #6d28d9, #4c1d95) !important;
    transform: translateY(-1px);
}

.stSelectbox > div > div {
    background: var(--surface) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}

.stTextInput > div > div > input {
    background: var(--surface) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}

[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Space Mono', monospace !important;
}

hr { border-color: var(--border) !important; }

.stExpander { border-color: var(--border) !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# INICIALIZAR AGENTE EN SESSION STATE
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_agent():
    """Inicializa el agente una sola vez y lo cachea."""
    from agent import HardwareAgent
    agent = HardwareAgent()
    agent.cargar_catalogo()
    return agent

agent = get_agent()

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🖥️ GM Components")
    st.markdown("**Agente IA**")
    st.markdown("---")

    pagina = st.radio(
        "Navegación",
        ["Analizar Carrito", "Chat con el Agente", "Memoria", "Observabilidad", "Arquitectura"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    mem_resumen = agent.memory.resumen()
    st.markdown("###  Estado del Agente")
    st.markdown(f"- 💬 Mensajes sesión: `{mem_resumen['corto_plazo_mensajes']}`")
    st.markdown(f"- 💾 Análisis guardados: `{mem_resumen['largo_plazo_analisis']}`")

    if mem_resumen["ultimo_analisis"]:
        ultimo = mem_resumen["ultimo_analisis"][:16].replace("T", " ")
        st.markdown(f"- 🕐 Último análisis: `{ultimo}`")

    st.markdown("---")
    st.markdown("### 🔧 Herramientas activas")
    st.markdown("- ✅ RAG (FAISS + SentenceTransformers)")
    st.markdown("- ✅ LLM (Groq llama-3.3-70b)")
    st.markdown("- ✅ Web Search (SerpAPI)")
    st.markdown("- ✅ Memoria corto/largo plazo")

# ─────────────────────────────────────────────────────────────
# PÁGINA: ANALIZAR CARRITO
# ─────────────────────────────────────────────────────────────
if "Analizar" in pagina:
    st.markdown('<div class="main-title">🖥️ GM Components — Agente IA</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Análisis de compatibilidad de hardware con IA</div>', unsafe_allow_html=True)

    # Carritos predefinidos
    CARRITOS = {
        "Carrito 1 — Gaming Mid-Range": {"cpu": 44, "gpu": 1, "ram": 18, "mb": 19, "case": 29},
        "Carrito 2 — Workstation": {"cpu": 40, "gpu": 2, "ram": 10, "mb": 23, "case": 32},
        "Carrito 3 — Budget Build": {"cpu": 43, "gpu": 3, "ram": 11, "mb": 24, "case": 38},
        "Personalizado": None,
    }

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("### 🛒 Selección de componentes")

        carrito_sel = st.selectbox(
            "Carrito predefinido:",
            list(CARRITOS.keys())
        )

        if carrito_sel == "Personalizado":
            st.markdown("**IDs de componentes:**")
            cpu_id = st.number_input("CPU ID", min_value=0, value=0, step=1)
            gpu_id = st.number_input("GPU ID", min_value=0, value=0, step=1)
            ram_id = st.number_input("RAM ID", min_value=0, value=0, step=1)
            mb_id  = st.number_input("Placa Madre ID", min_value=0, value=0, step=1)
            case_id = st.number_input("Gabinete ID", min_value=0, value=0, step=1)

            ids = {
                "cpu": cpu_id or None,
                "gpu": gpu_id or None,
                "ram": ram_id or None,
                "mb": mb_id or None,
                "case": case_id or None,
            }
        else:
            ids = CARRITOS[carrito_sel]
            st.markdown("**Componentes del carrito:**")
            for key, val in ids.items():
                st.markdown(f'<span class="component-tag">{key.upper()}: ID {val}</span>', unsafe_allow_html=True)

        analizar_btn = st.button("🚀 Analizar compatibilidad", use_container_width=True)

    with col2:
        st.markdown("### 📋 Plan de ejecución")

        if "plan_actual" in st.session_state and st.session_state.plan_actual:
            for paso in st.session_state.plan_actual:
                st.markdown(f'<div class="plan-step">{paso}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="plan-step">El plan aparecerá aquí al analizar</div>', unsafe_allow_html=True)

        st.markdown("### 🔄 Flujo del agente")
        st.code("""
API Catálogo → RAG Index
       ↓
  Planificador (adaptativo)
       ↓
  RAG Search + Web Search
       ↓
  LLM (Groq llama-3.3-70b)
       ↓
  Resultado + Memoria LP
""", language="text")

    # Ejecutar análisis
    if analizar_btn:
        with st.spinner("🤖 El agente está analizando..."):
            resultado = agent.analizar(
                cpu_id=ids.get("cpu"),
                gpu_id=ids.get("gpu"),
                ram_id=ids.get("ram"),
                mb_id=ids.get("mb"),
                case_id=ids.get("case"),
            )

        st.session_state.ultimo_resultado = resultado
        st.session_state.plan_actual = resultado.get("plan", [])
        st.rerun()

    # Mostrar resultado
    if "ultimo_resultado" in st.session_state:
        res = st.session_state.ultimo_resultado

        st.markdown("---")
        st.markdown("### 🏁 Resultado del análisis")

        if res.get("desde_cache"):
            st.markdown('<span class="cache-badge"> Desde memoria de largo plazo</span>', unsafe_allow_html=True)

        if res["ok"]:
            # Componentes analizados
            if res.get("componentes"):
                cols = st.columns(5)
                labels = ["CPU", "GPU", "RAM", "MB", "CASE"]
                keys = ["cpu", "gpu", "ram", "mb", "case"]
                for i, (col, label, key) in enumerate(zip(cols, labels, keys)):
                    with col:
                        val = res["componentes"].get(key)
                        if val:
                            st.markdown(f"**{label}**")
                            st.caption(val[:40] + "..." if len(val) > 40 else val)
                        else:
                            st.markdown(f"**{label}**")
                            st.caption("—")

            st.markdown("---")
            if res.get("trace_id"):
                st.caption(f"Trace ID: {res['trace_id']}")

            st.markdown(f'<div class="result-box">{res["resultado"]}</div>', unsafe_allow_html=True)

            # Contexto usado (expandible)
            with st.expander(" Contexto RAG utilizado"):
                st.text(res.get("contexto_rag", "Sin contexto RAG"))

            with st.expander(" Contexto Web utilizado"):
                st.text(res.get("contexto_web", "Sin contexto web"))
        else:
            st.error(res["resultado"])

# ─────────────────────────────────────────────────────────────
# PÁGINA: CHAT
# ─────────────────────────────────────────────────────────────
elif "Chat" in pagina:
    st.markdown('<div class="main-title">💬 Chat con el Agente</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Pregunta cualquier cosa sobre hardware y compatibilidad</div>', unsafe_allow_html=True)

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Mostrar historial
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Input
    if prompt := st.chat_input("Pregunta sobre hardware, compatibilidad, bottleneck..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤔 Pensando..."):
                respuesta = agent.chat(prompt)
            st.write(respuesta)

        st.session_state.chat_messages.append({"role": "assistant", "content": respuesta})

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Limpiar chat"):
            st.session_state.chat_messages = []
            agent.memory.limpiar_corto_plazo()
            st.rerun()
    with col2:
        st.caption(f"Mensajes en memoria: {agent.memory.resumen()['corto_plazo_mensajes']}")

# ─────────────────────────────────────────────────────────────
# PÁGINA: MEMORIA
# ─────────────────────────────────────────────────────────────
elif "Memoria" in pagina:
    st.markdown('<div class="main-title">🧠 Sistema de Memoria</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Memoria de corto y largo plazo del agente</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Corto Plazo (sesión)", "💾 Largo Plazo (persistente)"])

    with tab1:
        st.markdown("### Historial de la sesión actual")
        st.caption("Los últimos 10 mensajes se mantienen en memoria para dar contexto al agente.")

        historial = agent.memory.obtener_historial()
        if historial:
            for msg in historial:
                role_icon = "👤" if msg["role"] == "user" else "🤖"
                with st.expander(f"{role_icon} {msg['role'].capitalize()}: {msg['content'][:60]}..."):
                    st.write(msg["content"])
        else:
            st.info("No hay mensajes en la sesión actual. Usa el chat o analiza un carrito.")

        if st.button("🗑️ Limpiar memoria de sesión"):
            agent.memory.limpiar_corto_plazo()
            st.success("Memoria de sesión limpiada.")
            st.rerun()

    with tab2:
        st.markdown("### Análisis guardados (persistentes)")
        st.caption("Cada análisis se guarda en disco y permite recuperar resultados previos sin llamar al LLM.")

        analisis = agent.memory.obtener_historial_largo(limite=10)
        if analisis:
            for i, a in enumerate(reversed(analisis)):
                ts = a["timestamp"][:16].replace("T", " ")
                comp = a.get("componentes", {})
                label = f"🕐 {ts} | CPU:{comp.get('cpu','—')} GPU:{comp.get('gpu','—')}"
                with st.expander(label):
                    st.json(comp)
                    st.markdown("**Resultado:**")
                    st.write(a["resultado"][:500] + "...")
        else:
            st.info("No hay análisis guardados aún. Analiza un carrito primero.")

        if st.button("🗑️ Limpiar memoria de largo plazo"):
            agent.memory.limpiar_largo_plazo()
            st.success("Memoria de largo plazo limpiada.")
            st.rerun()

# ─────────────────────────────────────────────────────────────
# PÁGINA: ARQUITECTURA
# ─────────────────────────────────────────────────────────────
elif "Observabilidad" in pagina:
    st.markdown('<div class="main-title">Observabilidad del Agente</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Trazas, metricas y evidencia de ejecución</div>', unsafe_allow_html=True)

    traces = load_traces()
    summary = summarize_traces(traces)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ejecuciones", summary["total_traces"])
    col2.metric("Exito", f"{summary['success_rate']}%")
    col3.metric("Latencia promedio", f"{summary['avg_duration_ms']} ms")
    col4.metric("Cache hit", f"{summary['cache_hit_rate']}%")

    st.markdown("### Pasos mas costosos")
    if summary["slowest_steps"]:
        st.dataframe(summary["slowest_steps"], use_container_width=True)
    else:
        st.info("Aun no hay pasos registrados. Ejecuta un analisis para generar trazas.")

    st.markdown("### Ultimas trazas")
    if traces:
        rows = []
        for trace in reversed(traces[-20:]):
            rows.append({
                "trace_id": trace.get("trace_id"),
                "inicio": trace.get("started_at"),
                "operacion": trace.get("operation"),
                "ok": trace.get("ok"),
                "duracion_ms": trace.get("duration_ms"),
                "cache_hit": trace.get("metrics", {}).get("cache_hit"),
                "componentes": trace.get("metrics", {}).get("component_count"),
                "error": trace.get("error"),
            })
        st.dataframe(rows, use_container_width=True)

        with st.expander("Ver JSON de la ultima traza"):
            st.json(traces[-1])
    else:
        st.info("No existen trazas todavia.")

    st.markdown("### Recomendaciones operativas")
    recomendaciones = []
    if summary["avg_duration_ms"] > 8000:
        recomendaciones.append("Revisar latencia del LLM y cachear respuestas frecuentes.")
    if summary["cache_hit_rate"] < 20 and summary["total_traces"] >= 5:
        recomendaciones.append("Normalizar IDs de componentes para aumentar reutilizacion de memoria de largo plazo.")
    if summary["failed_traces"] > 0:
        recomendaciones.append("Priorizar revision de trazas fallidas y manejo de errores de API externa.")
    if not recomendaciones:
        recomendaciones.append("Mantener monitoreo por trazas y comparar latencia antes/despues de cambios.")
    for rec in recomendaciones:
        st.markdown(f"- {rec}")
elif "Arquitectura" in pagina:
    st.markdown('<div class="main-title">📐 Arquitectura del Sistema</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Documentación técnica del agente GM Components</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏗️ Componentes del sistema")

        componentes = [
            ("agent.py", "HardwareAgent", "Orquestador principal. Coordina herramientas, memoria y planificación. IL2.1, IL2.3"),
            ("services/llm.py", "analizar_con_ia()", "LLM Groq llama-3.3-70b-versatile. Razonamiento y síntesis. IL2.1"),
            ("services/rag.py", "RAG", "FAISS + SentenceTransformers. Recuperación semántica del catálogo. IL2.1, IL2.4"),
            ("services/web_search.py", "buscar_en_google()", "SerpAPI. Validación externa de componentes. IL2.1"),
            ("memory/memory_manager.py", "MemoryManager", "Memoria de corto y largo plazo (JSON). IL2.2, IL2.4"),
            ("app.py", "Streamlit UI", "Interfaz de usuario. Visualiza plan, resultado y memoria. IL2.4"),
        ]

        for archivo, clase, desc in componentes:
            with st.expander(f"📄 `{archivo}` — {clase}"):
                st.write(desc)

    with col2:
        st.markdown("### 🔄 Flujo de orquestación")
        st.code("""
┌─────────────────────────────────────┐
│           USUARIO / FRONTEND         │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│         HardwareAgent (agent.py)     │
│                                      │
│  1. cargar_catalogo()  → API REST    │
│  2. seleccionar_componentes()         │
│  3. _planificar() → plan adaptativo  │
│  4. RAG.buscar()  → contexto local   │
│  5. buscar_en_google() → web         │
│  6. analizar_con_ia() → LLM Groq     │
│  7. memory.guardar_analisis()         │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│         RESULTADO + MEMORIA          │
│  • Análisis de compatibilidad        │
│  • Plan de pasos ejecutados          │
│  • Guardado en largo plazo (JSON)    │
└─────────────────────────────────────┘
""", language="text")

    st.markdown("---")
    st.markdown("### 📊 Indicadores de Logro cubiertos")

    indicadores = {
        "IL2.1": "Agente funcional con 3 herramientas: RAG, Web Search, LLM Groq.",
        "IL2.2": "MemoryManager con corto plazo (sesión) y largo plazo (JSON persistente).",
        "IL2.3": "Planificador adaptativo: ajusta herramientas según componentes disponibles.",
        "IL2.4": "Documentación con docstrings, README, diagrama de orquestación y esta página.",
    }

    for il, desc in indicadores.items():
        col_a, col_b = st.columns([1, 5])
        with col_a:
            st.markdown(f"**`{il}`**")
        with col_b:
            st.markdown(desc)

    st.markdown("---")
    st.markdown("### 📚 Referencias")
    st.markdown("""
- Groq. (2024). *Groq API Documentation*. https://console.groq.com/docs
- LangChain. (2024). *LangChain Documentation*. https://docs.langchain.com
- Meta AI. (2024). *Llama 3: Open Foundation and Fine-Tuned Chat Models*. https://ai.meta.com/llama
- Hugging Face. (2024). *Sentence Transformers Documentation*. https://www.sbert.net
- Facebook Research. (2024). *FAISS: A Library for Efficient Similarity Search*. https://faiss.ai
- SerpApi. (2024). *Google Search API Documentation*. https://serpapi.com/docs
""")

