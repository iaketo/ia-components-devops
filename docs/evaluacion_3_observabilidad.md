# Evaluación Parcial 3: observabilidad y cumplimiento

## Acceso a los servicios y reportes

El [índice de servicios y paneles](../monitoring/README.md) reúne los accesos a Grafana, Prometheus, logs, alertas y Kubernetes, con instrucciones para Windows y ejecución manual en GitHub. Los paquetes nuevos están numerados y contienen `ABRIR-RESUMEN.html` para abrir las evidencias en el navegador, además de `REVISION.json` para identificar el commit y la ejecución. Los artefactos de ejecuciones antiguas conservan los prefijos `quality-`, `deployment-`, `kubernetes-` y `blocking-demo-`.

## Alcance y pauta

Base revisada: `main`, commit `5409e88` (EP3 parcial sobre EP2 fusionada). Se conservan los tests funcionales, cobertura mínima de 80%, auditoría completa de dependencias, SonarQube temporal, imagen por SHA, dos réplicas, gateway y smoke tests. Se extiende ese pipeline; no se reemplaza.

El alcance ahora cubre los seis indicadores. El destino autorizado es Kubernetes real con kind en una VM cloud efímera de GitHub Actions. No es EKS/GKE/AKS ni infraestructura permanente. La calificación corresponde al docente; esta descripción distingue despliegue académico verificado de operación productiva continua.

| Indicador | Peso | Implementación/evidencia |
|---|---:|---|
| IE1: monitoreo y logs | 20% | Prometheus por réplica, sonda HTTP, métricas del proceso y agente; Alloy recoge stdout de ambos pods y Loki centraliza logs correlacionados por `trace_id` |
| IE2: orquestación cloud | 20% | El runner cloud crea Kubernetes kind, carga la imagen del mismo SHA, aplica manifiestos y ConfigMaps, espera readiness y verifica ambos pods, monitoreo y recuperación |
| IE3: dashboard CI/CD | 10% | Grafana provisionado con cobertura, despliegue, CPU, memoria, errores, P95, logs y alertas; métricas CI provienen de cobertura y tiempos reales |
| IE4: documentación | 10% | Este procedimiento y el mapa operativo del pipeline, métricas y evidencias; las reflexiones personales corresponden al equipo |
| IE5: cumplimiento | 20% | Auditoría completa pip-audit, SonarQube, cobertura >=80%, gate que rechaza evidencia ausente/inválida y comprobaciones de contenedores Kubernetes restringidos |
| IE6: bloqueo | 20% | `needs: quality` sin omitir errores; pruebas negativas y workflow dedicado que queda rojo intencionalmente y omite su job de despliegue |

## Flujo CI/CD y trazabilidad

1. `quality` instala las dependencias CPU y ejecuta tests con cobertura y JUnit. `normalize_coverage.py` regenera el XML a partir de las mismas mediciones, con rutas relativas inequívocas para SonarQube y el mismo umbral >=80%; no altera líneas ejecutadas ni elimina archivos.
2. Entre los tests, `tests/test_ep3.py` ejecuta el gate con evidencia sintética aprobada y seis variantes rechazadas: cobertura 79%, vulnerabilidad, SonarQube ERROR, paquete omitido, reporte ausente y JSON corrupto. Si el gate acepta un caso negativo, falla pytest y se bloquea el despliegue.
3. La auditoría real de dependencias y SonarQube mantienen sus bloqueos originales. Después, `compliance_gate.py` verifica sus reportes reales junto con `coverage.xml`. Error de formato, ausencia de evidencia o incumplimiento devuelve 1. El reporte queda en `reports/compliance.json`.
4. Se conserva `01-Pruebas-y-seguridad` incluso ante fallas. Incluye JUnit, cobertura, auditoría, SonarQube y `negative-gate-tests/*.json`. Los reportes de prueba negativa se separan de los de análisis real.
5. `docker-deploy`, con `needs: quality`, descarga la cobertura de ese mismo workflow/commit. Valida Prometheus con `promtool`, construye la imagen por SHA y despliega dos réplicas, gateway y el complemento de monitoreo.
6. El reloj comienza inmediatamente antes de `compose up`. Después de health y smoke de ambas réplicas, `ci_metrics.py` convierte la cobertura XML y los segundos transcurridos a formato Prometheus. La duración incluye el arranque del stack y los smoke tests; excluye construcción de imagen y validación externa opcional.
7. `curl --fail` publica estas métricas en Pushgateway. `check_monitoring.py` exige dos targets de aplicación UP, sonda HTTP exitosa, cobertura >=80 y duración válida consultando Prometheus; Grafana debe responder y tener el dashboard provisionado. Cualquier fallo bloquea el job.
8. `02-Graficos-y-metricas-locales` conserva la evidencia Compose. Ese stack se elimina antes de crear Kubernetes para liberar puertos y memoria.
9. kind crea un clúster Kubernetes 1.34.0 en el mismo runner cloud. `kind load docker-image` carga la imagen ya construida y verificada. No se reconstruye otro código para Kubernetes.
10. `deploy_kubernetes.sh` aplica recursos y configuración, espera todos los despliegues y abre túneles locales de diagnóstico. La imagen se identifica por SHA; el Deployment registra esa revisión en una anotación. La aplicación no necesita acceso a la API de Kubernetes. Solo Alloy usa un ServiceAccount con permisos de lectura de pods/logs en el namespace.
11. Los smoke tests se repiten dentro de ambos pods. La cobertura y el tiempo de despliegue Kubernetes se publican en su Pushgateway; `check_monitoring.py` verifica la recepción real por Prometheus.
12. `check_kubernetes.py` exige contadores/histogramas, recursos y logs de ambos pods, dashboard y fuentes Prometheus/Loki. Escala el gateway a cero, comprueba sonda fallida, alerta crítica y recepción en Alertmanager; luego restaura el gateway. Elimina un pod de aplicación y exige su reemplazo por uno con otro UID, dos pods listos y dos exporters UP.
13. `03-Kubernetes-graficos-logs-y-alertas` conserva recursos, versión del clúster, eventos, logs y `runtime-verification.json`, incluidos tiempos observados y entorno de ejecución. El clúster se elimina incluso si una comprobación falla.

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

No cambiar esos bindings a interfaces públicas sin autenticación. El exporter interno 9100 no publica puerto en el host. Su arranque ocurre en `scripts/run_app.py`, antes de recibir sesiones Streamlit; cada proceso mantiene sus propias series. Las etiquetas solo contienen estados y `source=app|self_test`, de cardinalidad acotada; no IDs de trazas, consultas, respuestas o secretos.

Para registrar ejecuciones de la aplicación, analizar un carrito en Streamlit. Las métricas de errores/latencia necesitan ejecuciones y varias muestras; ausencia de datos no equivale a cero fallas. Los smoke tests corren en procesos aparte y no incrementan los contadores del proceso web. Para validar la cadena de observabilidad del propio proceso web, CI activa `OBSERVABILITY_SELF_TEST=true` únicamente en Kubernetes. Cada pod registra una ejecución sintética exitosa y otra fallida. Sus series llevan `source=self_test` y los logs `operation=observability_self_test`; los paneles operativos y la alerta de errores filtran `source=app`. La opción está desactivada por defecto y no añade endpoints de inyección de errores.

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

Las cinco pruebas de reglas (`monitoring/alerts.test.yml`) verifican espera de 30 s, desaparición de todos los targets, pérdida de una réplica, primer error real y exclusión de errores sintéticos. Los contadores publican cero desde el arranque para permitir detectar el primer incremento. Hay reglas para gateway caído 30 s, menos de dos exporters durante 30 s (también si desaparecen todos los targets) y errores del agente en cinco minutos. En Kubernetes Prometheus las entrega a Alertmanager y el ensayo de caída verifica esa recepción. El receptor es local, visible por API/UI; no envía correos ni mensajes a terceros.

## Demostrar el bloqueo sin comprometer el proyecto

```bash
python -m pytest tests/test_ep3.py -v
# Después de los análisis reales del pipeline:
python scripts/compliance_gate.py
```

`reports/negative-gate-tests/` muestra la salida 0 del caso sano y la salida 1 de los seis casos negativos. Son pruebas controladas, no evidencia de una vulnerabilidad real detectada. El JUnit documenta que las aserciones se ejecutaron. El workflow usa el mismo script de gate y no ejecuta `docker-deploy` si `quality` falla. Además, `.github/workflows/blocking-demo.yml` ejecuta el gate real en un job con evidencia sintética claramente marcada. Ese job debe fallar y su dependiente `deployment` debe quedar `skipped`. Se ejecuta en `verification/ep3-critical-block` o mediante `workflow_dispatch`; no introduce vulnerabilidades en la aplicación. Que esta demostración quede roja es el resultado esperado, separado del CI normal verde de `main`.

```bash
# Ejecución manual de la demostración en la rama de verificación:
gh workflow run blocking-demo.yml --ref verification/ep3-critical-block -f scenario=vulnerability
# También admite coverage y sonar.
```

## Reproducir Kubernetes

Los binarios kind 0.30.0, kubectl 1.34.0 y Docker deben estar disponibles. El workflow instala las versiones declaradas. Desde la raíz, con una imagen ya construida del commit:

```bash
kind create cluster --name gmcomponents --image kindest/node:v1.34.0 --config deploy/kubernetes/kind.yaml --wait 120s
kind load docker-image "$APP_IMAGE" --name gmcomponents
# false por defecto para uso normal. CI usa true para probar telemetría explícita.
EP3_SELF_TEST=true bash scripts/deploy_kubernetes.sh
# Ejecutar smoke en ambos pods y generar/publicar métricas CI como hace el workflow.
python scripts/check_monitoring.py --output reports/kubernetes/monitoring.json
python scripts/check_kubernetes.py
bash scripts/collect_kubernetes.sh
kind delete cluster --name gmcomponents
```

`check_kubernetes.py` provoca una caída controlada y elimina un pod: utilizarlo exclusivamente en el entorno de evaluación. El dashboard Kubernetes tiene UID `gmcomponents-kubernetes`, disponible mediante el túnel en `http://127.0.0.1:3000/d/gmcomponents-kubernetes`. Los servicios son ClusterIP/headless; no se crea LoadBalancer ni exposición pública. Los túneles son locales al runner y desaparecen al finalizarlo.

Los Deployments usan readiness/liveness/startup probes, límites de CPU/memoria, usuario no root, filesystem de solo lectura, `seccomp: RuntimeDefault`, capacidades eliminadas y `allowPrivilegeEscalation=false`. El namespace impone Pod Security Restricted. La memoria y los datos temporales usan `emptyDir`: reiniciar un pod no conserva su estado. Prometheus/Loki tienen retención configurada de siete días mientras dure el entorno; GitHub conserva los artefactos después de eliminar el clúster.

## Límites y validación

- El clúster cloud es efímero y pertenece al runner de GitHub Actions, destino autorizado para esta entrega. No se crea infraestructura permanente ni se requieren cuentas de AWS/Azure/GCP.
- Los archivos de trazas/memoria de cada pod y el historial interno de Prometheus/Loki no sobreviven al clúster; los artefactos conservan evidencia de auditoría. Producción continua requeriría volúmenes persistentes, respaldos y retención externa.
- La validación funcional de CI usa servicios externos simulados de manera explícita; FAISS, memoria, aplicación, contenedores, Kubernetes, métricas y logs son reales. La opción `live_validation` previa se conserva para exigir catálogo/embeddings/Groq reales cuando se proporcione el secreto correspondiente en Actions.
- También pasó el smoke local con catálogo, embeddings y Groq reales, usando `GROQ_MODEL=openai/gpt-oss-120b`. Se verificaron FAISS, análisis, caché, chat y cinco páginas. `GROQ_MODEL` es un identificador de modelo; `GROQ_API_KEY` es la credencial. El código rechaza una clave colocada en la variable de modelo sin mostrar su contenido.
- No se configuraron reglas remotas de branch protection ni se declara certificación normativa. El cumplimiento de esta evaluación se implementa mediante scripts y gates automatizados; las conclusiones/reflexiones individuales deben escribirlas los integrantes.
- Validación local: 38 pruebas aprobadas, cobertura 94,67%, análisis de configuración y auditoría de dependencias. El resultado definitivo del despliegue corresponde al workflow del commit publicado. Revisar los artefactos `01-Pruebas-y-seguridad`, `02-Graficos-y-metricas-locales`, `03-Kubernetes-graficos-logs-y-alertas` y el workflow negativo independiente; un pipeline anterior verde no valida estos cambios.

## Declaración de IA

Se utilizó Codex (OpenAI) para revisar el código y la pauta, implementar la instrumentación, configuración, scripts y pruebas, y preparar documentación operativa. El equipo debe revisar y validar este material antes de entregarlo. No se generaron conclusiones, justificaciones técnicas personales ni reflexiones individuales; las existentes no se modifican. Referencia: [Uso de IA, Bibliotecas Duoc UC](https://bibliotecas.duoc.cl/ia).
