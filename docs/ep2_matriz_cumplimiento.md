# EP2 — Matriz de cumplimiento y evidencias

## Referencia de evaluación

La EP2 se revisa con cinco indicadores de igual ponderación (20 % cada uno). Los apartados siguientes describen qué está implementado en este repositorio y cómo comprobarlo. La nota definitiva corresponde a la evaluación del docente.

| Indicador | Implementación comprobable | Evidencia |
| --- | --- | --- |
| IE1: Contenedores optimizados (20 %) | `Dockerfile` basado en Python slim, PyTorch para CPU, ejecución sin root, healthcheck y límites de CPU/memoria/procesos en Compose | `Dockerfile`, `docker-compose.yml`, build del workflow |
| IE2: Pruebas automatizadas (20 %) | PyTest con prueba del flujo del agente, selección, RAG, memoria, búsqueda, UI y observabilidad; cobertura mínima bloqueante del 80 % | `tests/`, `scripts/smoke_test.py`, reporte JUnit y `coverage.xml` |
| IE3: Seguridad y escalabilidad (20 %) | Auditoría de paquetes instalados con `pip-audit`, SonarQube con Quality Gate, usuarios sin privilegios, filesystem de solo lectura, `cap_drop`, `no-new-privileges`; escalado horizontal con Compose | `scripts/audit_dependencies.py`, `scripts/sonarqube_gate.py`, `docker-compose.yml` |
| IE4: Despliegue y trazabilidad (20 %) | Build ligado al SHA del commit, condición `needs: quality`, dos réplicas iniciadas y validadas en GitHub Actions, evidencias guardadas por commit | Workflow `.github/workflows/ci.yml`, artefactos `quality-<SHA>` y `deployment-<SHA>` |
| IE5: Orquestación (20 %) | Docker Compose coordina Streamlit y un gateway Nginx, healthchecks, dependencia de servicios y escalado a dos o más réplicas | `docker-compose.yml`, `deploy/nginx.conf`, smoke tests en cada instancia |

## Ejecución verificada

- **Repositorio:** `iaketo/ia-components-devops`
- **Commit verificado en `main`:** `2e21b6c7a904725d1917237df13a4a54adf780c3`
- **Ejecución:** [GitHub Actions #38648028707](https://github.com/iaketo/ia-components-devops/actions/runs/38648028707)
- **Pruebas:** 18 casos aprobados; cobertura **91,17 %** (mínimo exigido por el workflow: 80 %).
- **Dependencias:** `pip-audit` sin vulnerabilidades conocidas en la ejecución indicada.
- **Código:** SonarQube Quality Gate aprobado.
- **Orquestación:** job de despliegue simulado completado, dos réplicas y gateway probados; artefactos de calidad y despliegue disponibles en esa ejecución.

## Alcance y precauciones

La ejecución en GitHub Actions es **temporal**: no publica el sistema en internet ni demuestra disponibilidad 24/7. La persistencia de cada réplica es independiente. El smoke test estándar simula servicios externos; la validación real del catálogo y Groq requiere secretos válidos y ejecutar manualmente el workflow con `live_validation=true`.

La aprobación de los checks no equivale a autorización de producción ni sustituye las pruebas funcionales que pueda pedir el profesor. Es conveniente mostrar el resultado de un run ejecutado sobre **el commit exacto que se entregue**, especialmente después de agregar pruebas o dependencias.

## Pruebas adicionales incorporadas desde el trabajo del equipo

- `tests/test_memory_manager.py`: límite del historial corto, persistencia y recuperación del análisis más reciente, lectura segura de JSON inválido.
- `tests/test_web_search.py`: respuesta sin clave de SerpAPI, límite de resultados, tolerancia a errores de red.

Se agregan de forma complementaria y sin reemplazar el pipeline ni la arquitectura existentes.
