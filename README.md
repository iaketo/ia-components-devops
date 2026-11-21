# GM Components — DevOps, CI/CD y observabilidad (EV2 y EV3)

La aplicación Streamlit analiza compatibilidad de hardware usando el catálogo de GM Components, FAISS, embeddings y Groq. El pipeline prueba la aplicación, audita dependencias, analiza el código con SonarQube y verifica dos réplicas en Docker Compose. Después despliega la misma imagen en Kubernetes real con kind dentro de un runner cloud efímero de GitHub Actions, con métricas, logs centralizados, dashboards y pruebas controladas de recuperación.

## Ejecutar y probar localmente

Requisitos: Python 3.11, Docker con BuildKit y Docker Compose 2.24 o posterior. No requiere GPU.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.14.1+cpu'
python -m pip install -r requirements-dev.txt
python -m pip check
python -m pytest tests/ -v --cov=agent --cov=services --cov=memory --cov=observability --cov=utils --cov-report=xml:coverage.xml --cov-fail-under=80
python scripts/normalize_coverage.py
python scripts/smoke_test.py
```

El smoke test predeterminado controla las respuestas externas para ejecutarse sin secretos ni descargar modelos. Ejecuta el código real de selección, FAISS, análisis, caché, memoria, trazas, chat y las cinco páginas con Streamlit AppTest. Esta simulación **no certifica acceso a Groq ni la calidad del modelo de embeddings**.

Para usar la aplicación, configura `GROQ_API_KEY` de forma segura en el entorno o en un `.env` local ignorado por Git. `SERP_API_KEY` es opcional: sin ella hay un fallback informativo. Las variables inyectadas tienen prioridad sobre `.env`. No se usan claves `dummy`.

```bash
python scripts/run_app.py
python scripts/smoke_test.py --live
```

La validación `--live` exige un catálogo no vacío, embeddings reales, recuperación FAISS, un análisis y un chat con Groq, caché y navegación de la interfaz. Termina con código distinto de cero ante un fallo. Requiere HTTPS a `gmcomponents.onrender.com`, `api.groq.com`, `huggingface.co` y sus destinos Xet; la búsqueda opcional usa `serpapi.com`.

El modelo se selecciona con `GROQ_MODEL` y por defecto usa `openai/gpt-oss-120b`. La clave se configura en `GROQ_API_KEY`; una clave colocada por error en la variable del modelo se rechaza sin mostrar su contenido. `METRICS_ENABLED=true python scripts/run_app.py` habilita también el exporter local en el puerto 9100. El modelo anterior `llama-3.3-70b-versatile` ya no apareció en el listado de modelos de Groq durante esta validación; no basta con tener una clave para usar un modelo retirado.

## Construcción, orquestación y escalado

```bash
export VCS_REF="$(git rev-parse HEAD)"
export APP_IMAGE="gmcomponents-ev2:$VCS_REF"
docker compose config --quiet
docker compose build gmcomponents
docker compose up -d --no-build --scale gmcomponents=2 --wait --wait-timeout 180
curl --fail http://127.0.0.1:8501/_stcore/health
docker compose exec -T --index 1 gmcomponents python scripts/smoke_test.py
docker compose exec -T --index 2 gmcomponents python scripts/smoke_test.py
docker compose ps
```

El gateway Nginx publica un único puerto y distribuye peticiones a las réplicas, incluyendo WebSockets de Streamlit. La afinidad por IP ayuda a conservar las sesiones; no sustituye una sesión distribuida ni garantiza conservarla al cambiar réplicas. `APP_PORT` permite cambiar el puerto publicado. Para ajustar la capacidad:

```bash
docker compose up -d --no-build --scale gmcomponents=3 --wait
```

Cada réplica tiene límites de 1 CPU, 2 GiB y 128 procesos; el gateway tiene 0,25 CPU y 128 MiB. No hay nombres fijos de contenedor ni puertos del host por réplica. Los procesos corren sin privilegios, con filesystem de solo lectura, capacidades eliminadas y `no-new-privileges`. La escritura de memoria, trazas y caché se limita a `/data`, y temporales a `/tmp`.

Los volúmenes de `/data` son independientes por réplica: este despliegue simulado no ofrece memoria compartida entre instancias. `docker compose stop` y `start` conservan el estado de los contenedores existentes; recrearlos no garantiza recuperar el mismo volumen anónimo. Un despliegue persistente requiere diseñar almacenamiento compartido/transaccional antes de ofrecer memoria global.

```bash
docker compose down --volumes --remove-orphans
```

El comando anterior limpia el entorno simulado y elimina sus datos. No usarlo si se necesitan conservar esos datos.

### TLS en entornos con proxy

El Dockerfile verifica TLS siempre. Si el proxy usa una CA privada, pasa su **certificado público** mediante un secreto de BuildKit; no pases claves privadas ni tokens:

```bash
docker build --secret id=cloud_ca,src=/etc/ssl/certs/ca-certificates.crt --build-arg VCS_REF="$VCS_REF" -t "$APP_IMAGE" .
```

El bundle agrega confianza a las CA del sistema y permite verificar pip, Requests, HTTPX y Hugging Face. En GitHub Actions, sin proxy privado, se construye sin ese parámetro. No usar `--trusted-host`, `verify=False` ni desactivar verificaciones.

## Etapas, calidad, seguridad y trazabilidad

El workflow `.github/workflows/ci.yml` corre en pushes y PR hacia `main`/`develop`, y admite ejecución manual.

| Etapa | Comprobación | Bloqueo |
|---|---|---|
| Pruebas | Casos de catálogo, HTTP, selección, RAG, análisis, caché, memoria, chat y UI; cobertura mínima 80% de los módulos medidos | Pruebas fallidas o cobertura insuficiente |
| Dependencias | `scripts/audit_dependencies.py` consulta pip-audit sobre todas las versiones instaladas | Cualquier vulnerabilidad conocida, dependencia no auditada o error de auditoría |
| Código | SonarQube Community temporal, con credenciales aleatorias y análisis Python | Cualquier vulnerabilidad, incidencia crítica o bloqueante, o fallo del análisis |
| Cumplimiento | `scripts/compliance_gate.py` exige cobertura >=80%, auditoría completa sin vulnerabilidades y SonarQube OK | Reportes ausentes, inválidos o con incumplimientos |
| Compose | Imagen identificada por SHA, dos réplicas y Nginx; healthcheck más smoke test funcional en cada réplica | Fallo de construcción, arranque, gateway o funcionalidad |
| Kubernetes | kind 0.30.0, Kubernetes/kubectl 1.34.0, misma imagen por SHA y dos pods | Fallo de despliegue, readiness o smoke test de cualquier pod |
| Observabilidad | Prometheus, Grafana, Loki, Alloy y Alertmanager; consultas reales y ensayos controlados de caída/reposición | Telemetría incompleta, alertas no recibidas o recuperación fallida |

El job de despliegue tiene `needs: quality`: no se ejecuta si falla alguna comprobación de calidad/seguridad. No hay `continue-on-error` en esos controles. Un fallo crítico impide construir/desplegar la nueva versión. Las alertas operativas se evalúan en Prometheus y se reciben en Alertmanager dentro del laboratorio Kubernetes.

Dependabot revisa semanalmente dependencias Python, Docker y GitHub Actions mediante `.github/dependabot.yml`. Su configuración produce propuestas de actualización; no reemplaza el análisis bloqueante del pipeline. Las dependencias sin uso (CrewAI, LangChain, Flask y otras) se retiraron del entorno para reducir la superficie de dependencias; la aplicación usa Groq directamente.

Para ejecutar la auditoría local: `python scripts/audit_dependencies.py`. El identificador del wheel oficial `torch==2.14.1+cpu` se consulta como la versión base `2.14.1` en la base de advisories; esto no cambia el artefacto instalado ni su verificación. Así no se omite PyTorch por no existir una distribución `+cpu` en PyPI.

SonarQube se crea por ejecución, solo publica en loopback, cambia la contraseña inicial, analiza, espera el Quality Gate y elimina servidor y volúmenes al terminar. No requiere `SONAR_TOKEN` del equipo. La condición de seguridad usa todos los resultados de la ejecución, sin suprimir vulnerabilidades. El historial del servidor temporal no persiste: los reportes se conservan como artefactos de Actions.

La imagen se etiqueta con `${{ github.sha }}` y lleva la etiqueta OCI `org.opencontainers.image.revision`. Los artefactos `quality-<SHA>` contienen JUnit, cobertura y auditorías; `deployment-<SHA>` contiene el ID de imagen, commit, estado de contenedores y logs; `kubernetes-<SHA>` conserva versión del clúster, recursos, eventos, logs y verificaciones de telemetría, alertas y recuperación. Esto vincula código, controles y despliegue de la misma ejecución. La imagen se carga directamente en kind con `kind load docker-image`. No se publica en un registry ni se crea un entorno productivo permanente. Compose se elimina antes de crear el clúster para liberar recursos y puertos; el clúster también se elimina al finalizar.

Para validar los servicios reales desde Actions, crea el secreto de repositorio `GROQ_API_KEY` (y opcionalmente `SERP_API_KEY`) en Settings → Secrets and variables → Actions. Ejecuta manualmente CI-CD con `live_validation=true`. La ejecución falla si falta la clave o fallan los servicios; no se omite silenciosamente esa comprobación. Los PR y el despliegue simulado estándar no reciben secretos ni dependen de servicios externos.

Configura además una regla de protección para `main` y `develop` que exija PR y los checks del workflow antes del merge. El README describe esa política; su aplicación debe verificarse en Settings del repositorio, no se obtiene solo con este archivo.

Referencias: [Dependabot](https://docs.github.com/en/code-security/dependabot), [SonarQube](https://docs.sonarsource.com/sonarqube-server/), [pip-audit](https://github.com/pypa/pip-audit), [Docker Compose](https://docs.docker.com/compose/).

## Evaluación Parcial 3: revisión de requisitos

| Indicador de la pauta | Peso | Implementación y evidencia | Alcance o condición |
|---|---:|---|---|
| IE1: monitoreo, logs, uso, errores y disponibilidad | 20% | Prometheus por réplica, Blackbox Exporter, trazas JSONL y logs centralizados con Alloy/Loki | Los recursos medidos son del proceso Python; los registros se correlacionan por `trace_id` |
| IE2: despliegue orquestado en nube | 20% | Dos pods y observabilidad desplegados automáticamente en Kubernetes kind en el runner cloud de GitHub Actions | Entorno académico efímero autorizado; confirmar con el docente si exige un clúster externo de un proveedor específico |
| IE3: dashboard integrado al CI/CD | 10% | Grafana con cobertura, duración del despliegue, CPU, memoria, errores, P95, logs y alertas | Cobertura y tiempos proceden de reportes/relojes reales; la duración excluye el build de la imagen |
| IE4: documentación y decisiones técnicas | 10% | Este README y `docs/evaluacion_3_observabilidad.md` explican integración, reproducción, trazabilidad y lectura operativa | El equipo debe revisar el material y elaborar sus justificaciones personales |
| IE5: cumplimiento automatizado | 20% | pip-audit, SonarQube, cobertura mínima y gate que rechaza evidencia incompleta | La pauta permite estas herramientas; branch protection es una protección adicional, no una certificación obtenida por el código |
| IE6: interrupción ante fallas críticas | 20% | `needs: quality`, pruebas negativas y workflow independiente con gate fallido y despliegue omitido | La demostración utiliza reportes sintéticos claramente identificados |

Los seis indicadores tienen implementación y evidencias. Esto no garantiza una nota ni acredita por sí solo la entrega formal o las reflexiones individuales.

### Monitoreo local con Docker Compose

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.monitoring.yml
export VCS_REF="$(git rev-parse HEAD)"
export APP_IMAGE="gmcomponents-ev2:$VCS_REF"
docker compose config --quiet
docker compose build gmcomponents
docker compose up -d --no-build --scale gmcomponents=2 --wait --wait-timeout 180
```

- Aplicación: [http://127.0.0.1:8501](http://127.0.0.1:8501).
- Grafana Compose: [dashboard EP3](http://127.0.0.1:3000/d/gmcomponents-ep3).
- Prometheus: [http://127.0.0.1:9090](http://127.0.0.1:9090).
- Pushgateway: [http://127.0.0.1:9091](http://127.0.0.1:9091).

La cobertura y duración se publican automáticamente en CI/CD. En un entorno manual, esos paneles requieren generar `reports/ci-metrics.prom` a partir de `coverage.xml` y del tiempo realmente medido, y enviarlo a Pushgateway como indica el procedimiento de EV3. Sin ejecuciones del agente, los paneles de latencia pueden no tener observaciones.

### Kubernetes cloud y centralización de logs

El workflow instala kind/kubectl, crea el clúster, carga la imagen del commit y ejecuta `scripts/deploy_kubernetes.sh`. Los manifiestos y configuraciones están en `deploy/kubernetes/`.

El namespace aplica Pod Security Restricted. Los contenedores usan usuario no root, filesystem de solo lectura, capacidades eliminadas, `seccomp: RuntimeDefault`, límites de CPU/memoria y sondas de arranque, readiness y liveness. Solo Alloy obtiene permisos para leer pods/logs del namespace.

Prometheus recoge las métricas de ambos pods. Alloy envía sus logs a Loki. Grafana utiliza ambas fuentes en un dashboard de 12 paneles con UID `gmcomponents-kubernetes`. Prometheus también envía las alertas a Alertmanager, cuyo receptor es local y no envía mensajes externos.

CI habilita `OBSERVABILITY_SELF_TEST=true` para generar una ejecución sintética exitosa y otra fallida por pod. Sus series llevan `source=self_test`; los paneles operativos y las alertas de errores filtran `source=app`. Esta carga verifica la cadena de telemetría y no representa tráfico real de usuarios.

`scripts/check_kubernetes.py` verifica los datos, provoca una caída controlada del gateway, exige la alerta y su recepción, restaura el servicio y elimina un pod para comprobar su reposición automática. Estos ensayos deben ejecutarse únicamente en el laboratorio. El procedimiento de reproducción y publicación de métricas está en [la documentación operativa de EV3](docs/evaluacion_3_observabilidad.md#reproducir-kubernetes).

Los túneles del workflow pertenecen al runner; los enlaces localhost no exponen una aplicación permanente en el computador del estudiante. El clúster y sus volúmenes `emptyDir` son efímeros. La evidencia queda en los artefactos de Actions; una instalación permanente necesitaría almacenamiento persistente y respaldos.

### Evidencias comprobadas

Revisión del código en `3066ce4e418acadba033c4a2f36e9c8272f50f5e`:

- [CI/CD completo aprobado](https://github.com/iaketo/ia-components-devops/actions/runs/44832288188): 38 pruebas, 94,67% de cobertura, 99 dependencias Python auditadas sin vulnerabilidades conocidas y SonarQube aprobado.
- Cinco pruebas de reglas de alerta aprobadas con `promtool`: espera de 30 s, desaparición de targets, una réplica disponible, primer incremento del contador de errores y exclusión de carga sintética.
- Compose y Kubernetes: smoke tests funcionales en ambas réplicas/pods, consultas de métricas y recepción de logs.
- Evidencia Kubernetes: dos exporters UP, gateway disponible, dashboard de 12 paneles y fuentes Prometheus/Loki; despliegue medido en 81 s, alerta recibida en 34,14 s y reposición del pod en 6,32 s. Son resultados de esa ejecución, no garantías de rendimiento.
- [Demostración de bloqueo](https://github.com/iaketo/ia-components-devops/actions/runs/44832290459): el gate termina con `failure` y el job dependiente con `skipped`, resultado esperado de ese workflow de prueba.
- En esta revisión se repitieron las 38 pruebas localmente con 94,67% de cobertura. La ejecución normal de CI simula los servicios externos; el smoke real de catálogo, embeddings y Groq se validó por separado usando `GROQ_MODEL=openai/gpt-oss-120b`.

### Aportes del segundo integrante y cierre de entrega

El segundo integrante puede realizar aportes verificables sobre la implementación existente:

1. Ejecutar y documentar los escenarios de bloqueo `coverage` y `sonar` de `blocking-demo.yml`, conservando los enlaces y reportes de cada ejecución.
2. Obtener capturas de Grafana/Prometheus/Loki durante una ejecución del laboratorio, explicar las métricas observadas y relacionar un `trace_id` con los logs de su pod.
3. Reproducir el despliegue Kubernetes, revisar sus recursos/sondas y registrar el ensayo de caída y recuperación.
4. Revisar los cambios del compañero mediante Pull Request, con observaciones y validación propia.
5. Redactar su reflexión individual sobre el aprendizaje y su contribución a EV3, sin apoyo de IA. Cada integrante debe hacer la suya.

Antes de entregar: completar las reflexiones específicas de EV3 y conclusiones propias, revisar la declaración de IA, confirmar el alcance cloud con el docente y subir el enlace del repositorio a AVA/enviarlo por correo según la pauta. Las reflexiones existentes al final de este README se conservan intactas; su contenido actual se centra en GitFlow y no reemplaza automáticamente las reflexiones de esta evaluación.

## Estrategia de ramificación: GitFlow

Se optó por GitFlow como modelo de ramificación:

- **main**: código estable, listo para producción.
- **develop**: rama de integración, concentra el trabajo ya revisado antes del release.
- **feature/<nombre>**: nuevas funcionalidades, se crean desde `develop` y se integran hacia `develop` vía Pull Request.
- **hotfix/<nombre>**: correcciones urgentes, se crean desde `main` y se integran hacia `main` y `develop`.

## Convenciones de commits

Se utiliza el formato de Conventional Commits:


| Tipo       | Uso                                              |
|------------|---------------------------------------------------|
| feat       | Nueva funcionalidad                               |
| fix        | Corrección de errores                             |
| docs       | Cambios en documentación                          |
| ci         | Cambios en configuración de CI/CD                 |
| refactor   | Cambios de código que no alteran comportamiento   |

## Naming de ramas

| Prefijo    | Uso                                     | Ejemplo                              |
|------------|------------------------------------------|----------------------------------------|
| feature/   | Nueva funcionalidad                       | feature/observability-tracing          |
| hotfix/    | Corrección urgente sobre producción       | hotfix/fix-requirements                |
| develop    | Rama de integración (única, permanente)   | —                                       |
| main       | Rama de producción (única, permanente)    | —                                       |

## Flujo de merge

1. Las ramas `feature/*` se crean desde `develop` y se integran hacia `develop` mediante Pull Request.
2. Las ramas `hotfix/*` se crean desde `main` y se integran hacia `main` y `develop`.
3. Ningún cambio se sube directo a `main` o `develop`: todo pasa por Pull Request.
4. El pipeline de GitHub Actions (`.github/workflows/ci.yml`) se ejecuta en cada push a `develop`/`main` y en cada Pull Request hacia esas ramas.

## Estrategia de revisión (Pull Requests)

- Todo Pull Request debe tener al menos 1 revisor antes de aprobarse.
- El PR debe incluir una descripción breve de qué cambia y por qué.
- El revisor valida que el código cumple su propósito, los tests pasan (verificado automáticamente por GitHub Actions), y las convenciones de nombres y commits se respetan.

## Pipeline de Integración Continua (CI)

El archivo `.github/workflows/ci.yml` automatiza:

1. Descarga del código (checkout).
2. Configuración del entorno Python 3.11.
3. Instalación de dependencias CPU y herramientas de calidad (`pip install -r requirements-dev.txt`).
4. Ejecución de la batería de pruebas (`python -m pytest tests/`).

Las etapas adicionales de seguridad, Docker, despliegue y evidencias se describen arriba y están implementadas en el mismo workflow.

## Uso de Inteligencia Artificial

Se utilizó Claude (Anthropic) como apoyo para resolver errores de configuración del pipeline de CI/CD, corregir dependencias en `requirements.txt`, y documentar las convenciones del proyecto. Las decisiones de diseño y las conclusiones individuales fueron elaboradas por los propios integrantes.

En esta actualización se utilizó Codex (OpenAI) para revisar la pauta, implementar configuración CI/CD, pruebas, correcciones y documentación operativa, y ejecutar validaciones locales. El equipo debe revisar y validar estos cambios antes de entregar. Las reflexiones individuales existentes se conservaron. Referencia para declarar el uso de IA: https://bibliotecas.duoc.cl/ia.


##Reflexiones##
[Nicolás Troncoso]
Al principio me costó entender GitFlow, sobre todo diferenciar main de develop y saber desde qué rama debía crear cada tipo de trabajo (feature o hotfix). Un momento que me ayudó a entenderlo de verdad fue cuando tuvimos que resolver un conflicto de merge en requirements.txt, donde dos cambios distintos (un hotfix mío y una actualización de mi compañero) chocaban en el mismo archivo, ahí entendí en la práctica por qué Git necesita que alguien decida manualmente qué versión final debe quedar. También aprendí lo importante que es revisar el código de otra persona antes de integrarlo: no es solo un trámite, sino una forma real de detectar errores o inconsistencias antes de que lleguen a producción.

[Álvaro Eyzaguirre]
Durante el desarrollo del proyecto pude aprender y aplicar GitFlow para organizar el trabajo con mi compañero. Lo que más me gustó fue la forma en que se puede revisar y aprobar el código de otra persona antes de integrarlo, ya que permite tener un mayor control sobre los cambios realizados. Esta experiencia me ayudó a entender mejor cómo GitFlow facilita el trabajo colaborativo y la integración del código entre los integrantes del equipo.


## Evaluación Parcial 3

Se extendió el CI/CD de EP2 con Prometheus, Grafana, métricas por réplica, sonda de disponibilidad, métricas reales de cobertura/despliegue y pruebas negativas del bloqueo de cumplimiento. La configuración básica de Compose sigue disponible; el stack de monitoreo se activa con `-f docker-compose.yml -f docker-compose.monitoring.yml`. El workflow usa ambos archivos y conserva los gates obligatorios antes del despliegue.

Consultar [procedimiento, matriz ponderada y pendientes de EP3](docs/evaluacion_3_observabilidad.md). La EV3 completa añade Kubernetes real con kind en el runner cloud efímero autorizado, logs centralizados con Loki/Alloy, Alertmanager, ensayo de caída y reposición de pods. Se reutiliza la misma imagen validada; `blocking-demo.yml` demuestra el bloqueo entre jobs en una rama independiente. No se crea un clúster permanente de un proveedor externo.
