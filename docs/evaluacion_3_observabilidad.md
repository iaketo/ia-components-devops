# Evaluación Parcial 3: observabilidad y cumplimiento

## Alcance y pauta

Base revisada: `main`, commit `8bf96a9` (EP2 fusionada). Se conservan los tests funcionales, cobertura mínima de 80%, auditoría completa de dependencias, SonarQube temporal, imagen por SHA, dos réplicas, gateway y smoke tests. Se extiende ese pipeline; no se reemplaza.

El objetivo de alcance es aproximadamente 80% de la pauta, no una garantía de nota. Se concentran los cambios en IE1, IE5 e IE6, de 20% cada uno, y en IE3/IE4, de 10% cada uno. IE2 (20%, Kubernetes en nube) queda pendiente: Docker Compose es un entorno simulado, no evidencia de Kubernetes ni de despliegue en nube. No se inventan capturas, resultados ni recursos cloud.

| Indicador | Peso | Implementación/evidencia | Límite |
|---|---:|---|---|
| IE1: monitoreo y logs | 20% | Prometheus descubre cada réplica por DNS; métricas del agente y del proceso; blackbox consulta health del gateway; JSONL y logs stdout con `trace_id` | No hay agregador central de logs; las trazas detalladas se consultan por réplica |
| IE2: orquestación en nube | 20% | Se conserva Compose con dos réplicas y límites de recursos | Pendiente Kubernetes/cloud y validación real en ese entorno |
| IE3: dashboard CI/CD | 10% | Grafana provisionado: cobertura, duración de despliegue, CPU, memoria, errores, latencia y disponibilidad; CI verifica los targets y guarda respuestas | Métricas de CI corresponden al último despliegue en ese stack; no hay historial entre runners efímeros |
| IE4: documentación | 10% | Este procedimiento, mapa del pipeline y tabla operativa | El equipo debe validar la documentación y redactar sus propias conclusiones |
| IE5: cumplimiento | 20% | pip-audit sin omitir dependencias, SonarQube, cobertura >=80%; `scripts/compliance_gate.py` exige reportes completos | No se cambiaron reglas remotas de branch protection; no constituye certificación normativa |
| IE6: bloqueo | 20% | Sin `continue-on-error`; `docker-deploy` requiere `quality`; pruebas negativas ejecutan la política real como proceso y exigen salida 1 | Casos negativos sintéticos, identificados como tales; no se introducen vulnerabilidades reales |

## Flujo CI/CD y trazabilidad

1. `quality` instala las dependencias CPU y ejecuta tests con cobertura y JUnit.
2. Entre los tests, `tests/test_ep3.py` ejecuta el gate con evidencia sintética aprobada y seis variantes rechazadas: cobertura 79%, vulnerabilidad, SonarQube ERROR, paquete omitido, reporte ausente y JSON corrupto. Si el gate acepta un caso negativo, falla pytest y se bloquea el despliegue.
3. La auditoría real de dependencias y SonarQube mantienen sus bloqueos originales. Después, `compliance_gate.py` verifica sus reportes reales junto con `coverage.xml`. Error de formato, ausencia de evidencia o incumplimiento devuelve 1. El reporte queda en `reports/compliance.json`.
4. Se conserva `quality-<SHA>` incluso ante fallas. Incluye JUnit, cobertura, auditoría, SonarQube y `negative-gate-tests/*.json`. Los reportes de prueba negativa se separan de los de análisis real.
5. `docker-deploy`, con `needs: quality`, descarga la cobertura de ese mismo workflow/commit. Valida Prometheus con `promtool`, construye la imagen por SHA y despliega dos réplicas, gateway y el complemento de monitoreo.
6. El reloj comienza inmediatamente antes de `compose up`. Después de health y smoke de ambas réplicas, `ci_metrics.py` convierte la cobertura XML y los segundos transcurridos a formato Prometheus. La duración incluye el arranque del stack y los smoke tests; excluye construcción de imagen y validación externa opcional.
7. `curl --fail` publica estas métricas en Pushgateway. `check_monitoring.py` exige dos targets de aplicación UP, sonda HTTP exitosa, cobertura >=80 y duración válida consultando Prometheus; Grafana debe responder y tener el dashboard provisionado. Cualquier fallo bloquea el job.
8. `deployment-<SHA>` conserva métricas, consultas reales de monitoreo, dashboard JSON, salud de Grafana, contenedores, logs y revisión de imagen. El stack y sus volúmenes se eliminan al finalizar el runner.

No se suprimen vulnerabilidades ni se baja la cobertura. SonarQube sigue bloqueando vulnerabilidades y violaciones críticas/blocker. Los controles protegen este pipeline; impedir pushes directos o merges sin checks requiere reglas de GitHub adicionales, pendientes de configuración del equipo.

## Ejecutar y consultar

Requiere Docker Compose y las dependencias de desarrollo si se ejecutan scripts/tests en el host.

```bash
# Shell desde la raíz del repositorio; conserva la opción básica de EP2.
export COMPOSE_FILE=docker-compose.yml:docker-compose.monitoring.yml
export VCS_REF="$(git rev-parse HEAD)"
export APP_IMAGE="gmcomponents-ev2:$VCS_REF"
docker compose config --quiet
docker compose run --rm --no-deps --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
docker compose build gmcomponents
DEPLOY_STARTED_AT=$(date +%s)
docker compose up -d --no-build --scale gmcomponents=2 --wait --wait-timeout 180
curl --fail http://127.0.0.1:8501/_stcore/health
docker compose exec -T --index 1 gmcomponents python scripts/smoke_test.py
docker compose exec -T --index 2 gmcomponents python scripts/smoke_test.py
# coverage.xml debe ser el reporte real de tests de esta revisión.
python scripts/ci_metrics.py --coverage coverage.xml --deployment-seconds "$(( $(date +%s) - DEPLOY_STARTED_AT ))"
curl --fail --data-binary @reports/ci-metrics.prom http://127.0.0.1:9091/metrics/job/gmcomponents-ci
python scripts/check_monitoring.py
```

- Aplicación y trazas: [Streamlit](http://127.0.0.1:8501), página Observabilidad.
- [Grafana EP3](http://127.0.0.1:3000/d/gmcomponents-ep3): provisionado automáticamente, acceso anónimo Viewer exclusivamente en loopback.
- [Prometheus](http://127.0.0.1:9090): consultar targets, series y alertas.
- [Pushgateway](http://127.0.0.1:9091): recibe evidencia de CI. No se publica fuera de loopback.

No cambiar esos bindings a interfaces públicas sin autenticación. El exporter interno 9100 no publica puerto en el host. Su arranque ocurre en `scripts/run_app.py`, antes de recibir sesiones Streamlit; cada proceso mantiene sus propias series. Las etiquetas solo contienen estados de cardinalidad acotada, no IDs de trazas, consultas, respuestas o secretos.

Para registrar ejecuciones de la aplicación, analizar un carrito en Streamlit. Las métricas de errores/latencia necesitan ejecuciones y varias muestras; ausencia de datos no equivale a cero fallas. Los smoke tests corren en procesos aparte y no incrementan los contadores del proceso web.

```bash
# Logs operativos correlacionados (event, trace_id, ok, duration_ms).
docker compose logs --no-color gmcomponents
# Detalle de trazas por réplica: contienen contexto y errores, tratar como datos privados.
docker compose exec -T --index 1 gmcomponents cat /data/observability_data/traces.jsonl
docker compose exec -T --index 2 gmcomponents cat /data/observability_data/traces.jsonl
# Limpieza del entorno local, elimina también el historial de monitoreo.
docker compose down --volumes --remove-orphans
```

Cada réplica conserva su propio volumen anónimo `/data`; el dashboard Streamlit muestra la réplica que atiende esa sesión. Prometheus agrega ambas y retiene siete días mientras se conserve su volumen. Grafana consulta Prometheus mediante una fuente de datos provisionada con UID estable.

## Métricas y lectura operativa

| Señal | Fuente real | Comprobación operativa sugerida |
|---|---|---|
| Disponibilidad | `probe_success` del health HTTP del gateway | Revisar gateway, salud y logs de réplicas si vale 0; no demuestra que Groq esté operativo |
| Exporters disponibles | `up{job="gmcomponents"}` por IP | Comprobar proceso exporter y red si falta una réplica |
| CPU | `rate(process_cpu_seconds_total[1m])` | Revisar carga del proceso Python; no equivale a CPU del nodo ni de todos los procesos del contenedor |
| Memoria | `process_resident_memory_bytes` | Comparar memoria del proceso con el límite de 2 GiB por réplica; revisar embeddings/cache |
| Errores | `gm_agent_runs_total{status="error"}` | Localizar `trace_id` en stdout y JSONL; no cuenta errores recuperados que no finalizan la ejecución como fallida |
| Latencia P95 | Histograma `gm_agent_duration_seconds` | Consultar pasos de la traza para localizar la operación lenta |
| Cobertura | `gm_ci_test_coverage_percent` desde XML | El gate exige >=80%; revisar reporte por módulo, no solo el total |
| Duración despliegue | `gm_ci_deployment_duration_seconds` | Comparar arranque/smoke con evidencia anterior; el tiempo de build se observa en Actions |

Hay reglas de alerta para gateway caído 30 s, exporter caído 30 s y errores del agente en cinco minutos. Se evalúan y visualizan en Prometheus; no hay Alertmanager ni envío de notificaciones externas.

## Demostrar el bloqueo sin comprometer el proyecto

```bash
python -m pytest tests/test_ep3.py -v
# Después de los análisis reales del pipeline:
python scripts/compliance_gate.py
```

`reports/negative-gate-tests/` muestra la salida 0 del caso sano y la salida 1 de los seis casos negativos. Son pruebas controladas, no evidencia de una vulnerabilidad real detectada. El JUnit documenta que las aserciones se ejecutaron. El workflow usa el mismo script de gate y no ejecuta `docker-deploy` si `quality` falla. Una demostración adicional de un workflow completo intencionalmente rojo en una rama descartable queda pendiente; no se rompe `main` para obtener esa captura.

## Pendientes de entrega y límites

- IE2: elegir proveedor, credenciales, cluster y registro; desplegar en Kubernetes cloud y verificar observabilidad allí. No hay infraestructura cloud creada.
- Agregación de logs, retención de trazas entre réplicas/runners y persistencia del historial CI entre ejecuciones.
- Alertmanager, notificaciones y validación de carga. Los límites configurados no son prueba de capacidad.
- Reglas remotas de branch protection y revisión del alcance normativo aplicable.
- El equipo debe adjuntar evidencia del nuevo workflow en GitHub, revisar los cambios y escribir sus reflexiones individuales y justificaciones técnicas propias.

## Validación de esta implementación

- Python 3.11: 33 pruebas aprobadas y cobertura agregada 94,49%, usando el mismo comando y umbral que CI.
- Prueba HTTP del exporter: se generan ejecuciones exitosa/fallida, se consultan contadores e histograma y se verifica que stdout no publique metadata ni mensajes de error privados.
- Política: caso sano aprobado y seis escenarios negativos rechazados con código 1.
- `docker compose config --quiet` y `promtool check config`: correctos, incluidas las tres reglas de alerta.
- Auditoría local completa: 96 dependencias, sin vulnerabilidades conocidas después de actualizar cuatro paquetes antiguos y Streamlit a una versión compatible con Pillow 13. Se fijan esos mínimos corregidos en requirements; no se omiten controles para lograrlo.
- El entorno local tiene disco limitado y Docker con almacenamiento VFS; la construcción completa y el arranque conjunto no pudieron completarse allí por falta de espacio. La validación definitiva del Dockerfile, SonarQube y el stack corresponde al workflow del commit publicado, cuyos resultados y artefactos se consultan en GitHub Actions. Un pipeline anterior verde no valida estos cambios.

## Declaración de IA

Se utilizó Codex (OpenAI) para revisar el código y la pauta, implementar la instrumentación, configuración, scripts y pruebas, y preparar documentación operativa. El equipo debe revisar y validar este material antes de entregarlo. No se generaron conclusiones, justificaciones técnicas personales ni reflexiones individuales; las existentes no se modifican. Referencia: [Uso de IA, Bibliotecas Duoc UC](https://bibliotecas.duoc.cl/ia).
