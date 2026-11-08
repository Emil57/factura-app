import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, current_user, require_roles
from ..models import Emisor, Usuario
from ..schemas import CSDIn, EmisorIn, EmisorOut
from ..services.pac import PACError, get_pac
from ..services.validation import validate_party

router = APIRouter(prefix="/api/emisores", tags=["emisores"])


def _get(db: Session, emisor_id: int) -> Emisor:
    emisor = db.get(Emisor, emisor_id)
    if not emisor:
        raise HTTPException(404, "Emisor no encontrado")
    return emisor


@router.get("", response_model=list[EmisorOut], dependencies=[Depends(current_user)])
def list_emisores(db: Session = Depends(get_db)):
    return db.scalars(select(Emisor).where(Emisor.activo).order_by(Emisor.razon_social)).all()


@router.post("", response_model=EmisorOut, status_code=201)
def create_emisor(data: EmisorIn, request: Request, db: Session = Depends(get_db),
                  user: Usuario = Depends(require_roles())):
    errors = validate_party(data.rfc, data.regimen_fiscal, data.codigo_postal, "Emisor")
    if errors:
        raise HTTPException(422, errors)
    if db.scalar(select(Emisor).where(Emisor.rfc == data.rfc)):
        raise HTTPException(409, "Ya existe un emisor con ese RFC")
    emisor = Emisor(**data.model_dump())
    db.add(emisor)
    db.flush()
    audit(db, request, user, "crear", "emisores", emisor.id, despues=data.model_dump())
    db.commit()
    return emisor


@router.put("/{emisor_id}", response_model=EmisorOut)
def update_emisor(emisor_id: int, data: EmisorIn, request: Request, db: Session = Depends(get_db),
                  user: Usuario = Depends(require_roles())):
    emisor = _get(db, emisor_id)
    errors = validate_party(data.rfc, data.regimen_fiscal, data.codigo_postal, "Emisor")
    if errors:
        raise HTTPException(422, errors)
    if data.rfc != emisor.rfc and db.scalar(select(Emisor).where(Emisor.rfc == data.rfc)):
        raise HTTPException(409, "Ya existe un emisor con ese RFC")
    antes = EmisorOut.model_validate(emisor).model_dump()
    if data.rfc != emisor.rfc:
        emisor.csd_cargado = False  # new RFC needs its own CSD
    for k, v in data.model_dump().items():
        setattr(emisor, k, v)
    audit(db, request, user, "actualizar", "emisores", emisor.id, antes, data.model_dump())
    db.commit()
    return emisor


@router.post("/{emisor_id}/csd", response_model=EmisorOut)
def upload_csd(emisor_id: int, data: CSDIn, request: Request, db: Session = Depends(get_db),
               user: Usuario = Depends(require_roles())):
    """Send the issuer's CSD (.cer/.key) to the PAC. The key is never stored in our DB."""
    emisor = _get(db, emisor_id)
    try:
        base64.b64decode(data.certificado_b64, validate=True)
        base64.b64decode(data.llave_b64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, "El certificado y la llave deben venir en Base64")
    try:
        get_pac().upload_csd(emisor.rfc, data.certificado_b64, data.llave_b64, data.password)
    except PACError as e:
        raise HTTPException(502, {"mensaje": str(e), "detalle": e.detail})
    emisor.csd_cargado = True
    audit(db, request, user, "cargar_csd", "emisores", emisor.id)
    db.commit()
    return emisor


@router.delete("/{emisor_id}", status_code=204)
def deactivate_emisor(emisor_id: int, request: Request, db: Session = Depends(get_db),
                      user: Usuario = Depends(require_roles())):
    emisor = _get(db, emisor_id)
    emisor.activo = False
    audit(db, request, user, "desactivar", "emisores", emisor.id)
    db.commit()
