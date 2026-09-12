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
3. Instalación de dependencias (`pip install -r requirements.txt`).
4. Ejecución de la batería de pruebas (`python -m pytest tests/`).

## Uso de Inteligencia Artificial

Se utilizó Claude (Anthropic) como apoyo para resolver errores de configuración del pipeline de CI/CD, corregir dependencias en `requirements.txt`, y documentar las convenciones del proyecto. Las decisiones de diseño y las conclusiones individuales fueron elaboradas por los propios integrantes.


##Reflexiones##
[Nicolás Troncoso]
Al principio me costó entender GitFlow, sobre todo diferenciar main de develop y saber desde qué rama debía crear cada tipo de trabajo (feature o hotfix). Un momento que me ayudó a entenderlo de verdad fue cuando tuvimos que resolver un conflicto de merge en requirements.txt, donde dos cambios distintos (un hotfix mío y una actualización de mi compañero) chocaban en el mismo archivo — ahí entendí en la práctica por qué Git necesita que alguien decida manualmente qué versión final debe quedar. También aprendí lo importante que es revisar el código de otra persona antes de integrarlo: no es solo un trámite, sino una forma real de detectar errores o inconsistencias antes de que lleguen a producción.

[Álvaro Eyzaguirre]
Durante el desarrollo del proyecto pude aprender y aplicar GitFlow para organizar el trabajo con mi compañero. Lo que más me gustó fue la forma en que se puede revisar y aprobar el código de otra persona antes de integrarlo, ya que permite tener un mayor control sobre los cambios realizados. Esta experiencia me ayudó a entender mejor cómo GitFlow facilita el trabajo colaborativo y la integración del código entre los integrantes del equipo.
