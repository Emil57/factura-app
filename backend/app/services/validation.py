"""CFDI 4.0 business validations run before an invoice is sent to the PAC.

Catching these locally gives clear Spanish messages instead of cryptic PAC errors.
Inputs are duck-typed (ORM objects or SimpleNamespace) so this module stays pure.
"""

from __future__ import annotations

import re
from decimal import Decimal

from ..sat import catalogs as cat
from ..sat.rfc import is_generic_rfc, is_valid_rfc, normalize_rfc, tipo_persona

_CP_RE = re.compile(r"^\d{5}$")


def _tipo(rfc: str) -> str | None:
    try:
        return tipo_persona(rfc)
    except ValueError:
        return None


def validate_party(rfc: str, regimen: str, codigo_postal: str, who: str) -> list[str]:
    errors: list[str] = []
    rfc = normalize_rfc(rfc)
    if not is_valid_rfc(rfc):
        errors.append(f"{who}: RFC '{rfc}' con formato inválido")
        return errors
    tipo = _tipo(rfc)
    reg = cat.REGIMENES_FISCALES.get(regimen)
    if reg is None:
        errors.append(f"{who}: régimen fiscal '{regimen}' no existe en el catálogo")
    elif tipo and not reg[tipo]:
        errors.append(f"{who}: el régimen {regimen} no aplica para persona {tipo}")
    if not _CP_RE.match(codigo_postal or ""):
        errors.append(f"{who}: el código postal debe tener 5 dígitos")
    return errors


def validate_invoice(emisor, cliente, factura) -> list[str]:
    errors = validate_party(emisor.rfc, emisor.regimen_fiscal, emisor.codigo_postal, "Emisor")
    if is_generic_rfc(emisor.rfc):
        errors.append("Emisor: no se puede emitir con un RFC genérico")

    receptor_rfc = normalize_rfc(cliente.rfc)
    if receptor_rfc == cat.RFC_PUBLICO_GENERAL:
        if cliente.regimen_fiscal != "616":
            errors.append("Público en general: el régimen del receptor debe ser 616")
        if factura.uso_cfdi != "S01":
            errors.append("Público en general: el uso de CFDI debe ser S01")
        if cliente.codigo_postal != emisor.codigo_postal:
            errors.append("Público en general: el CP del receptor debe ser igual al lugar de expedición")
    elif receptor_rfc == cat.RFC_EXTRANJERO:
        if cliente.regimen_fiscal != "616" or factura.uso_cfdi != "S01":
            errors.append("Receptor extranjero: régimen 616 y uso S01")
    else:
        errors += validate_party(cliente.rfc, cliente.regimen_fiscal, cliente.codigo_postal, "Receptor")
        tipo = _tipo(cliente.rfc)
        uso = cat.USOS_CFDI.get(factura.uso_cfdi)
        if uso is None:
            errors.append(f"Uso de CFDI '{factura.uso_cfdi}' no existe en el catálogo")
        elif tipo and not uso[tipo]:
            errors.append(f"El uso de CFDI {factura.uso_cfdi} no aplica para persona {tipo}")

    if factura.tipo_comprobante not in cat.TIPOS_COMPROBANTE:
        errors.append("Tipo de comprobante inválido")
    if factura.metodo_pago not in cat.METODOS_PAGO:
        errors.append("Método de pago inválido")
    if factura.forma_pago not in cat.FORMAS_PAGO:
        errors.append("Forma de pago inválida")
    if factura.metodo_pago == "PPD" and factura.forma_pago != "99":
        errors.append("Con método PPD la forma de pago debe ser 99 (Por definir)")
    if factura.metodo_pago == "PUE" and factura.forma_pago == "99":
        errors.append("Con método PUE la forma de pago no puede ser 99 (Por definir)")

    if factura.moneda not in cat.MONEDAS:
        errors.append(f"Moneda '{factura.moneda}' no soportada")
    elif factura.moneda != "MXN" and not (factura.tipo_cambio and Decimal(str(factura.tipo_cambio)) > 0):
        errors.append("Para monedas distintas a MXN se requiere tipo de cambio")
    if factura.exportacion not in cat.EXPORTACION:
        errors.append("Clave de exportación inválida")
    return errors
