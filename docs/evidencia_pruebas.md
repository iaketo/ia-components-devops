# Evidencia de pruebas de software

## Validación del pipeline de la Evaluación 2

- PyTest: **18 pruebas aprobadas**, incluyendo catálogo, errores HTTP, selección, análisis, caché, memoria, chat, RAG y las cinco páginas.
- Cobertura de `agent`, `services`, `memory`, `observability` y `utils`: **91,17%**, por encima del mínimo obligatorio de 80%.
- Auditoría: **95 dependencias auditadas**, ninguna omitida y ninguna vulnerabilidad conocida reportada en las versiones instaladas.
- SonarQube: **Quality Gate aprobado**, 0 vulnerabilidades, 0 incidencias críticas y 0 bloqueantes en la revisión final. El gate sí bloqueó una revisión intermedia; el código se corrigió y se volvió a analizar sin desactivar condiciones.
- Docker: imagen construida con TLS verificado y CA pública del proxy del entorno.
- Compose: dos réplicas y gateway Nginx saludables; smoke test funcional aprobado dentro de cada réplica con respuestas externas controladas.
- Workflow: validado con actionlint; el despliegue depende del job obligatorio de pruebas y seguridad.
- Groq real: inferencia aprobada usando `openai/gpt-oss-120b`.
- Embeddings reales: `all-MiniLM-L6-v2` cargado y matriz `(2, 384)` generada.
- Prueba completa `--live`: **fallida por HTTP 503 del catálogo remoto**. Esto no equivale a una prueba aprobada de análisis con catálogo real.

Estas verificaciones se ejecutaron en el entorno local de trabajo. No constituyen evidencia de una ejecución nueva de GitHub Actions; esa ejecución debe comprobarse después de publicar los cambios al repositorio. SonarQube conserva su resultado en `reports/sonarqube.json`, y el pipeline lo sube como artefacto; se exige estado `OK`.

## Pruebas agregadas

Archivo: `tests/test_observability.py`

Casos cubiertos:

- Escritura de una traza en archivo JSONL.
- Generacion de resumen agregado.
- Calculo de tasa de exito.
- Creacion de archivo `summary.json`.
- Tolerancia a lineas JSON corruptas en logs.

## Comandos sugeridos

```bash
python -m pytest tests/ -v
python scripts/smoke_test.py
python scripts/audit_dependencies.py
python -m streamlit run app.py
```

## Resultado esperado

- Las pruebas unitarias deben finalizar en `OK`.
- El analizador debe crear `observability_data/metrics_summary.json`.
- El dashboard debe mostrar KPIs aunque todavia no existan trazas.

## Nota de ejecucion local

El entorno dispone de Python 3.11 y `.venv`; las pruebas indicadas arriba sí se ejecutaron. `scripts/analyze_logs.py` es una herramienta adicional que actualiza el resumen de trazas. El resumen de muestra existente está versionado: preservar sus cambios o usar un directorio de datos separado mediante `APP_DATA_DIR`.
