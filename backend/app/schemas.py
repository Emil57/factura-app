from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from .sat import catalogs as cat
from .sat.rfc import is_valid_rfc, normalize_rfc


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioOut(ORM):
    id: int
    email: str
    nombre: str
    activo: bool
    role_names: list[str]


class UsuarioIn(BaseModel):
    email: str
    nombre: str
    password: str = Field(min_length=8)
    roles: list[str] = ["Usuario"]


# ---------- Shared validators ----------
def _rfc(v: str) -> str:
    v = normalize_rfc(v)
    if not is_valid_rfc(v):
        raise ValueError("RFC con formato inválido")
    return v


def _regimen(v: str) -> str:
    if v not in cat.REGIMENES_FISCALES:
        raise ValueError("Régimen fiscal no existe en el catálogo del SAT")
    return v


def _cp(v: str) -> str:
    if not (len(v) == 5 and v.isdigit()):
        raise ValueError("El código postal debe tener 5 dígitos")
    return v


RFC = Annotated[str, AfterValidator(_rfc)]
Regimen = Annotated[str, AfterValidator(_regimen)]
CodigoPostal = Annotated[str, AfterValidator(_cp)]


# ---------- Emisores ----------
class EmisorIn(BaseModel):
    rfc: RFC
    razon_social: str = Field(min_length=1, max_length=300)
    regimen_fiscal: Regimen
    codigo_postal: CodigoPostal
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    logo_url: str | None = None
    serie: str = "A"
    siguiente_folio: int = Field(default=1, ge=1)


    @field_validator("razon_social")
    @classmethod
    def upper_name(cls, v: str) -> str:
        # CFDI 4.0: name must match the Constancia de Situación Fiscal, without régimen societario.
        return v.strip().upper()


class EmisorOut(ORM):
    id: int
    rfc: str
    razon_social: str
    regimen_fiscal: str
    codigo_postal: str
    email: str | None
    telefono: str | None
    direccion: str | None
    logo_url: str | None
    serie: str
    siguiente_folio: int
    csd_cargado: bool
    activo: bool


class CSDIn(BaseModel):
    certificado_b64: str = Field(description=".cer en Base64")
    llave_b64: str = Field(description=".key en Base64")
    password: str


# ---------- Clientes ----------
class ClienteIn(BaseModel):
    rfc: RFC
    razon_social: str = Field(min_length=1, max_length=300)
    regimen_fiscal: Regimen
    uso_cfdi: str = "G03"
    codigo_postal: CodigoPostal
    email: str | None = None


    @field_validator("razon_social")
    @classmethod
    def upper_name(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("uso_cfdi")
    @classmethod
    def check_uso(cls, v: str) -> str:
        if v not in cat.USOS_CFDI:
            raise ValueError("Uso de CFDI no existe en el catálogo")
        return v


class ClienteOut(ORM):
    id: int
    rfc: str
    razon_social: str
    tipo_persona: str
    regimen_fiscal: str
    uso_cfdi: str
    codigo_postal: str
    email: str | None
    activo: bool


# ---------- Productos ----------
class ProductoIn(BaseModel):
    categoria_id: int | None = None
    codigo: str | None = None
    nombre: str = Field(min_length=1)
    descripcion: str | None = None
    clave_prod_serv: str = Field(pattern=r"^\d{8}$")
    clave_unidad: str = Field(min_length=1, max_length=3)
    unidad: str | None = None
    precio_unitario: Decimal = Field(ge=0)
    objeto_imp: str = "02"
    iva_tasa: str | None = "0.160000"
    ieps_tasa: str | None = None
    stock: int | None = None


class ProductoOut(ORM):
    id: int
    categoria_id: int | None
    codigo: str | None
    nombre: str
    descripcion: str | None
    clave_prod_serv: str
    clave_unidad: str
    unidad: str | None
    precio_unitario: Decimal
    objeto_imp: str
    iva_tasa: str | None
    ieps_tasa: str | None
    stock: int | None
    activo: bool


class CategoriaIn(BaseModel):
    nombre: str
    descripcion: str | None = None


class CategoriaOut(ORM):
    id: int
    nombre: str
    descripcion: str | None


# ---------- Facturas ----------
class DetalleIn(BaseModel):
    producto_id: int | None = None
    codigo: str | None = None
    clave_prod_serv: str = Field(pattern=r"^\d{8}$")
    clave_unidad: str = Field(min_length=1, max_length=3)
    unidad: str | None = None
    descripcion: str = Field(min_length=1, max_length=1000)
    cantidad: Decimal = Field(gt=0)
    precio_unitario: Decimal = Field(ge=0)
    descuento: Decimal = Field(default=Decimal("0"), ge=0)
    objeto_imp: str = "02"
    iva_tasa: str | None = "0.160000"
    ieps_tasa: str | None = None
    ret_isr_tasa: str | None = None
    ret_iva_tasa: str | None = None


class FacturaIn(BaseModel):
    emisor_id: int
    cliente_id: int
    tipo_comprobante: str = "I"
    uso_cfdi: str
    forma_pago: str
    metodo_pago: str
    moneda: str = "MXN"
    tipo_cambio: Decimal | None = None
    exportacion: str = "01"
    condiciones_pago: str | None = None
    observaciones: str | None = None
    cfdi_relacionado_uuid: str | None = None
    tipo_relacion: str | None = None
    detalles: list[DetalleIn] = Field(min_length=1)


class DetalleOut(ORM):
    id: int
    producto_id: int | None
    codigo: str | None
    clave_prod_serv: str
    clave_unidad: str
    unidad: str | None
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    descuento: Decimal
    objeto_imp: str
    iva_tasa: str | None
    ieps_tasa: str | None
    ret_isr_tasa: str | None
    ret_iva_tasa: str | None
    importe: Decimal
    total: Decimal


class FacturaListOut(ORM):
    id: int
    serie: str | None
    folio: int | None
    estado: str
    uuid: str | None
    tipo_comprobante: str
    fecha_emision: datetime | None
    fecha_creacion: datetime
    total: Decimal
    moneda: str
    emisor: EmisorOut
    cliente: ClienteOut


class FacturaOut(FacturaListOut):
    emisor_id: int
    cliente_id: int
    uso_cfdi: str
    forma_pago: str
    metodo_pago: str
    tipo_cambio: Decimal | None
    exportacion: str
    condiciones_pago: str | None
    observaciones: str | None
    cfdi_relacionado_uuid: str | None
    tipo_relacion: str | None
    subtotal: Decimal
    descuento: Decimal
    total_traslados: Decimal
    total_retenciones: Decimal
    fecha_timbrado: datetime | None
    motivo_cancelacion: str | None
    fecha_cancelacion: datetime | None
    detalles: list[DetalleOut]


class CancelIn(BaseModel):
    motivo: str
    uuid_sustitucion: str | None = None

    @field_validator("motivo")
    @classmethod
    def check_motivo(cls, v: str) -> str:
        if v not in cat.MOTIVOS_CANCELACION:
            raise ValueError("Motivo de cancelación inválido")
        return v
