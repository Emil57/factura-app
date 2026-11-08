from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from . import models
from .config import settings
from .database import Base, SessionLocal, engine
from .routers import auth, catalogs, clientes, emisores, facturas, productos
from .security import hash_password

ROLES = {
    "Admin": "Acceso total: emisores, usuarios y CSD",
    "Usuario": "Captura clientes, productos y emite facturas",
    "Contador": "Consulta y cancela facturas",
}


def init_db() -> None:
    """Create tables and seed roles + first admin. Swap for Alembic migrations before production."""
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        existing = {r.nombre for r in db.scalars(select(models.Rol))}
        for nombre, desc in ROLES.items():
            if nombre not in existing:
                db.add(models.Rol(nombre=nombre, descripcion=desc))
        db.flush()
        if not db.scalar(select(models.Usuario).limit(1)):
            admin_role = db.scalar(select(models.Rol).where(models.Rol.nombre == "Admin"))
            db.add(models.Usuario(email=settings.admin_email.lower(), nombre="Administrador",
                                  password_hash=hash_password(settings.admin_password), roles=[admin_role]))
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Factura App API", version="0.1.0",
              description="Emisión de CFDI 4.0 para cualquier tipo de contribuyente", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth, catalogs, emisores, clientes, productos, facturas):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "pac": settings.pac_provider}
