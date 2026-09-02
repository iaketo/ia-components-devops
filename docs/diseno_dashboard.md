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
