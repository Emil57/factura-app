from pydantic import BaseModel
from datetime import date

class FacturaCreate(BaseModel):
    cliente: str
    monto: float
    fecha: date

class Factura(FacturaCreate):
    id: int
