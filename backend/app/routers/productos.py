from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, current_user, require_roles
from ..models import Categoria, Producto, Usuario
from ..sat import catalogs as cat
from ..schemas import CategoriaIn, CategoriaOut, ProductoIn, ProductoOut

router = APIRouter(prefix="/api", tags=["productos"])


def _check(data: ProductoIn) -> None:
    if data.objeto_imp not in cat.OBJETOS_IMPUESTO:
        raise HTTPException(422, "Objeto de impuesto inválido")
    if data.iva_tasa is not None and data.iva_tasa not in cat.TASAS_IVA:
        raise HTTPException(422, "Tasa de IVA inválida")
    if data.ieps_tasa is not None and data.ieps_tasa not in cat.TASAS_IEPS:
        raise HTTPException(422, "Tasa de IEPS inválida")
    if data.objeto_imp == "02" and data.iva_tasa is None and data.ieps_tasa is None:
        raise HTTPException(422, "Con objeto de impuesto 02 indica al menos IVA o IEPS")


@router.get("/categorias", response_model=list[CategoriaOut], dependencies=[Depends(current_user)])
def list_categorias(db: Session = Depends(get_db)):
    return db.scalars(select(Categoria).order_by(Categoria.nombre)).all()


@router.post("/categorias", response_model=CategoriaOut, status_code=201,
             dependencies=[Depends(require_roles("Usuario"))])
def create_categoria(data: CategoriaIn, db: Session = Depends(get_db)):
    categoria = Categoria(**data.model_dump())
    db.add(categoria)
    db.commit()
    return categoria


@router.get("/productos", response_model=list[ProductoOut], dependencies=[Depends(current_user)])
def list_productos(q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Producto).where(Producto.activo)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Producto.nombre.ilike(like), Producto.codigo.ilike(like)))
    return db.scalars(stmt.order_by(Producto.nombre).limit(200)).all()


@router.post("/productos", response_model=ProductoOut, status_code=201)
def create_producto(data: ProductoIn, request: Request, db: Session = Depends(get_db),
                    user: Usuario = Depends(require_roles("Usuario"))):
    _check(data)
    producto = Producto(**data.model_dump())
    db.add(producto)
    db.flush()
    audit(db, request, user, "crear", "productos", producto.id, despues=data.model_dump())
    db.commit()
    return producto


@router.put("/productos/{producto_id}", response_model=ProductoOut)
def update_producto(producto_id: int, data: ProductoIn, request: Request, db: Session = Depends(get_db),
                    user: Usuario = Depends(require_roles("Usuario"))):
    producto = db.get(Producto, producto_id)
    if not producto:
        raise HTTPException(404, "Producto no encontrado")
    _check(data)
    antes = ProductoOut.model_validate(producto).model_dump()
    for k, v in data.model_dump().items():
        setattr(producto, k, v)
    audit(db, request, user, "actualizar", "productos", producto.id, antes, data.model_dump())
    db.commit()
    return producto


@router.delete("/productos/{producto_id}", status_code=204)
def deactivate_producto(producto_id: int, request: Request, db: Session = Depends(get_db),
                        user: Usuario = Depends(require_roles("Usuario"))):
    producto = db.get(Producto, producto_id)
    if not producto:
        raise HTTPException(404, "Producto no encontrado")
    producto.activo = False
    audit(db, request, user, "desactivar", "productos", producto.id)
    db.commit()
