# Servicios y paneles de EV3

Este es el punto de entrada para encontrar gráficos, métricas, logs, alertas y evidencias.

## Qué quieres ver

| Nombre fácil | Servicio | Dónde abrirlo | Qué muestra |
|---|---|---|---|
| **Gráficos y métricas de la aplicación** | Grafana | [Abrir gráficos locales](http://localhost:3000/d/gmcomponents-ep3) | Cobertura, despliegue, CPU, memoria, errores y tiempos de respuesta |
| **Estado de los servicios** | Prometheus | [Ver servicios disponibles](http://localhost:9090/targets) | `UP` significa que Prometheus puede consultar ese exporter |
| **Consultar métricas numéricas** | Prometheus | [Abrir consultas de métricas](http://localhost:9090/query) | Permite buscar métricas y dibujar sus series |
| **Alertas del monitoreo** | Prometheus | [Ver reglas y alertas](http://localhost:9090/alerts) | Estado de las reglas: inactivas, pendientes o activas |
| **Métricas publicadas por el pipeline** | Pushgateway | [Ver cobertura y tiempo de despliegue](http://localhost:9091) | Datos enviados por CI/CD; no es el dashboard principal |
| **Aplicación de hardware** | Streamlit | [Abrir la aplicación](http://localhost:8501) | Carrito, chat, memoria y trazas del agente |

Los enlaces `localhost` abren servicios de **tu propio computador**. Docker Desktop debe estar abierto y los contenedores iniciados. GitHub no mantiene esos servicios encendidos por visitar el repositorio.

### Accesos directos para Windows

Después de actualizar el proyecto con `git pull origin main`, abre la carpeta [accesos-windows](accesos-windows/) en el Explorador de archivos. Haz doble clic en el acceso que necesites. Esos archivos `.url` abren el navegador; primero debes iniciar los servicios.

Desde PowerShell dentro de la carpeta del proyecto:

```powershell
# Primera vez o después de actualizar el código:
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d --build --scale gmcomponents=2 --wait --wait-timeout 180

# Para volver a mostrarlo, con las imágenes ya construidas:
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d --scale gmcomponents=2 --wait --wait-timeout 180

# Para detenerlo conservando los contenedores y sus datos:
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml stop
```

Grafana abre con acceso de lectura. Los paneles de cobertura/despliegue requieren que se publiquen las métricas del pipeline; la latencia necesita ejecuciones del agente. Una falta de muestras no debe interpretarse como una medición inventada. Consulta el [procedimiento de publicación de métricas](../docs/evaluacion_3_observabilidad.md#ejecutar-y-consultar).

## Ver resultados en GitHub, sin instalar servicios

1. Abre [EV3: gráficos, métricas y pruebas](https://github.com/iaketo/ia-components-devops/actions/workflows/ci.yml?query=branch%3Amain).
2. Selecciona una ejecución de `main` con marca verde.
3. En **Summary / Resumen**, encontrarás el índice de paquetes. En **Artifacts**, descarga el que necesites.
4. Extrae el ZIP completo y abre **`ABRIR-RESUMEN.html`** con tu navegador. Mantén juntos el HTML y los demás archivos extraídos.

| Paquete nuevo | Para qué sirve | Nombre anterior en ejecuciones antiguas |
|---|---|---|
| **01-Pruebas-y-seguridad** | Pruebas, cobertura, auditoría y SonarQube | `quality-<commit>` |
| **02-Graficos-y-metricas-locales** | Grafana/Prometheus de Compose, resultados de métricas y logs del despliegue | `deployment-<commit>` |
| **03-Kubernetes-graficos-logs-y-alertas** | Estado de pods, métricas, logs, alerta crítica y recuperación | `kubernetes-<commit>` |
| **04-Demostracion-de-bloqueo** | Reportes sintéticos que deben impedir el despliegue | `blocking-demo-<commit>-<ejecución>` |

Los nuevos nombres se aplican a ejecuciones posteriores a esta reorganización. Los ZIP antiguos siguen siendo evidencia válida y mantienen sus nombres originales. Cada paquete nuevo incluye `REVISION.json`, que identifica el commit y la ejecución.

El HTML es un **resumen estático de evidencias**. Los dashboards interactivos de Grafana y Prometheus se abren en los servicios que estés ejecutando. El paquete 04 pertenece a [la demostración de bloqueo, cuyo fallo es esperado](https://github.com/iaketo/ia-components-devops/actions/workflows/blocking-demo.yml), y no aparece en cada ejecución normal.

## Qué es Kubernetes y dónde verlo

**Kubernetes administra contenedores**: mantiene las copias de la aplicación, distribuye su acceso y repone un pod si desaparece. Un **pod** es la unidad donde se ejecuta una copia de la aplicación.

Este proyecto crea Kubernetes con kind dentro de un runner cloud de GitHub Actions, lo prueba y lo elimina. Para verlo, entra en el job **02 - Paneles y monitoreo (Compose y Kubernetes)** y abre sus pasos de creación, despliegue y comprobación. Después descarga **03-Kubernetes-graficos-logs-y-alertas**.

- En `ABRIR-RESUMEN.html`: verás las métricas y enlaces con nombres legibles.
- En `resources.json`: aparecen los pods, despliegues y servicios que existieron.
- En `runtime-verification.json`: están las comprobaciones de métricas, logs, alertamiento y reposición del pod.
- En `events.txt` y los `.log`: están los eventos y registros del ensayo.

El clúster temporal de Actions no aparece como un clúster permanente en Docker Desktop de tu PC. El arranque local explicado arriba utiliza Compose.

### Servicios adicionales del laboratorio Kubernetes

| Nombre fácil | Servicio | Cómo se consulta |
|---|---|---|
| **Gráficos, logs y alertas de Kubernetes** | Grafana | Dashboard `gmcomponents-kubernetes`, accesible durante el laboratorio mediante [su túnel local](http://localhost:3000/d/gmcomponents-kubernetes) |
| **Registros de la aplicación por pod** | Loki | Panel de logs y opción Explore de Grafana; Loki no es otra página de gráficos independiente |
| **Recolector de registros** | Alloy | Lee los logs de los pods y los envía a Loki; sus resultados están en `alloy.log` |
| **Alertas recibidas** | Alertmanager | [Interfaz de alertas](http://localhost:9093), únicamente con el laboratorio y su túnel iniciados |
| **Disponibilidad HTTP** | Blackbox Exporter | Métrica `probe_success` y panel de disponibilidad; el valor 1 significa que la sonda pasó |

Estos enlaces del laboratorio requieren un despliegue Kubernetes activo y sus túneles; el comando de Compose no inicia Loki, Alloy ni Alertmanager. Consulta el [procedimiento completo de Kubernetes](../docs/evaluacion_3_observabilidad.md#reproducir-kubernetes).

## Dónde está la configuración

| Configuración | Enlace |
|---|---|
| Dashboard local: gráficos y métricas | [Grafana Compose](grafana/dashboards/ep3.json) |
| Dashboard Kubernetes: gráficos, logs y alertas | [Grafana Kubernetes](../deploy/kubernetes/dashboard.json) |
| Recolección de métricas | [Prometheus Compose](prometheus.yml) / [Prometheus Kubernetes](../deploy/kubernetes/prometheus.yml) |
| Reglas y pruebas de alertas | [Reglas](alerts.yml) / [Pruebas](alerts.test.yml) |
| Recolección y almacenamiento de logs | [Alloy](../deploy/kubernetes/config.alloy) / [Loki](../deploy/kubernetes/loki.yml) |
| Recepción de alertas | [Alertmanager](../deploy/kubernetes/alertmanager.yml) |
| Pipeline y artefactos | [Workflow principal](../.github/workflows/ci.yml) |

## Ejecutar Kubernetes manualmente

### Opción sencilla: desde GitHub

1. Abre [el workflow principal](https://github.com/iaketo/ia-components-devops/actions/workflows/ci.yml).
2. Pulsa **Run workflow**, elige **main** y deja `live_validation` desmarcado para la prueba normal.
3. Pulsa **Run workflow** otra vez y sigue el job **02 - Paneles y monitoreo (Compose y Kubernetes)**.
4. Al finalizar, descarga **03-Kubernetes-graficos-logs-y-alertas** y abre su resumen HTML.

Este recorrido crea y elimina el clúster automáticamente. No mantiene una dirección pública para abrir los paneles después de la ejecución.

### Mantener el laboratorio abierto en tu PC Windows

Requiere Docker Desktop en modo Linux, Git Bash, [kind](https://kind.sigs.k8s.io/docs/user/quick-start/) y [kubectl para Windows](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/), instalados y disponibles en `PATH`. En una terminal nueva comprueba `kind version` y `kubectl version --client`. kind creará su propio clúster; no hace falta activar además el clúster de la pestaña Kubernetes de Docker Desktop.

Abre **Git Bash** dentro de la carpeta del proyecto. Los siguientes comandos usan sintaxis Bash, no PowerShell:

```bash
# Libera los puertos que usa el laboratorio; conserva los datos de Compose.
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml stop
export VCS_REF="$(git rev-parse HEAD)"
export APP_IMAGE="gmcomponents-ev2:$VCS_REF"
docker compose build gmcomponents
kind create cluster --name gmcomponents --image kindest/node:v1.34.0 --config deploy/kubernetes/kind.yaml --wait 120s
kind load docker-image "$APP_IMAGE" --name gmcomponents
bash scripts/deploy_kubernetes.sh
kubectl -n gmcomponents get pods
```

Conserva la terminal abierta mientras uses sus túneles. Después abre [Grafana Kubernetes](http://localhost:3000/d/gmcomponents-kubernetes), [Prometheus](http://localhost:9090/targets) y [Alertmanager](http://localhost:9093).

Este arranque manual no publica automáticamente cobertura/duración de CI ni carga sintética; no inventa resultados. Los smoke tests y el ensayo completo se ejecutan automáticamente en el workflow de GitHub. Para repetirlos localmente, sigue el [procedimiento de evaluación](../docs/evaluacion_3_observabilidad.md#reproducir-kubernetes).

El despliegue manual no copia claves de `.env` al clúster. Para realizar análisis con tu configuración local existente, crea un Secret sin mostrar su contenido ni subirlo a Git:

```bash
kubectl -n gmcomponents create secret generic gmcomponents-credenciales --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -
kubectl -n gmcomponents set env deployment/gmcomponents --from=secret/gmcomponents-credenciales
kubectl -n gmcomponents rollout status deployment/gmcomponents --timeout=180s
```

Sin ese Secret puedes inspeccionar infraestructura y monitoreo; el análisis real necesita la credencial. Mantén `GROQ_MODEL=openai/gpt-oss-120b` y tu clave en `GROQ_API_KEY`, en el `.env` local ignorado por Git.

Para eliminar únicamente el clúster de este laboratorio cuando termines:

```bash
kind delete cluster --name gmcomponents
```

Si después de una prueba de caída necesitas volver a abrir el acceso a la aplicación, inicia de nuevo su túnel: `kubectl -n gmcomponents port-forward service/gateway 8501:8080`.
