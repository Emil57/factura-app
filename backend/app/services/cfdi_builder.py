"""Turn an invoice (duck-typed ORM objects) into PAC payloads / preview XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import Decimal

from ..sat.catalogs import RFC_PUBLICO_GENERAL
from ..sat.rfc import normalize_rfc
from .taxes import LineInput, Totals, compute_invoice


def line_inputs(factura) -> list[LineInput]:
    return [
        LineInput(
            cantidad=Decimal(str(d.cantidad)),
            precio_unitario=Decimal(str(d.precio_unitario)),
            descuento=Decimal(str(d.descuento or 0)),
            objeto_imp=d.objeto_imp,
            iva_tasa=d.iva_tasa,
            ieps_tasa=d.ieps_tasa,
            ret_isr_tasa=d.ret_isr_tasa,
            ret_iva_tasa=d.ret_iva_tasa,
        )
        for d in factura.detalles
    ]


def totals_for(factura) -> Totals:
    return compute_invoice(line_inputs(factura))


def _facturama_tax(t) -> dict:
    if t.tipo_factor == "Exento":
        name = "IVA Exento"
    else:
        name = t.impuesto
    return {
        "Name": name,
        "Base": float(t.base),
        "Rate": float(t.tasa) if t.tasa is not None else 0,
        "Total": float(t.importe),
        "IsRetention": t.tipo == "retencion",
        "IsFederalTax": True,
    }


def facturama_payload(factura, emisor, cliente) -> dict:
    """Payload for Facturama API Multiemisor: POST /api-lite/4/cfdis."""
    totals = totals_for(factura)
    is_publico = normalize_rfc(cliente.rfc) == RFC_PUBLICO_GENERAL

    items = []
    for d, r in zip(factura.detalles, totals.lines):
        item = {
            "ProductCode": d.clave_prod_serv,
            "IdentificationNumber": d.codigo or None,
            "Description": d.descripcion,
            "Unit": d.unidad or None,
            "UnitCode": d.clave_unidad,
            "UnitPrice": float(d.precio_unitario),
            "Quantity": float(d.cantidad),
            "Subtotal": float(r.importe),
            "Discount": float(r.descuento) if r.descuento else None,
            "TaxObject": d.objeto_imp,
            "Total": float(r.total),
        }
        if r.impuestos:
            item["Taxes"] = [_facturama_tax(t) for t in r.impuestos]
        items.append({k: v for k, v in item.items() if v is not None})

    payload = {
        "NameId": "1" if factura.tipo_comprobante == "I" else "2",
        "CfdiType": factura.tipo_comprobante,
        "Currency": factura.moneda,
        "Serie": factura.serie or None,
        "Folio": str(factura.folio) if factura.folio else None,
        "PaymentForm": factura.forma_pago,
        "PaymentMethod": factura.metodo_pago,
        "ExpeditionPlace": emisor.codigo_postal,
        "Exportation": factura.exportacion,
        "PaymentConditions": factura.condiciones_pago or None,
        "Observations": factura.observaciones or None,
        "Issuer": {
            "Rfc": normalize_rfc(emisor.rfc),
            "Name": emisor.razon_social,
            "FiscalRegime": emisor.regimen_fiscal,
        },
        "Receiver": {
            "Rfc": normalize_rfc(cliente.rfc),
            "Name": cliente.razon_social,
            "CfdiUse": factura.uso_cfdi,
            "FiscalRegime": cliente.regimen_fiscal,
            "TaxZipCode": cliente.codigo_postal,
        },
        "Items": items,
    }
    if factura.moneda != "MXN":
        payload["ExchangeRate"] = float(factura.tipo_cambio)
    if is_publico:
        # Factura global al público en general: periodicidad mensual del mes de emisión.
        payload["GlobalInformation"] = {
            "Periodicity": "04", "Months": factura_month(factura), "Year": factura_year(factura)}
    if factura.cfdi_relacionado_uuid:
        payload["Relations"] = {"Type": factura.tipo_relacion or "01",
                                "Cfdis": [{"Uuid": factura.cfdi_relacionado_uuid}]}
    return {k: v for k, v in payload.items() if v is not None}


def factura_month(factura) -> str:
    return f"{factura.fecha_emision.month:02d}" if factura.fecha_emision else "01"


def factura_year(factura) -> str:
    return str(factura.fecha_emision.year) if factura.fecha_emision else "2026"


CFDI_NS = "http://www.sat.gob.mx/cfd/4"


def preview_xml(factura, emisor, cliente, uuid: str | None = None) -> str:
    """Unsigned CFDI 4.0 XML. Used for previews and by the mock PAC (no fiscal validity)."""
    ET.register_namespace("cfdi", CFDI_NS)
    q = lambda tag: f"{{{CFDI_NS}}}{tag}"  # noqa: E731
    totals = totals_for(factura)

    attrs = {
        "Version": "4.0",
        "Serie": factura.serie or "",
        "Folio": str(factura.folio or ""),
        "Fecha": (factura.fecha_emision.strftime("%Y-%m-%dT%H:%M:%S") if factura.fecha_emision else ""),
        "FormaPago": factura.forma_pago,
        "SubTotal": str(totals.subtotal),
        "Moneda": factura.moneda,
        "Total": str(totals.total),
        "TipoDeComprobante": factura.tipo_comprobante,
        "Exportacion": factura.exportacion,
        "MetodoPago": factura.metodo_pago,
        "LugarExpedicion": emisor.codigo_postal,
    }
    if totals.descuento:
        attrs["Descuento"] = str(totals.descuento)
    if factura.moneda != "MXN":
        attrs["TipoCambio"] = str(factura.tipo_cambio)
    root = ET.Element(q("Comprobante"), {k: v for k, v in attrs.items() if v != ""})
    ET.SubElement(root, q("Emisor"), {"Rfc": normalize_rfc(emisor.rfc), "Nombre": emisor.razon_social,
                                       "RegimenFiscal": emisor.regimen_fiscal})
    ET.SubElement(root, q("Receptor"), {"Rfc": normalize_rfc(cliente.rfc), "Nombre": cliente.razon_social,
                                         "DomicilioFiscalReceptor": cliente.codigo_postal,
                                         "RegimenFiscalReceptor": cliente.regimen_fiscal,
                                         "UsoCFDI": factura.uso_cfdi})
    conceptos = ET.SubElement(root, q("Conceptos"))
    for d, r in zip(factura.detalles, totals.lines):
        c_attrs = {"ClaveProdServ": d.clave_prod_serv, "Cantidad": str(d.cantidad), "ClaveUnidad": d.clave_unidad,
                   "Descripcion": d.descripcion, "ValorUnitario": str(d.precio_unitario),
                   "Importe": str(r.importe), "ObjetoImp": d.objeto_imp}
        if r.descuento:
            c_attrs["Descuento"] = str(r.descuento)
        c = ET.SubElement(conceptos, q("Concepto"), c_attrs)
        if r.impuestos:
            imp = ET.SubElement(c, q("Impuestos"))
            for tipo, wrapper, tag in (("traslado", "Traslados", "Traslado"), ("retencion", "Retenciones", "Retencion")):
                taxes = [t for t in r.impuestos if t.tipo == tipo]
                if not taxes:
                    continue
                w = ET.SubElement(imp, q(wrapper))
                for t in taxes:
                    ta = {"Base": str(t.base), "Impuesto": _sat_tax_code(t.impuesto), "TipoFactor": t.tipo_factor}
                    if t.tasa is not None:
                        ta["TasaOCuota"] = str(t.tasa)
                        ta["Importe"] = str(t.importe)
                    ET.SubElement(w, q(tag), ta)
    if totals.traslados or totals.retenciones:
        attrs = {}
        if totals.retenciones:
            attrs["TotalImpuestosRetenidos"] = str(totals.retenciones)
        if any(t.tipo == "traslado" for l in totals.lines for t in l.impuestos):
            attrs["TotalImpuestosTrasladados"] = str(totals.traslados)
        ET.SubElement(root, q("Impuestos"), attrs)
    if uuid:
        comp = ET.SubElement(root, q("Complemento"))
        ET.SubElement(comp, "TimbreFiscalDigital", {"UUID": uuid, "Leyenda": "SIN VALIDEZ FISCAL - MOCK PAC"})
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def _sat_tax_code(name: str) -> str:
    return {"ISR": "001", "IVA": "002", "IEPS": "003"}[name]
