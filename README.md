# GM Components — Pipeline CI/CD (Evaluación Parcial 2)

La aplicación Streamlit analiza compatibilidad de hardware usando el catálogo de GM Components, FAISS, embeddings y Groq. El pipeline prueba la aplicación, audita dependencias, analiza el código con SonarQube y despliega dos réplicas en un entorno Docker Compose simulado.

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
python scripts/smoke_test.py
```

El smoke test predeterminado controla las respuestas externas para ejecutarse sin secretos ni descargar modelos. Ejecuta el código real de selección, FAISS, análisis, caché, memoria, trazas, chat y las cinco páginas con Streamlit AppTest. Esta simulación **no certifica acceso a Groq ni la calidad del modelo de embeddings**.

Para usar la aplicación, configura `GROQ_API_KEY` de forma segura en el entorno o en un `.env` local ignorado por Git. `SERP_API_KEY` es opcional: sin ella hay un fallback informativo. Las variables inyectadas tienen prioridad sobre `.env`. No se usan claves `dummy`.

```bash
python -m streamlit run app.py --server.headless=true --browser.gatherUsageStats=false
python scripts/smoke_test.py --live
```

La validación `--live` exige un catálogo no vacío, embeddings reales, recuperación FAISS, un análisis y un chat con Groq, caché y navegación de la interfaz. Termina con código distinto de cero ante un fallo. Requiere HTTPS a `gmcomponents.onrender.com`, `api.groq.com`, `huggingface.co` y sus destinos Xet; la búsqueda opcional usa `serpapi.com`.

El modelo se selecciona con `GROQ_MODEL` y por defecto usa `openai/gpt-oss-120b`. El modelo anterior `llama-3.3-70b-versatile` ya no apareció en el listado de modelos de Groq durante esta validación; no basta con tener una clave para usar un modelo retirado.

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
| Despliegue | Imagen identificada por SHA, dos réplicas y Nginx; healthcheck más smoke test funcional en cada réplica | Fallo de construcción, arranque, gateway o funcionalidad |

El job de despliegue tiene `needs: quality`: no se ejecuta si falla alguna comprobación de calidad/seguridad. No hay `continue-on-error` en esos controles. GitHub Actions muestra el workflow fallido; la pauta exige alertas **o** bloqueos y aquí se implementa bloqueo.

Dependabot revisa semanalmente dependencias Python, Docker y GitHub Actions mediante `.github/dependabot.yml`. Su configuración produce propuestas de actualización; no reemplaza el análisis bloqueante del pipeline. Las dependencias sin uso (CrewAI, LangChain, Flask y otras) se retiraron del entorno para reducir la superficie de dependencias; la aplicación usa Groq directamente.

Para ejecutar la auditoría local: `python scripts/audit_dependencies.py`. El identificador del wheel oficial `torch==2.14.1+cpu` se consulta como la versión base `2.14.1` en la base de advisories; esto no cambia el artefacto instalado ni su verificación. Así no se omite PyTorch por no existir una distribución `+cpu` en PyPI.

SonarQube se crea por ejecución, solo publica en loopback, cambia la contraseña inicial, analiza, espera el Quality Gate y elimina servidor y volúmenes al terminar. No requiere `SONAR_TOKEN` del equipo. La condición de seguridad usa todos los resultados de la ejecución, sin suprimir vulnerabilidades. El historial del servidor temporal no persiste: los reportes se conservan como artefactos de Actions.

La imagen se etiqueta con `${{ github.sha }}` y lleva la etiqueta OCI `org.opencontainers.image.revision`. Los artefactos `quality-<SHA>` contienen JUnit, cobertura y auditorías; `deployment-<SHA>` contiene el ID de imagen, commit, estado de contenedores y logs. Esto vincula código, controles y despliegue de la misma ejecución. La imagen se ejecuta en el runner; no se publica en un registry ni se despliega a producción.

Para validar los servicios reales desde Actions, crea el secreto de repositorio `GROQ_API_KEY` (y opcionalmente `SERP_API_KEY`) en Settings → Secrets and variables → Actions. Ejecuta manualmente CI-CD con `live_validation=true`. La ejecución falla si falta la clave o fallan los servicios; no se omite silenciosamente esa comprobación. Los PR y el despliegue simulado estándar no reciben secretos ni dependen de servicios externos.

Configura además una regla de protección para `main` y `develop` que exija PR y los checks del workflow antes del merge. El README describe esa política; su aplicación debe verificarse en Settings del repositorio, no se obtiene solo con este archivo.

Referencias: [Dependabot](https://docs.github.com/en/code-security/dependabot), [SonarQube](https://docs.sonarsource.com/sonarqube-server/), [pip-audit](https://github.com/pypa/pip-audit), [Docker Compose](https://docs.docker.com/compose/).

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
Al principio me costó entender GitFlow, sobre todo diferenciar main de develop y saber desde qué rama debía crear cada tipo de trabajo (feature o hotfix). Un momento que me ayudó a entenderlo de verdad fue cuando tuvimos que resolver un conflicto de merge en requirements.txt, donde dos cambios distintos (un hotfix mío y una actualización de mi compañero) chocaban en el mismo archivo — ahí entendí en la práctica por qué Git necesita que alguien decida manualmente qué versión final debe quedar. También aprendí lo importante que es revisar el código de otra persona antes de integrarlo: no es solo un trámite, sino una forma real de detectar errores o inconsistencias antes de que lleguen a producción.

[Álvaro Eyzaguirre]
Durante el desarrollo del proyecto pude aprender y aplicar GitFlow para organizar el trabajo con mi compañero. Lo que más me gustó fue la forma en que se puede revisar y aprobar el código de otra persona antes de integrarlo, ya que permite tener un mayor control sobre los cambios realizados. Esta experiencia me ayudó a entender mejor cómo GitFlow facilita el trabajo colaborativo y la integración del código entre los integrantes del equipo.
