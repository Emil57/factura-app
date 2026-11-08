from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Cliente, Emisor
from ..sat.catalogs import all_catalogs
from ..sat.rfc import tipo_persona
from ..services.taxes import suggest_withholdings

router = APIRouter(prefix="/api/catalogos", tags=["catálogos"], dependencies=[Depends(current_user)])


@router.get("")
def catalogos():
    return all_catalogs()


@router.get("/retenciones-sugeridas")
def retenciones_sugeridas(emisor_id: int, cliente_id: int, db: Session = Depends(get_db)):
    emisor, cliente = db.get(Emisor, emisor_id), db.get(Cliente, cliente_id)
    if not emisor or not cliente:
        raise HTTPException(404, "Emisor o cliente no encontrado")
    return suggest_withholdings(emisor.regimen_fiscal, tipo_persona(emisor.rfc), cliente.tipo_persona)
