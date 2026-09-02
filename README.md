# GM Components — Agente IA de Compatibilidad de Hardware

Agente inteligente que analiza la compatibilidad de componentes de hardware (CPU, GPU, RAM, Placa Madre, Gabinete) para la tienda GM Components.

## Indicadores de Logro cubiertos

| IL | Descripción | Implementación |
|----|-------------|----------------|
| IL2.1 | Agente funcional con herramientas de consulta, escritura y razonamiento | `agent.py` + `services/` |
| IL2.2 | Memoria de corto y largo plazo | `memory/memory_manager.py` |
| IL2.3 | Planificación adaptativa y toma de decisiones | `agent.py` → `_planificar()` |
| IL2.4 | Documentación técnica y orquestación | `README.md`, docstrings, `app.py` |

---

## Arquitectura del sistema

```
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
│        RESULTADO + MEMORIA          │
│   Análisis de compatibilidad        │
│   Plan de pasos ejecutados          │
│   Guardado en largo plazo (JSON)    │
└─────────────────────────────────────┘
```

---

## Estructura de archivos

```
agente-ia/
├── agent.py                  # Agente principal — orquestador
├── app.py                    # Interfaz Streamlit
├── requirements.txt          # Dependencias Python
├── .env                      # Variables de entorno
├── .env.example              # Ejemplo de configuración
├── services/
│   ├── llm.py                # Servicio LLM (Groq)
│   ├── rag.py                # RAG con FAISS + SentenceTransformers
│   └── web_search.py         # Búsqueda web (SerpAPI)
├── memory/
│   ├── memory_manager.py     # Memoria de corto y largo plazo
│   └── long_term_memory.json # Análisis persistidos
└── utils/
    └── embeddings.py         # Utilidades de embeddings
```

---

## Instalación y ejecución

### Requisitos
- Python 3.11 (para la compatibilidad correcta, muy importante profe, porque dio muchos errores esto jskdjsd)
- Cuenta en [Groq](https://console.groq.com) para obtener API key
- Cuenta en [SerpAPI](https://serpapi.com) para búsqueda web real (preferiblemente usela para evitar errores, las ubicaciones de las api es en ENV.)

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copia `.env.example` como `.env` y completa tus keys:

```bash
cp .env.example .env
```

Edita `.env`:
```
GROQ_API_KEY= gsk_key
SERP_API_KEY= serp_key
```

### 3. Ejecutar la interfaz Streamlit

```bash
python -m streamlit run app.py
```

Abre en tu navegador: http://localhost:8501

---

## 🔧 Componentes técnicos

### LLM — Groq llama-3.3-70b-versatile
Motor de razonamiento principal. Analiza compatibilidad, detecta cuellos de botella y genera recomendaciones técnicas.

### RAG — FAISS + SentenceTransformers
Sistema de recuperación semántica sobre el catálogo de productos. Usa el modelo `all-MiniLM-L6-v2` para generar embeddings y FAISS para búsqueda eficiente.

### Web Search — SerpAPI
Valida la existencia real de los componentes en internet. Si no hay API key, el LLM usa su conocimiento interno.

### Memoria
- **Corto plazo**: historial de mensajes de la sesión (últimos 10 mensajes).
- **Largo plazo**: análisis persistidos en `memory/long_term_memory.json`. Permite recuperar análisis previos sin llamar al LLM.

### Planificador adaptativo (IL2.3)
El agente adapta su plan según los componentes disponibles:
- CPU + GPU → análisis de bottleneck completo
- Solo CPU → análisis centrado en procesador
- Solo GPU → análisis centrado en gráfica
- Sin CPU ni GPU → análisis básico con componentes disponibles

---

## Referencias

- Groq. (2024). *Groq API Documentation*. https://console.groq.com/docs
- LangChain. (2024). *LangChain Documentation*. https://docs.langchain.com
- Meta AI. (2024). *Llama 3 Models*. https://ai.meta.com/llama
- Hugging Face. (2024). *Sentence Transformers*. https://www.sbert.net
- Facebook Research. (2024). *FAISS*. https://faiss.ai
- SerpApi. (2024). *Google Search API*. https://serpapi.com/docs
- Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search with GPUs. *IEEE Transactions on Big Data*, 7(3), 535–547.

---

## Evaluacion 3 contenido nuevo agregado - Observabilidad y trazabilidad 

Esta version agrega una capa de observabilidad:

- Trazas por ejecucion con `trace_id` unico.
- Medicion de latencia total y por paso interno.
- Registro de cache hit, cantidad de componentes, tamano de contexto RAG/web y longitud de respuesta.
- Dashboard Streamlit en la pagina `Observabilidad`.
- Analisis de registros con `scripts/analyze_logs.py`.
- Pruebas unitarias en `tests/test_observability.py`.
- Documentacion de entrega en `docs/evaluacion_3_observabilidad.md`.

### Ejecutar dashboard

```bash
python -m streamlit run app.py
```

Luego abrir la pagina `Observabilidad` desde el menu lateral.

### Analizar logs

```bash
python scripts/analyze_logs.py
```

El script lee `observability_data/traces.jsonl` y genera `observability_data/metrics_summary.json`.

### Ejecutar pruebas

```bash
python -m unittest discover tests
```

### Archivos clave para la entrega

- `observability/tracing.py`: implementacion de metricas y trazas.
- `app.py`: dashboard de observabilidad.
- `agent.py`: pasos instrumentados del agente.
- `docs/evaluacion_3_observabilidad.md`: informe base de la Evaluacion 3.
- `docs/diseno_dashboard.md`: boceto del dashboard.
- `docs/evidencia_pruebas.md`: evidencia y comandos de prueba.
