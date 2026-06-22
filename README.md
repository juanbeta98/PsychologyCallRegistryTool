# Herramienta de Gestión de Llamadas — CIP Dosquebradas

Aplicación de escritorio para la gestión del proceso de acompañamiento estudiantil en el **Centro de Escucha Unadista** del CIP Dosquebradas, UNAD. Permite registrar llamadas de seguimiento a estudiantes, conducir entrevistas estructuradas, generar reportes y exportar datos para análisis.

---

## Funcionalidades

- **Cola de llamadas** — vista priorizada de estudiantes pendientes y reagendados
- **Registro de llamadas** — resultado, notas, reagendamiento y entrevista estructurada
- **Entrevista de acompañamiento** — autonomía en virtualidad, herramientas digitales (Teams, correo), motivación, acompañamiento psicosocial y psicoeducativo
- **Histórico** — registro completo de todas las llamadas realizadas, con edición por llamada
- **Reportes interactivos** — dashboard con 10+ gráficos (embudo, demografía, hallazgos, resultados)
- **Exportación Excel** — con filtro por rango de fechas
- **Informe PDF imprimible** — reporte profesional con narrativa automática y gráficos
- **Importación de listas** — carga de estudiantes desde Excel con manejo de vigencias

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| Backend | Python 3 · Flask 3 · SQLAlchemy 2 |
| Base de datos | SQLite (archivo local) |
| Frontend | Bootstrap 5 · Chart.js 4 · DataTables 2 |
| Exportación | pandas · xlsxwriter |

---

## Estructura del proyecto

```
PsychologyCallRegistryTool/
├── Abrir Herramienta.command   # Lanzador — doble clic para iniciar
├── app/
│   ├── app.py                  # Fábrica Flask + migración de BD al inicio
│   ├── models.py               # Modelos SQLAlchemy (Student, Call, CallInterview…)
│   ├── requirements.txt        # Dependencias Python
│   ├── routes/
│   │   ├── calls.py            # Registro de llamadas, histórico, edición
│   │   ├── imports.py          # Importación de listas Excel
│   │   ├── phones.py           # Gestión de teléfonos
│   │   ├── reports.py          # Dashboard, informe PDF, exportación Excel
│   │   └── students.py         # Listado y búsqueda de estudiantes
│   ├── static/                 # CSS y JS propios
│   └── templates/              # Plantillas Jinja2 (HTML)
├── data/                       # Base de datos SQLite — NO se versiona
├── reports/                    # Reportes Excel generados — NO se versionan
└── uploads/                    # Listas de estudiantes importadas — NO se versionan
```

> **Privacidad:** `data/`, `reports/` y `uploads/` están excluidos del repositorio por contener datos personales de estudiantes (Ley 1581 de 2012 — Habeas Data). Estos directorios existen en el equipo de trabajo pero nunca se suben a GitHub.

---

## Instalación (primera vez)

**Requisitos:** macOS con Python 3 instalado.

1. Clona o descarga el repositorio en una carpeta local.
2. Asegúrate de que `Abrir Herramienta.command` tenga permisos de ejecución:
   ```bash
   chmod +x "Abrir Herramienta.command"
   ```
3. Haz doble clic en `Abrir Herramienta.command`.  
   La primera vez instala las dependencias automáticamente (~1-2 min) y abre la herramienta en el navegador en `http://127.0.0.1:5050`.

El entorno virtual se crea en `~/.psicologia_app_venv` (fuera del repositorio).

---

## Actualizar a una nueva versión

Cuando hay cambios en el código, **solo se actualiza la carpeta `app/`**. La base de datos (`data/psicologia.db`) nunca se sobreescribe.

```
Pasos:
1. Cerrar la herramienta (Ctrl+C en la terminal o cerrar la ventana).
2. Reemplazar la carpeta app/ con la nueva versión.
3. Abrir Herramienta.command — las nuevas columnas de BD
   se agregan automáticamente al iniciar (migración idempotente).
```

> No es necesario reinstalar el entorno virtual ni tocar `data/`, `uploads/` ni `reports/`.

---

## Migraciones de base de datos

La herramienta **no usa Alembic ni scripts manuales**. Cada vez que la app inicia, `app/app.py` verifica qué columnas existen en `call_interview` y agrega las que falten con `ALTER TABLE ADD COLUMN`. Esto es seguro para bases de datos con datos existentes.

Columnas que se agregan automáticamente si no existen:
- `virtual_most_easy`
- `has_teams_access`
- `has_email_access`
- `psychoeducational_accompaniment`
- `psychoeducational_notes`

---

## Desarrollo

```bash
# Crear entorno y instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt

# Ejecutar en modo desarrollo
python app/app.py
```

La app corre en `http://127.0.0.1:5050`.

---

## Créditos

Desarrollado para el programa de acompañamiento estudiantil del **CIP Dosquebradas — UNAD**.  
Psicóloga responsable: **Vivian Juliana Osorio**
