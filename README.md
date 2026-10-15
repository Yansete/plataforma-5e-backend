# Plataforma Docente — generación asistida de recursos educativos

Proyecto del curso **Taller Integrador 1** (UPAO, 2026-II). A partir del material del docente, la plataforma propone
recursos para cada momento de la clase, con **revisión docente obligatoria**, **trazabilidad a la evidencia de origen** y
descarga de lo aprobado para **Moodle (Moodle XML)**, **Chamilo (QTI 2.1)** o como **documento de la unidad**.

> **Estado actual:** sistema completo con base de datos. Cada docente crea su cuenta, registra sus cursos y unidades, sube su
> material (PDF, PPTX o TXT) o busca el tema en una fuente abierta (Wikipedia en español, licencia CC BY-SA 4.0), y genera
> recursos que citan los fragmentos de ese material (RAG), con IA si el servidor tiene clave o con reglas si no. La revisión,
> las decisiones y el historial de descargas se guardan en el servidor.
>
> Internamente cada tipo de recurso corresponde a una etapa del modelo instruccional **5E** (Bybee et al., 2006); en la
> interfaz se muestran como momentos de la clase: *Para iniciar la clase, Para explorar, Para explicar, Para aplicar y Para evaluar*.

Enlace: https://plataforma-5e-taller-integrador.vercel.app/

## Ejecutar en local

Dos terminales desde la raíz del repositorio. El backend usa SQLite por defecto (no requiere Docker).

```bash
# Terminal 1 · backend (FastAPI)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn plataforma5e.bootstrap.app:crear_aplicacion --factory --port 8000

# Terminal 2 · frontend (React + Vite)
cd frontend
npm install
npm run dev
```

Abre [http://localhost:5173](http://localhost:5173), elige **Crear cuenta** y regístrate con tu nombre, correo y una
contraseña de al menos 8 caracteres. Todo se guarda en la base del backend (`backend/demo.db` con SQLite, o la que
indique `DATABASE_URL`).

## Requisitos

- **Node.js 18 o superior** (recomendado: Node.js 22 LTS). Descárgalo de [https://nodejs.org](https://nodejs.org) e instálalo con las opciones por defecto.
- **Python 3.11 o superior** (para el entorno del backend).
- **Docker Desktop** (requerido para la base de datos PostgreSQL + pgvector).
- Un navegador moderno (Chrome, Edge o Firefox).
- Conexión a internet solo para instalar dependencias y cargar las fuentes de Google Fonts (sin conexión la interfaz usa Georgia y Segoe UI).

Comprueba la instalación en una terminal nueva:

```bash
node --version   # debe mostrar v18 o superior
npm --version
python --version # debe mostrar 3.11 o superior
```

## Instalación y ejecución

### Frontend

```bash
cd frontend
npm install        # instala dependencias (solo la primera vez o si cambia package.json)
npm run dev        # abre el servidor de desarrollo
```

Abre en el navegador la dirección que muestra la terminal (normalmente [http://localhost:5173](http://localhost:5173)). Para detenerlo, pulsa `Ctrl + C`.

Otros comandos (dentro de `frontend/`):

| Comando               | Qué hace                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `npm run build`     | Comprueba los tipos y genera la versión de producción en`frontend/dist/`                                       |
| `npm run preview`   | Sirve la versión de producción en[http://localhost:4173](http://localhost:4173) (ejecuta antes `npm run build`) |
| `npm run typecheck` | Solo comprueba los tipos de TypeScript                                                                             |
| `npm test`          | Ejecuta las pruebas unitarias de los servicios (`npm run test:coverage` con cobertura)                          |
| `npm run test:e2e`  | Recorre la plataforma en Chromium con el backend real (necesita el backend instalado; ver [docs/pruebas.md](docs/pruebas.md)) |

### Backend

```bash
cd backend
python -m venv .venv
# Activar entorno virtual:
# En Windows (PowerShell): .\.venv\Scripts\Activate.ps1
# En Linux/macOS: source .venv/bin/activate

pip install -e ".[dev]"    # dependencias del backend y de las pruebas
uvicorn plataforma5e.bootstrap.app:crear_aplicacion --factory --reload --port 8000
```

* **Swagger UI:** Documentación interactiva disponible en [http://localhost:8000/docs](http://localhost:8000/docs).
* **Contrato OpenAPI:** Archivo estático versionado en [`docs/openapi.json`](docs/openapi.json).

Otros comandos (dentro de `backend/`):

| Comando                       | Qué hace                                                                          |
| ----------------------------- | ---------------------------------------------------------------------------------- |
| `pytest`                    | Ejecuta la suite completa de pruebas (unitarias, arquitectura, integración y e2e) |
| `pytest tests/unit`         | Ejecuta exclusivamente las pruebas de dominio unitarias                            |
| `pytest tests/arquitectura` | Valida el aislamiento y las reglas de capas de la arquitectura hexagonal           |
| `pytest tests/integration`  | Valida los repositorios y la persistencia ORM con la base de datos                 |
| `pytest tests/e2e`          | Ejecuta pruebas HTTP y XML; SQLite temporal por defecto, PostgreSQL configurable             |

## Cómo se usa

1. **Crear cuenta** o **Iniciar sesión**.
2. **Mis cursos → Nuevo curso**: código, nombre, periodo, sumilla, logro y las unidades con sus resultados de aprendizaje
   (uno por línea; los códigos RA1.1, RA1.2… se ponen solos). Desde «Editar» también se puede **borrar el curso** completo.
3. **Entrar al curso → Abrir unidad.** Cada unidad tiene cuatro pestañas, en el orden de trabajo:
   1. **Material**: sube un PDF, PPTX o TXT, o **busca el tema**. El servidor extrae el texto y lo parte en fragmentos
      («Ver fragmentos» muestra lo que la generación puede citar).
   2. **Generación**: **Elegir opciones** (qué recurso, agrupado por momento de la clase; resultado de aprendizaje, cantidad,
      dificultad y alternativas) o **Escribir pedido** (la plataforma muestra cómo entendió el pedido y envía el texto
      completo como indicación).
   3. **Revisión**: cada recurso con la evidencia que cita. Acepta, edita o descarta cada distractor (con motivo), aprueba,
      regenera (la versión anterior queda en «Descartados») o descarta el recurso. Todo se guarda en el servidor.
   4. **Exportación**: elige los recursos aprobados y descarga el archivo para **Moodle** (.xml), **Chamilo** (.zip) o el
      **documento de la unidad** (.html, con todos los tipos de recurso y su evidencia). El historial de descargas se guarda
      y se puede borrar.

Con la ventana estrecha, el menú lateral se abre con el botón «Menú».

## Base de datos local (PostgreSQL + pgvector) y Almacenamiento

Requiere **Docker Desktop** abierto. Desde la raíz del repositorio:

```bash
cp .env.example .env
docker compose up -d --wait db        # PostgreSQL 17 con pgvector
docker compose run --rm dbmate up     # aplica las migraciones
./db/verificacion/verificar.sh        # comprueba la extensión y los índices (EN-011)
```

Detalles, comandos y estructura de las migraciones en [db/README.md](db/README.md).

### Dónde se guardan los datos y archivos

* **Datos y Embeddings (PostgreSQL):** La información relacional (recursos pedagógicos, opciones, revisiones) e índices vectoriales de los fragmentos se almacenan en el contenedor de **PostgreSQL 17** gestionado por Docker, persistiendo en el volumen local `datos-postgres`.
* **Cuentas, cursos, archivos, fragmentos, recursos revisados e historial de descargas:** en la base de datos del backend (SQLite por defecto o PostgreSQL con `DATABASE_URL`; en producción, Neon). Las contraseñas se guardan cifradas (PBKDF2). Los embeddings en pgvector son el siguiente paso (EN-013).

## Estructura

```
taller-integrador/
├── backend/               Backend en FastAPI (Arquitectura Hexagonal)
│   ├── plataforma5e/      Módulos del backend
│   │   ├── domain/        Entidades nucleares y reglas pedagógicas puras
│   │   ├── application/   Puertos, servicios y casos de uso
│   │   ├── adapters/      Rutas y contratos en inbound/; persistencia y exportación en outbound/
│   │   └── bootstrap/     Factoría de aplicación e inyección de dependencias
│   └── tests/             Suites de pruebas (unit, arquitectura, integration, e2e)
├── documentos/            Documentos del curso (solo lectura)
├── db/                    Base de datos local: migraciones (dbmate), esquema y verificación
├── docs/                  Documentación técnica y especificación OpenAPI (openapi.json)
├── frontend/              Aplicación React + TypeScript + Vite
│   ├── e2e/               Pruebas de punta a punta (Playwright) con el backend real
│   └── src/
│       ├── components/    Componentes reutilizables (sistema de diseño) y marco de la aplicación
│       ├── pages/         Pantallas: inicio de sesión, crear cuenta, cursos, curso y unidad (4 pestañas)
│       ├── services/      Llamadas al backend y reglas del cliente (revisión, pedido escrito, archivos de descarga)
│       ├── state/         Sesión y datos compartidos entre pantallas
│       ├── types/         Modelos de datos
│       ├── styles/        tokens.css (variables) y base.css
│       └── utils/         Formato de fechas y números
├── spikes/                Experimentos aislados (no son código de producción)
├── docker-compose.yml     PostgreSQL + pgvector y dbmate
├── .env.example           Variables de entorno locales (copiar como .env)
└── README.md
```

## Generación con IA

Sin configuración, el backend usa el **generador por reglas**: arma los recursos con oraciones y términos del material, sin
inventar nada. Para redactar con un modelo de lenguaje, define en la terminal del backend (o en el servidor):

```bash
IA_PROVEEDOR=gemini        # gemini, anthropic u openai (o compatible, con IA_URL_BASE)
IA_API_KEY=tu-clave        # nunca se sube al repositorio
IA_MODELO=gemini-3.8-flash # opcional
```

`GET /api/v1/ia` indica qué generador está activo. Si el proveedor falla (clave inválida o límite de uso), la generación
usa el generador por reglas, la pantalla lo avisa y el motivo queda en los registros del servidor
(«Generación con respaldo: …»). El despliegue completo (Vercel, Render y Neon) está en [docs/despliegue.md](docs/despliegue.md).

## Documentación

* [Arquitectura y estado del proyecto](docs/arquitectura.md): capas, contratos, integración, límites y ejecución.
* [Decisiones técnicas](docs/decisiones-tecnicas.md): decisiones, motivos, contradicciones y vacíos detectados.
* [Formatos de exportación SP-003](docs/spikes/SP-003-formatos-de-exportacion.md): Moodle XML y QTI 2.1, validación LMS pendiente.
* [Despliegue](docs/despliegue.md): Vercel, Render y Neon, variables de entorno y problemas frecuentes.
* [Pruebas](docs/pruebas.md): dónde va cada tipo de prueba y cómo correrlas.
* [Guía de Git y GitHub](docs/guia-git.md): pasos para versionar y subir el proyecto.
* [Especificación OpenAPI](docs/openapi.json): especificación contractual generada del backend.

## Equipo

| Integrante | Usuario en GitHub | Responsabilidad principal |
|---|---|---|
| Juan Alegria Sagastegui | `iamjuanyouarenot` | Product Owner, pruebas y medición; agentes de Elaborar y Evaluar |
| Silvana Diaz Calderon | `SilvanaD12` | EP-002 Configuración del docente y diseño de la interfaz |
| Yan Liu Dai | `Yansete` | EP-003 Creación por etapa 5E, ingesta y RAG, despliegue del frontend |
| Sergio Celi Vertiz | `sceliv` | EP-004 Integración y tipología, arquitectura del backend |
