# factura-app

Web app para emitir facturas electrónicas **CFDI 4.0** para cualquier tipo de contribuyente:
personas físicas o morales, de cualquier régimen fiscal, timbrando con **Facturama (API Multiemisor)**.

| Capa | Tecnología |
|---|---|
| Front End | Next.js 15 (App Router) + React 19 + TypeScript |
| Back End | Python 3.12 + FastAPI + SQLAlchemy 2 |
| Base de datos | PostgreSQL 16 |
| PAC | Facturama API Multiemisor (o PAC simulado para desarrollo) |

## Qué hace (MVP)

- **Emisores**: registra varios RFC emisores (físicas y morales, cualquier régimen), con serie y folio propios, y sube su CSD al PAC.
- **Clientes** con validación CFDI 4.0: formato de RFC, régimen y uso de CFDI compatibles con persona física/moral, CP fiscal, y reglas de *Público en general* (XAXX010101000) y extranjeros.
- **Productos** con ClaveProdServ, ClaveUnidad, ObjetoImp, IVA (16 %, 8 %, 0 %, exento) e IEPS.
- **Facturas** (ingreso y egreso/nota de crédito): borrador → validación → timbrado → XML/PDF → cancelación (motivos 01–04, incluye cancelación pendiente de aceptación).
- **Motor de impuestos** con redondeo SAT: traslados de IVA/IEPS (el IEPS forma parte de la base del IVA) y **retenciones** de ISR e IVA por concepto.
- **Retenciones sugeridas** según emisor y receptor:
  - Persona física 612 (honorarios) o 606 (arrendamiento) → persona moral: ISR 10 % + IVA 2/3.
  - Persona física RESICO 626 → persona moral: ISR 1.25 % + IVA 2/3.
  - Siempre editables. Confirma casos especiales (fletes, outsourcing, etc.) con tu contador.
- **Roles**: Admin (todo), Usuario (captura y timbra), Contador (consulta y cancela).
- **Bitácora** (`log_actividades`) de altas, cambios, timbrado y cancelación.

## Arranque rápido (Docker)

```bash
cp backend/.env.example backend/.env   # ajusta JWT_SECRET y ADMIN_PASSWORD
docker compose up --build
```

- App: http://localhost:3000 (usuario inicial: `ADMIN_EMAIL` / `ADMIN_PASSWORD` del `.env`)
- API y documentación interactiva: http://localhost:8000/docs

Por defecto `PAC_PROVIDER=mock`: el timbrado genera un UUID aleatorio y un XML **sin validez fiscal**, útil para desarrollar sin credenciales.

## Desarrollo local sin Docker

```bash
# Base de datos
docker compose up -d db

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
python -m pytest            # pruebas del motor de impuestos, validaciones y XML

# Frontend
cd ../frontend
cp .env.example .env.local
npm install
npm run dev
```

## Timbrar con Facturama (sandbox)

1. Crea una cuenta de pruebas en https://apisandbox.facturama.mx y usa ese usuario y contraseña.
2. En `backend/.env`:
   ```
   PAC_PROVIDER=facturama
   FACTURAMA_USER=tu_usuario
   FACTURAMA_PASSWORD=tu_password
   FACTURAMA_SANDBOX=true
   ```
3. Crea el emisor de prueba `EKU9003173C9` · `ESCUELA KEMPER URGATE` · régimen `601` y sube el CSD de pruebas del SAT (contraseña `12345678a`).
4. Crea un cliente de prueba (por ejemplo `URE180429TM6` · `UNIVERSIDAD ROBOTICA ESPAÑOLA` · `601` · CP `86991`) y emite.

En sandbox, Facturama solo permite cancelar CFDI del RFC `EKU9003173C9`.

## Estructura

```
backend/
  app/
    main.py             # FastAPI, CORS, creación de tablas y usuario admin inicial
    models.py           # Tablas (basadas en docs/db.txt, adaptadas a CFDI 4.0)
    schemas.py          # Validación de entrada/salida (Pydantic)
    routers/            # auth, catalogos, emisores, clientes, productos, facturas
    sat/                # Catálogos SAT y validación de RFC
    services/
      taxes.py          # Motor de impuestos puro (traslados, retenciones, redondeo)
      validation.py     # Reglas CFDI 4.0 antes de timbrar
      cfdi_builder.py   # Payload para Facturama y XML de vista previa
      pac.py            # Clientes PAC: Facturama Multiemisor y Mock
  tests/
frontend/
  app/(app)/            # facturas, clientes, productos, emisores
  components/           # Editor de factura, selects de catálogos, modales
  lib/                  # Cliente de API, tipos, utilidades
docs/                   # Requerimientos, tablas, diagrama original y arquitectura-tecnica.drawio
```

## Diagrama técnico

`docs/arquitectura-tecnica.drawio` (ábrelo en https://app.diagrams.net) tiene cuatro páginas: **Arquitectura** (componentes, endpoints y despliegue), **Flujo de timbrado** (secuencia de borrador → timbrado → descarga → cancelación), **Modelo de datos** (tablas y relaciones) y **Stack técnico** (tecnologías con versiones exactas).

## Cambios respecto a `docs/db.txt`

- `ConfiguracionEmpresa` → `emisores` (varios emisores para facturar como cualquier contribuyente).
- Se agregó `usuarios` (no estaba definida) y `Sesiones` se reemplazó por JWT.
- `clientes` agrega `codigo_postal` (DomicilioFiscalReceptor, obligatorio en 4.0); el tipo de persona se deriva del RFC.
- `productos` y `detalle_factura` agregan claves SAT, objeto de impuesto y tasas (incluye retenciones).
- La tabla `Impuestos` se sustituye por los catálogos SAT en código.

## Siguientes pasos

Ver [ROADMAP.md](ROADMAP.md) para la lista priorizada de lo que falta.
