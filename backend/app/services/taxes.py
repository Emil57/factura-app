"""Pure tax engine for CFDI 4.0 concepts (no DB / framework imports, easy to test).

Rules implemented:
* Importe = Cantidad x ValorUnitario; Base = Importe - Descuento.
* Taxes are only computed when ObjetoImp == "02".
* IEPS trasladado is part of the IVA base (Ley del IVA, art. 18).
* ISR / IVA withholdings use the Base without IVA.
* Every amount is rounded to 2 decimals (MXN) with ROUND_HALF_UP; invoice totals are
  sums of the already-rounded concept amounts, as the SAT validator expects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

TWO = Decimal("0.01")
SIX = Decimal("0.000001")

# 2/3 of the 16% IVA (RLIVA art. 3): SAT accepts the 6-decimal rate.
RET_IVA_DOS_TERCIOS = Decimal("0.106667")


def money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(TWO, rounding=ROUND_HALF_UP)


def rate(value: Decimal | str | float | None) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value)).quantize(SIX, rounding=ROUND_HALF_UP)


@dataclass
class LineInput:
    cantidad: Decimal
    precio_unitario: Decimal
    descuento: Decimal = Decimal("0")
    objeto_imp: str = "02"
    iva_tasa: str | None = "0.160000"  # "exento" or a rate string or None
    ieps_tasa: str | None = None
    ret_isr_tasa: str | None = None
    ret_iva_tasa: str | None = None


@dataclass
class TaxLine:
    impuesto: str  # "IVA" | "IEPS" | "ISR"
    tipo: str  # "traslado" | "retencion"
    tipo_factor: str  # "Tasa" | "Exento"
    base: Decimal
    tasa: Decimal | None
    importe: Decimal

    def as_dict(self) -> dict:
        return {
            "impuesto": self.impuesto,
            "tipo": self.tipo,
            "tipo_factor": self.tipo_factor,
            "base": str(self.base),
            "tasa": None if self.tasa is None else str(self.tasa),
            "importe": str(self.importe),
        }


@dataclass
class LineResult:
    importe: Decimal
    descuento: Decimal
    base: Decimal
    impuestos: list[TaxLine] = field(default_factory=list)

    @property
    def traslados(self) -> Decimal:
        return sum((t.importe for t in self.impuestos if t.tipo == "traslado"), Decimal("0.00"))

    @property
    def retenciones(self) -> Decimal:
        return sum((t.importe for t in self.impuestos if t.tipo == "retencion"), Decimal("0.00"))

    @property
    def total(self) -> Decimal:
        return self.base + self.traslados - self.retenciones


@dataclass
class Totals:
    subtotal: Decimal
    descuento: Decimal
    traslados: Decimal
    retenciones: Decimal
    total: Decimal
    lines: list[LineResult]

    def summary(self) -> dict:
        def group(tipo: str) -> list[dict]:
            acc: dict[tuple, dict] = {}
            for line in self.lines:
                for t in line.impuestos:
                    if t.tipo != tipo:
                        continue
                    key = (t.impuesto, t.tipo_factor, t.tasa)
                    g = acc.setdefault(key, {"impuesto": t.impuesto, "tipo_factor": t.tipo_factor,
                                             "tasa": None if t.tasa is None else str(t.tasa),
                                             "base": Decimal("0.00"), "importe": Decimal("0.00")})
                    g["base"] += t.base
                    g["importe"] += t.importe
            return [{**g, "base": str(g["base"]), "importe": str(g["importe"])} for g in acc.values()]

        return {
            "subtotal": str(self.subtotal),
            "descuento": str(self.descuento),
            "total_traslados": str(self.traslados),
            "total_retenciones": str(self.retenciones),
            "total": str(self.total),
            "traslados": group("traslado"),
            "retenciones": group("retencion"),
            "conceptos": [
                {
                    "importe": str(l.importe),
                    "descuento": str(l.descuento),
                    "base": str(l.base),
                    "impuestos": [t.as_dict() for t in l.impuestos],
                    "total": str(l.total),
                }
                for l in self.lines
            ],
        }


def compute_line(line: LineInput) -> LineResult:
    cantidad = Decimal(str(line.cantidad))
    precio = Decimal(str(line.precio_unitario))
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a cero")
    if precio < 0:
        raise ValueError("El valor unitario no puede ser negativo")

    importe = money(cantidad * precio)
    descuento = money(line.descuento or 0)
    if descuento < 0 or descuento > importe:
        raise ValueError("El descuento debe estar entre 0 y el importe del concepto")
    base = importe - descuento
    result = LineResult(importe=importe, descuento=descuento, base=base)

    if line.objeto_imp != "02":
        return result

    ieps_importe = Decimal("0.00")
    ieps = rate(line.ieps_tasa)
    if ieps is not None:
        ieps_importe = money(base * ieps)
        result.impuestos.append(TaxLine("IEPS", "traslado", "Tasa", base, ieps, ieps_importe))

    iva_base = base + ieps_importe
    if line.iva_tasa == "exento":
        result.impuestos.append(TaxLine("IVA", "traslado", "Exento", iva_base, None, Decimal("0.00")))
    else:
        iva = rate(line.iva_tasa)
        if iva is not None:
            result.impuestos.append(TaxLine("IVA", "traslado", "Tasa", iva_base, iva, money(iva_base * iva)))

    ret_isr = rate(line.ret_isr_tasa)
    if ret_isr:
        result.impuestos.append(TaxLine("ISR", "retencion", "Tasa", base, ret_isr, money(base * ret_isr)))
    ret_iva = rate(line.ret_iva_tasa)
    if ret_iva:
        result.impuestos.append(TaxLine("IVA", "retencion", "Tasa", base, ret_iva, money(base * ret_iva)))

    if not result.impuestos:
        raise ValueError("Un concepto con ObjetoImp 02 debe llevar al menos un impuesto")
    return result


def compute_invoice(lines: list[LineInput]) -> Totals:
    if not lines:
        raise ValueError("La factura debe tener al menos un concepto")
    results = [compute_line(l) for l in lines]
    subtotal = sum((r.importe for r in results), Decimal("0.00"))
    descuento = sum((r.descuento for r in results), Decimal("0.00"))
    traslados = sum((r.traslados for r in results), Decimal("0.00"))
    retenciones = sum((r.retenciones for r in results), Decimal("0.00"))
    total = subtotal - descuento + traslados - retenciones
    return Totals(subtotal, descuento, traslados, retenciones, total, results)


def suggest_withholdings(emisor_regimen: str, emisor_tipo: str, receptor_tipo: str) -> dict:
    """Default withholdings when an issuer bills a persona moral.

    These are the common cases; the user can always edit them per concept and should
    confirm with their accountant for special activities (fletes, outsourcing, etc.).
    """
    none = {"ret_isr_tasa": None, "ret_iva_tasa": None, "motivo": None}
    if emisor_tipo != "fisica" or receptor_tipo != "moral":
        return none
    if emisor_regimen == "612":
        return {"ret_isr_tasa": "0.100000", "ret_iva_tasa": str(RET_IVA_DOS_TERCIOS),
                "motivo": "Honorarios de persona física a persona moral: ISR 10% y 2/3 de IVA"}
    if emisor_regimen == "606":
        return {"ret_isr_tasa": "0.100000", "ret_iva_tasa": str(RET_IVA_DOS_TERCIOS),
                "motivo": "Arrendamiento de persona física a persona moral: ISR 10% y 2/3 de IVA"}
    if emisor_regimen == "626":
        return {"ret_isr_tasa": "0.012500", "ret_iva_tasa": str(RET_IVA_DOS_TERCIOS),
                "motivo": "RESICO persona física a persona moral: ISR 1.25% y 2/3 de IVA"}
    return none
