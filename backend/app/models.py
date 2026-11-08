"""Database models, adapted from docs/db.txt to CFDI 4.0.

Changes vs. the original design:
* `ConfiguracionEmpresa` -> `Emisor`: many issuers (personas físicas or morales) so the
  app can invoice for any taxpayer through Facturama Multiemisor.
* `Clientes` gains `codigo_postal` (DomicilioFiscalReceptor, required in CFDI 4.0);
  `TipoPersona` is derived from the RFC length instead of a separate table.
* `Productos` / `DetalleFactura` carry SAT keys (ClaveProdServ, ClaveUnidad, ObjetoImp)
  and per-concept tax rates, including withholdings (ISR / IVA retenido).
* `Impuestos` catalog table is replaced by the SAT catalogs in `app/sat/catalogs.py`.
* `Sesiones` is replaced by stateless JWT; payments (`Pagos`, complemento de pago) are
  the next milestone.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class Rol(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)  # Admin, Usuario, Contador
    descripcion: Mapped[str | None] = mapped_column(String(255))
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UsuarioRol(Base):
    __tablename__ = "usuario_roles"
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    fecha_asignacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    roles: Mapped[list[Rol]] = relationship(secondary="usuario_roles", lazy="selectin")

    @property
    def role_names(self) -> list[str]:
        return [r.nombre for r in self.roles]


class Emisor(Base):
    __tablename__ = "emisores"
    id: Mapped[int] = mapped_column(primary_key=True)
    rfc: Mapped[str] = mapped_column(String(13), unique=True, index=True)
    razon_social: Mapped[str] = mapped_column(String(300))
    regimen_fiscal: Mapped[str] = mapped_column(String(3))
    codigo_postal: Mapped[str] = mapped_column(String(5))  # LugarExpedicion
    email: Mapped[str | None] = mapped_column(String(255))
    telefono: Mapped[str | None] = mapped_column(String(30))
    direccion: Mapped[str | None] = mapped_column(String(500))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    serie: Mapped[str] = mapped_column(String(25), default="A")
    siguiente_folio: Mapped[int] = mapped_column(Integer, default=1)
    csd_cargado: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Cliente(Base):
    __tablename__ = "clientes"
    id: Mapped[int] = mapped_column(primary_key=True)
    rfc: Mapped[str] = mapped_column(String(13), index=True)
    razon_social: Mapped[str] = mapped_column(String(300))
    tipo_persona: Mapped[str] = mapped_column(String(10))  # fisica | moral
    regimen_fiscal: Mapped[str] = mapped_column(String(3))
    uso_cfdi: Mapped[str] = mapped_column(String(4), default="G03")
    codigo_postal: Mapped[str] = mapped_column(String(5))
    email: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Categoria(Base):
    __tablename__ = "categorias"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255))


class Producto(Base):
    __tablename__ = "productos"
    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id"))
    codigo: Mapped[str | None] = mapped_column(String(100))  # NoIdentificacion
    nombre: Mapped[str] = mapped_column(String(255))
    descripcion: Mapped[str | None] = mapped_column(String(1000))
    clave_prod_serv: Mapped[str] = mapped_column(String(8))
    clave_unidad: Mapped[str] = mapped_column(String(3))
    unidad: Mapped[str | None] = mapped_column(String(20))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    objeto_imp: Mapped[str] = mapped_column(String(2), default="02")
    iva_tasa: Mapped[str | None] = mapped_column(String(10), default="0.160000")
    ieps_tasa: Mapped[str | None] = mapped_column(String(10))
    stock: Mapped[int | None] = mapped_column(Integer)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    categoria: Mapped[Categoria | None] = relationship(lazy="selectin")


ESTADOS = ("Borrador", "Emitida", "Cancelación pendiente", "Cancelada")


class Factura(Base):
    __tablename__ = "facturas"
    __table_args__ = (UniqueConstraint("emisor_id", "serie", "folio", name="uq_factura_folio"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    emisor_id: Mapped[int] = mapped_column(ForeignKey("emisores.id"))
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))

    tipo_comprobante: Mapped[str] = mapped_column(String(1), default="I")
    serie: Mapped[str | None] = mapped_column(String(25))
    folio: Mapped[int | None] = mapped_column(Integer)  # assigned when stamped (no gaps)
    fecha_emision: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    uso_cfdi: Mapped[str] = mapped_column(String(4))
    forma_pago: Mapped[str] = mapped_column(String(2))
    metodo_pago: Mapped[str] = mapped_column(String(3))
    moneda: Mapped[str] = mapped_column(String(3), default="MXN")
    tipo_cambio: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    exportacion: Mapped[str] = mapped_column(String(2), default="01")
    condiciones_pago: Mapped[str | None] = mapped_column(String(255))
    observaciones: Mapped[str | None] = mapped_column(Text)
    cfdi_relacionado_uuid: Mapped[str | None] = mapped_column(String(36))
    tipo_relacion: Mapped[str | None] = mapped_column(String(2))

    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    descuento: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_traslados: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_retenciones: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    estado: Mapped[str] = mapped_column(String(30), default="Borrador")
    pac_id: Mapped[str | None] = mapped_column(String(100))
    uuid: Mapped[str | None] = mapped_column(String(36), index=True)
    fecha_timbrado: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    xml: Mapped[str | None] = mapped_column(Text)
    motivo_cancelacion: Mapped[str | None] = mapped_column(String(2))
    fecha_cancelacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acuse_cancelacion: Mapped[str | None] = mapped_column(Text)

    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    emisor: Mapped[Emisor] = relationship(lazy="selectin")
    cliente: Mapped[Cliente] = relationship(lazy="selectin")
    detalles: Mapped[list[DetalleFactura]] = relationship(
        back_populates="factura", cascade="all, delete-orphan", order_by="DetalleFactura.id", lazy="selectin")


class DetalleFactura(Base):
    __tablename__ = "detalle_factura"
    id: Mapped[int] = mapped_column(primary_key=True)
    factura_id: Mapped[int] = mapped_column(ForeignKey("facturas.id", ondelete="CASCADE"), index=True)
    producto_id: Mapped[int | None] = mapped_column(ForeignKey("productos.id"))
    codigo: Mapped[str | None] = mapped_column(String(100))
    clave_prod_serv: Mapped[str] = mapped_column(String(8))
    clave_unidad: Mapped[str] = mapped_column(String(3))
    unidad: Mapped[str | None] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(String(1000))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    descuento: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    objeto_imp: Mapped[str] = mapped_column(String(2), default="02")
    iva_tasa: Mapped[str | None] = mapped_column(String(10))
    ieps_tasa: Mapped[str | None] = mapped_column(String(10))
    ret_isr_tasa: Mapped[str | None] = mapped_column(String(10))
    ret_iva_tasa: Mapped[str | None] = mapped_column(String(10))
    importe: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    factura: Mapped[Factura] = relationship(back_populates="detalles")


class LogActividad(Base):
    __tablename__ = "log_actividades"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    accion: Mapped[str] = mapped_column(String(50))
    tabla_afectada: Mapped[str] = mapped_column(String(50))
    registro_id: Mapped[int | None] = mapped_column(Integer)
    valor_anterior: Mapped[str | None] = mapped_column(Text)
    valor_nuevo: Mapped[str | None] = mapped_column(Text)
    fecha_accion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    direccion_ip: Mapped[str | None] = mapped_column(String(45))
