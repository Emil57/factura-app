from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, current_user, require_roles
from ..models import Cliente, Usuario
from ..sat import catalogs as cat
from ..sat.rfc import is_generic_rfc, tipo_persona
from ..schemas import ClienteIn, ClienteOut

router = APIRouter(prefix="/api/clientes", tags=["clientes"])


def _check(data: ClienteIn) -> str:
    tipo = tipo_persona(data.rfc)
    if is_generic_rfc(data.rfc):
        if data.regimen_fiscal != "616" or data.uso_cfdi != "S01":
            raise HTTPException(422, "Para RFC genérico usa régimen 616 y uso de CFDI S01")
        return tipo
    if not cat.REGIMENES_FISCALES[data.regimen_fiscal][tipo]:
        raise HTTPException(422, f"El régimen {data.regimen_fiscal} no aplica para persona {tipo}")
    if not cat.USOS_CFDI[data.uso_cfdi][tipo]:
        raise HTTPException(422, f"El uso de CFDI {data.uso_cfdi} no aplica para persona {tipo}")
    return tipo


def _get(db: Session, cliente_id: int) -> Cliente:
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    return cliente


@router.get("", response_model=list[ClienteOut], dependencies=[Depends(current_user)])
def list_clientes(q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Cliente).where(Cliente.activo)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Cliente.rfc.ilike(like), Cliente.razon_social.ilike(like)))
    return db.scalars(stmt.order_by(Cliente.razon_social).limit(200)).all()


@router.get("/{cliente_id}", response_model=ClienteOut, dependencies=[Depends(current_user)])
def get_cliente(cliente_id: int, db: Session = Depends(get_db)):
    return _get(db, cliente_id)


@router.post("", response_model=ClienteOut, status_code=201)
def create_cliente(data: ClienteIn, request: Request, db: Session = Depends(get_db),
                   user: Usuario = Depends(require_roles("Usuario"))):
    tipo = _check(data)
    cliente = Cliente(**data.model_dump(), tipo_persona=tipo)
    db.add(cliente)
    db.flush()
    audit(db, request, user, "crear", "clientes", cliente.id, despues=data.model_dump())
    db.commit()
    return cliente


@router.put("/{cliente_id}", response_model=ClienteOut)
def update_cliente(cliente_id: int, data: ClienteIn, request: Request, db: Session = Depends(get_db),
                   user: Usuario = Depends(require_roles("Usuario"))):
    cliente = _get(db, cliente_id)
    tipo = _check(data)
    antes = ClienteOut.model_validate(cliente).model_dump()
    for k, v in data.model_dump().items():
        setattr(cliente, k, v)
    cliente.tipo_persona = tipo
    audit(db, request, user, "actualizar", "clientes", cliente.id, antes, data.model_dump())
    db.commit()
    return cliente


@router.delete("/{cliente_id}", status_code=204)
def deactivate_cliente(cliente_id: int, request: Request, db: Session = Depends(get_db),
                       user: Usuario = Depends(require_roles("Usuario"))):
    cliente = _get(db, cliente_id)
    cliente.activo = False
    audit(db, request, user, "desactivar", "clientes", cliente.id)
    db.commit()
