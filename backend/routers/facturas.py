from fastapi import APIRouter, HTTPException
from typing import List
from backend.schemas.factura import Factura, FacturaCreate

router = APIRouter(
    prefix="/facturas",
    tags=["facturas"]
)

# Simulación de base de datos en memoria
db_facturas = []

@router.post("/", response_model=Factura)
def crear_factura(factura: FacturaCreate):
    nueva_factura = Factura(id=len(db_facturas)+1, **factura.dict())
    db_facturas.append(nueva_factura)
    return nueva_factura

@router.get("/", response_model=List[Factura])
def listar_facturas():
    return db_facturas

@router.get("/{factura_id}", response_model=Factura)
def obtener_factura(factura_id: int):
    for factura in db_facturas:
        if factura.id == factura_id:
            return factura
    raise HTTPException(status_code=404, detail="Factura no encontrada")

@router.put("/{factura_id}", response_model=Factura)
def actualizar_factura(factura_id: int, factura_actualizada: FacturaCreate):
    for i, factura in enumerate(db_facturas):
        if factura.id == factura_id:
            db_facturas[i] = Factura(id=factura_id, **factura_actualizada.dict())
            return db_facturas[i]
    raise HTTPException(status_code=404, detail="Factura no encontrada")

@router.delete("/{factura_id}")
def eliminar_factura(factura_id: int):
    for i, factura in enumerate(db_facturas):
        if factura.id == factura_id:
            db_facturas.pop(i)
            return {"message": "Factura eliminada"}
    raise HTTPException(status_code=404, detail="Factura no encontrada")
