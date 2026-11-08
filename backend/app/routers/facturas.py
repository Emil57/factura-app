from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, current_user, require_roles
from ..models import Cliente, DetalleFactura, Emisor, Factura, Usuario
from ..sat import catalogs as cat
from ..schemas import CancelIn, FacturaIn, FacturaListOut, FacturaOut
from ..services.cfdi_builder import facturama_payload, preview_xml, totals_for
from ..services.pac import MockPAC, PACError, get_pac
from ..services.taxes import LineInput, compute_invoice
from ..services.validation import validate_invoice

router = APIRouter(prefix="/api/facturas", tags=["facturas"])
MX_TZ = ZoneInfo("America/Mexico_City")


def _get(db: Session, factura_id: int) -> Factura:
    factura = db.get(Factura, factura_id)
    if not factura:
        raise HTTPException(404, "Factura no encontrada")
    return factura


def _check_lines(data: FacturaIn) -> None:
    for i, d in enumerate(data.detalles, start=1):
        if d.objeto_imp not in cat.OBJETOS_IMPUESTO:
            raise HTTPException(422, f"Concepto {i}: objeto de impuesto inválido")
        if d.iva_tasa is not None and d.iva_tasa not in cat.TASAS_IVA:
            raise HTTPException(422, f"Concepto {i}: tasa de IVA inválida")
        if d.ieps_tasa is not None and d.ieps_tasa not in cat.TASAS_IEPS:
            raise HTTPException(422, f"Concepto {i}: tasa de IEPS inválida")


def _apply(db: Session, factura: Factura, data: FacturaIn) -> None:
    emisor, cliente = db.get(Emisor, data.emisor_id), db.get(Cliente, data.cliente_id)
    if not emisor or not emisor.activo:
        raise HTTPException(422, "Emisor inválido")
    if not cliente or not cliente.activo:
        raise HTTPException(422, "Cliente inválido")
    _check_lines(data)

    for k, v in data.model_dump(exclude={"detalles"}).items():
        setattr(factura, k, v)
    factura.serie = emisor.serie
    factura.emisor, factura.cliente = emisor, cliente
    factura.detalles = [DetalleFactura(**d.model_dump()) for d in data.detalles]

    try:
        totals = totals_for(factura)
    except ValueError as e:
        raise HTTPException(422, str(e))
    for det, r in zip(factura.detalles, totals.lines):
        det.importe, det.total = r.importe, r.total
    factura.subtotal, factura.descuento = totals.subtotal, totals.descuento
    factura.total_traslados, factura.total_retenciones = totals.traslados, totals.retenciones
    factura.total = totals.total


@router.get("", response_model=list[FacturaListOut], dependencies=[Depends(current_user)])
def list_facturas(estado: str | None = None, emisor_id: int | None = None, cliente_id: int | None = None,
                  q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Factura).join(Factura.cliente)
    if estado:
        stmt = stmt.where(Factura.estado == estado)
    if emisor_id:
        stmt = stmt.where(Factura.emisor_id == emisor_id)
    if cliente_id:
        stmt = stmt.where(Factura.cliente_id == cliente_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Factura.uuid.ilike(like), Cliente.razon_social.ilike(like), Cliente.rfc.ilike(like)))
    return db.scalars(stmt.order_by(Factura.id.desc()).limit(300)).all()


@router.post("/calcular", dependencies=[Depends(current_user)])
def calcular(data: FacturaIn):
    """Live totals for the invoice editor; nothing is saved."""
    _check_lines(data)
    try:
        totals = compute_invoice([LineInput(**d.model_dump(include=set(LineInput.__dataclass_fields__)))
                                  for d in data.detalles])
    except ValueError as e:
        raise HTTPException(422, str(e))
    return totals.summary()


@router.get("/{factura_id}", response_model=FacturaOut, dependencies=[Depends(current_user)])
def get_factura(factura_id: int, db: Session = Depends(get_db)):
    return _get(db, factura_id)


@router.get("/{factura_id}/resumen", dependencies=[Depends(current_user)])
def resumen(factura_id: int, db: Session = Depends(get_db)):
    return totals_for(_get(db, factura_id)).summary()


@router.post("", response_model=FacturaOut, status_code=201)
def create_factura(data: FacturaIn, request: Request, db: Session = Depends(get_db),
                   user: Usuario = Depends(require_roles("Usuario"))):
    factura = Factura(usuario_id=user.id, estado="Borrador")
    _apply(db, factura, data)
    db.add(factura)
    db.flush()
    audit(db, request, user, "crear", "facturas", factura.id, despues={"total": factura.total})
    db.commit()
    return factura


@router.put("/{factura_id}", response_model=FacturaOut)
def update_factura(factura_id: int, data: FacturaIn, request: Request, db: Session = Depends(get_db),
                   user: Usuario = Depends(require_roles("Usuario"))):
    factura = _get(db, factura_id)
    if factura.estado != "Borrador":
        raise HTTPException(409, "Solo se pueden editar facturas en borrador")
    _apply(db, factura, data)
    audit(db, request, user, "actualizar", "facturas", factura.id, despues={"total": factura.total})
    db.commit()
    return factura


@router.delete("/{factura_id}", status_code=204)
def delete_draft(factura_id: int, request: Request, db: Session = Depends(get_db),
                 user: Usuario = Depends(require_roles("Usuario"))):
    factura = _get(db, factura_id)
    if factura.estado != "Borrador":
        raise HTTPException(409, "Solo se pueden eliminar borradores; las facturas emitidas se cancelan")
    audit(db, request, user, "eliminar", "facturas", factura.id)
    db.delete(factura)
    db.commit()


@router.post("/{factura_id}/validar", dependencies=[Depends(current_user)])
def validar(factura_id: int, db: Session = Depends(get_db)):
    factura = _get(db, factura_id)
    return {"errores": validate_invoice(factura.emisor, factura.cliente, factura)}


@router.post("/{factura_id}/timbrar", response_model=FacturaOut)
def timbrar(factura_id: int, request: Request, db: Session = Depends(get_db),
            user: Usuario = Depends(require_roles("Usuario"))):
    factura = _get(db, factura_id)
    if factura.estado != "Borrador":
        raise HTTPException(409, "La factura ya fue timbrada")
    errors = validate_invoice(factura.emisor, factura.cliente, factura)
    if errors:
        raise HTTPException(422, errors)

    pac = get_pac()
    if not isinstance(pac, MockPAC) and not factura.emisor.csd_cargado:
        raise HTTPException(422, "Carga el CSD del emisor antes de timbrar")

    # Lock the issuer row so two concurrent stamps never get the same folio.
    emisor = db.scalar(select(Emisor).where(Emisor.id == factura.emisor_id).with_for_update()
                       .execution_options(populate_existing=True))
    factura.serie, factura.folio = emisor.serie, emisor.siguiente_folio
    factura.fecha_emision = datetime.now(MX_TZ).replace(microsecond=0)

    try:
        result = pac.stamp(facturama_payload(factura, emisor, factura.cliente),
                           preview_xml(factura, emisor, factura.cliente, uuid="__UUID__"))
    except PACError as e:
        db.rollback()  # releases the folio
        raise HTTPException(502, {"mensaje": str(e), "detalle": e.detail})

    emisor.siguiente_folio += 1
    factura.pac_id, factura.uuid = result.pac_id, result.uuid
    factura.fecha_timbrado, factura.xml = result.fecha_timbrado, result.xml
    factura.estado = "Emitida"
    audit(db, request, user, "timbrar", "facturas", factura.id, despues={"uuid": result.uuid, "pac": pac.name})
    db.commit()
    return factura


@router.post("/{factura_id}/cancelar", response_model=FacturaOut)
def cancelar(factura_id: int, data: CancelIn, request: Request, db: Session = Depends(get_db),
             user: Usuario = Depends(require_roles("Contador"))):
    factura = _get(db, factura_id)
    if factura.estado not in ("Emitida", "Cancelación pendiente"):
        raise HTTPException(409, "Solo se pueden cancelar facturas emitidas")
    if data.motivo == "01" and not data.uuid_sustitucion:
        raise HTTPException(422, "El motivo 01 requiere el UUID de la factura que la sustituye")
    try:
        result = get_pac().cancel(factura.pac_id, data.motivo,
                                  data.uuid_sustitucion if data.motivo == "01" else None)
    except PACError as e:
        raise HTTPException(502, {"mensaje": str(e), "detalle": e.detail})

    factura.motivo_cancelacion = data.motivo
    if result.status == "canceled":
        factura.estado = "Cancelada"
        factura.fecha_cancelacion = datetime.now(MX_TZ)
    elif result.status == "pending":
        factura.estado = "Cancelación pendiente"  # receptor must accept
    if result.acuse_xml:
        factura.acuse_cancelacion = result.acuse_xml
    audit(db, request, user, "cancelar", "facturas", factura.id,
          despues={"motivo": data.motivo, "status": result.status, "mensaje": result.message})
    db.commit()
    return factura


@router.get("/{factura_id}/xml", dependencies=[Depends(current_user)])
def descargar_xml(factura_id: int, db: Session = Depends(get_db)):
    factura = _get(db, factura_id)
    if factura.xml:
        xml, name = factura.xml, f"{factura.serie or ''}{factura.folio}_{factura.uuid}.xml"
    else:
        xml, name = preview_xml(factura, factura.emisor, factura.cliente), f"borrador_{factura.id}.xml"
    return Response(xml, media_type="application/xml",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/{factura_id}/pdf", dependencies=[Depends(current_user)])
def descargar_pdf(factura_id: int, db: Session = Depends(get_db)):
    factura = _get(db, factura_id)
    if not factura.pac_id:
        raise HTTPException(409, "La factura aún no está timbrada")
    try:
        pdf = get_pac().download(factura.pac_id, "pdf")
    except PACError as e:
        raise HTTPException(502, {"mensaje": str(e), "detalle": e.detail})
    name = f"{factura.serie or ''}{factura.folio}_{factura.uuid}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})
