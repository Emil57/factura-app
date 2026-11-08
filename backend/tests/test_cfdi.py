"""Tests for the pure CFDI logic (tax engine, validations, payload/XML builder).

Run: cd backend && python -m pytest
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal as D
from types import SimpleNamespace as NS

import pytest

from app.sat.rfc import is_valid_rfc, tipo_persona
from app.services.cfdi_builder import CFDI_NS, facturama_payload, preview_xml
from app.services.taxes import LineInput, compute_invoice, compute_line, suggest_withholdings
from app.services.validation import validate_invoice

# Facturama sandbox test RFCs
EMISOR_MORAL = NS(rfc="EKU9003173C9", razon_social="ESCUELA KEMPER URGATE", regimen_fiscal="601",
                  codigo_postal="42501")
EMISOR_FISICA = NS(rfc="CACX7605101P8", razon_social="XOCHILT CASAS CHAVEZ", regimen_fiscal="612",
                   codigo_postal="36257")
CLIENTE_MORAL = NS(rfc="URE180429TM6", razon_social="UNIVERSIDAD ROBOTICA ESPAÑOLA", regimen_fiscal="601",
                   codigo_postal="86991")
CLIENTE_FISICA = NS(rfc="FUNK671228PH6", razon_social="KARLA FUENTE NOLASCO", regimen_fiscal="605",
                    codigo_postal="01160")


def line(**kw):
    defaults = dict(producto_id=None, codigo=None, clave_prod_serv="80111600", clave_unidad="E48",
                    unidad="Servicio", descripcion="Servicio", cantidad=D("1"), precio_unitario=D("1000"),
                    descuento=D("0"), objeto_imp="02", iva_tasa="0.160000", ieps_tasa=None,
                    ret_isr_tasa=None, ret_iva_tasa=None)
    defaults.update(kw)
    return NS(**defaults)


def factura(detalles, **kw):
    defaults = dict(tipo_comprobante="I", serie="A", folio=1, fecha_emision=datetime(2026, 11, 8, 12, 0, 0),
                    uso_cfdi="G03", forma_pago="03", metodo_pago="PUE", moneda="MXN", tipo_cambio=None,
                    exportacion="01", condiciones_pago=None, observaciones=None, cfdi_relacionado_uuid=None,
                    tipo_relacion=None, detalles=detalles)
    defaults.update(kw)
    return NS(**defaults)


# ---------------- RFC ----------------
def test_rfc_types():
    assert tipo_persona("EKU9003173C9") == "moral"
    assert tipo_persona("cacx7605101p8") == "fisica"
    assert not is_valid_rfc("ABC123")
    assert not is_valid_rfc("EKU9013173C9")  # month 13


# ---------------- Taxes ----------------
def test_iva_16():
    t = compute_invoice([LineInput(D("2"), D("50"))])
    assert (t.subtotal, t.traslados, t.total) == (D("100.00"), D("16.00"), D("116.00"))


def test_discount_reduces_base():
    r = compute_line(LineInput(D("1"), D("1000"), descuento=D("100")))
    assert r.base == D("900.00")
    assert r.traslados == D("144.00")
    assert r.total == D("1044.00")


def test_honorarios_persona_fisica_to_moral():
    sug = suggest_withholdings("612", "fisica", "moral")
    t = compute_invoice([LineInput(D("1"), D("10000"), ret_isr_tasa=sug["ret_isr_tasa"],
                                   ret_iva_tasa=sug["ret_iva_tasa"])])
    assert t.traslados == D("1600.00")
    # ISR 10% = 1000, IVA 2/3 = 1066.67
    assert t.retenciones == D("2066.67")
    assert t.total == D("9533.33")


def test_resico_withholding():
    sug = suggest_withholdings("626", "fisica", "moral")
    assert sug["ret_isr_tasa"] == "0.012500"
    t = compute_invoice([LineInput(D("1"), D("1000"), ret_isr_tasa=sug["ret_isr_tasa"],
                                   ret_iva_tasa=sug["ret_iva_tasa"])])
    assert t.retenciones == D("12.50") + D("106.67")


def test_no_withholding_between_morales_or_to_fisica():
    assert suggest_withholdings("601", "moral", "moral")["ret_isr_tasa"] is None
    assert suggest_withholdings("612", "fisica", "fisica")["ret_isr_tasa"] is None


def test_ieps_is_part_of_iva_base():
    r = compute_line(LineInput(D("1"), D("100"), ieps_tasa="0.080000"))
    ieps, iva = r.impuestos
    assert (ieps.impuesto, ieps.importe) == ("IEPS", D("8.00"))
    assert (iva.base, iva.importe) == (D("108.00"), D("17.28"))


def test_exento_and_no_objeto():
    r = compute_line(LineInput(D("1"), D("100"), iva_tasa="exento"))
    assert r.impuestos[0].tipo_factor == "Exento" and r.total == D("100.00")
    r = compute_line(LineInput(D("1"), D("100"), objeto_imp="01"))
    assert r.impuestos == [] and r.total == D("100.00")


def test_totals_are_sum_of_rounded_lines():
    # 3 x 33.333 -> 99.999 -> 100.00 ; IVA 16.00
    t = compute_invoice([LineInput(D("3"), D("33.333")), LineInput(D("1"), D("0.05"))])
    assert t.subtotal == D("100.05")
    assert t.traslados == D("16.00") + D("0.01")
    assert t.total == t.subtotal + t.traslados


def test_invalid_lines():
    with pytest.raises(ValueError):
        compute_line(LineInput(D("0"), D("10")))
    with pytest.raises(ValueError):
        compute_line(LineInput(D("1"), D("10"), descuento=D("11")))
    with pytest.raises(ValueError):
        compute_line(LineInput(D("1"), D("10"), iva_tasa=None))


# ---------------- Validation ----------------
def test_valid_invoice_has_no_errors():
    assert validate_invoice(EMISOR_MORAL, CLIENTE_MORAL, factura([line()])) == []


def test_uso_cfdi_d01_not_for_moral():
    errs = validate_invoice(EMISOR_MORAL, CLIENTE_MORAL, factura([line()], uso_cfdi="D01"))
    assert any("D01" in e for e in errs)


def test_regimen_mismatch_with_persona_type():
    bad = NS(**{**vars(CLIENTE_FISICA), "regimen_fiscal": "601"})
    errs = validate_invoice(EMISOR_MORAL, bad, factura([line()]))
    assert any("601" in e for e in errs)


def test_ppd_requires_forma_99():
    errs = validate_invoice(EMISOR_MORAL, CLIENTE_MORAL, factura([line()], metodo_pago="PPD", forma_pago="03"))
    assert any("PPD" in e for e in errs)
    assert validate_invoice(EMISOR_MORAL, CLIENTE_MORAL, factura([line()], metodo_pago="PPD", forma_pago="99")) == []


def test_foreign_currency_needs_exchange_rate():
    errs = validate_invoice(EMISOR_MORAL, CLIENTE_MORAL, factura([line()], moneda="USD"))
    assert any("tipo de cambio" in e for e in errs)


def test_publico_en_general_rules():
    publico = NS(rfc="XAXX010101000", razon_social="PUBLICO EN GENERAL", regimen_fiscal="616",
                 codigo_postal=EMISOR_MORAL.codigo_postal)
    assert validate_invoice(EMISOR_MORAL, publico, factura([line()], uso_cfdi="S01")) == []
    errs = validate_invoice(EMISOR_MORAL, publico, factura([line()], uso_cfdi="G03"))
    assert any("S01" in e for e in errs)


# ---------------- Builder ----------------
def test_facturama_payload_with_withholdings():
    f = factura([line(precio_unitario=D("10000"), ret_isr_tasa="0.100000", ret_iva_tasa="0.106667")])
    p = facturama_payload(f, EMISOR_FISICA, CLIENTE_MORAL)
    assert p["Issuer"] == {"Rfc": "CACX7605101P8", "Name": "XOCHILT CASAS CHAVEZ", "FiscalRegime": "612"}
    assert p["Receiver"]["TaxZipCode"] == "86991"
    assert p["ExpeditionPlace"] == "36257"
    item = p["Items"][0]
    assert item["Total"] == 9533.33
    names = [(t["Name"], t["IsRetention"]) for t in item["Taxes"]]
    assert names == [("IVA", False), ("ISR", True), ("IVA", True)]
    assert "GlobalInformation" not in p


def test_payload_publico_general_has_global_information():
    publico = NS(rfc="XAXX010101000", razon_social="PUBLICO EN GENERAL", regimen_fiscal="616",
                 codigo_postal="42501")
    p = facturama_payload(factura([line()], uso_cfdi="S01"), EMISOR_MORAL, publico)
    assert p["GlobalInformation"] == {"Periodicity": "04", "Months": "11", "Year": "2026"}


def test_preview_xml_is_well_formed():
    f = factura([line(ret_isr_tasa="0.100000", ret_iva_tasa="0.106667"), line(objeto_imp="01")])
    xml = preview_xml(f, EMISOR_FISICA, CLIENTE_MORAL, uuid="ABC")
    root = ET.fromstring(xml.split("\n", 1)[1])
    assert root.attrib["Total"] == "1953.33"
    assert root.find(f"{{{CFDI_NS}}}Impuestos").attrib == {
        "TotalImpuestosRetenidos": "206.67", "TotalImpuestosTrasladados": "160.00"}
    assert len(root.find(f"{{{CFDI_NS}}}Conceptos")) == 2
