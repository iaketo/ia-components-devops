# Boceto de dashboard de observabilidad

## Vista principal

```text
+------------------------------------------------------------+
| Observabilidad del Agente                                  |
| Trazas, metricas y evidencia de ejecucion                  |
+--------------+--------------+--------------+---------------+
| Ejecuciones  | Exito        | Latencia     | Cache hit     |
| 12           | 91.7%        | 2450 ms      | 33.3%         |
+--------------+--------------+--------------+---------------+
| Pasos mas costosos                                         |
| step              avg_duration_ms   runs   errors          |
| llm_sintesis      2100              8      0               |
| web_search        480               6      1               |
+------------------------------------------------------------+
| Ultimas trazas                                             |
| trace_id | inicio | operacion | ok | duracion | error      |
+------------------------------------------------------------+
| Recomendaciones operativas                                 |
| - Revisar latencia del LLM y cachear respuestas frecuentes |
+------------------------------------------------------------+
```

## Criterios de diseno

- KPIs arriba para lectura rapida.
- Tabla de pasos internos para diagnostico tecnico.
- Ultimas trazas para auditoria de ejecuciones.
- JSON expandible para inspeccion detallada sin saturar la pantalla.
- Recomendaciones automaticas basadas en umbrales simples y explicables.


## Dashboard operativo EP3

El dashboard real de Grafana se versiona en `monitoring/grafana/dashboards/ep3.json`, con UID `gmcomponents-ep3` y fuente Prometheus provisionada. Incluye disponibilidad HTTP, réplicas UP, cobertura, duración de despliegue, CPU y memoria del proceso por réplica, errores, latencia P95, ejecuciones por estado y fecha de publicación de CI.

La página Streamlit anterior se conserva para investigar trazas detalladas. Grafana agrega series de las dos réplicas; no agrega sus archivos JSONL. Los paneles muestran ausencia de datos hasta recibir muestras reales. Consultar `docs/evaluacion_3_observabilidad.md` para reproducir la integración, interpretar métricas y revisar sus límites.
