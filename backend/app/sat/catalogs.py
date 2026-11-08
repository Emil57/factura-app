"""SAT catalogs for CFDI 4.0 (subset needed for issuing ingreso/egreso invoices).

Keys follow Anexo 20 catalogs (c_RegimenFiscal, c_UsoCFDI, c_FormaPago, ...).
`fisica` / `moral` flags say which taxpayer type may use each entry.
"""

from __future__ import annotations

REGIMENES_FISCALES: dict[str, dict] = {
    "601": {"descripcion": "General de Ley Personas Morales", "fisica": False, "moral": True},
    "603": {"descripcion": "Personas Morales con Fines no Lucrativos", "fisica": False, "moral": True},
    "605": {"descripcion": "Sueldos y Salarios e Ingresos Asimilados a Salarios", "fisica": True, "moral": False},
    "606": {"descripcion": "Arrendamiento", "fisica": True, "moral": False},
    "607": {"descripcion": "Régimen de Enajenación o Adquisición de Bienes", "fisica": True, "moral": False},
    "608": {"descripcion": "Demás ingresos", "fisica": True, "moral": False},
    "610": {"descripcion": "Residentes en el Extranjero sin Establecimiento Permanente en México", "fisica": True, "moral": True},
    "611": {"descripcion": "Ingresos por Dividendos (socios y accionistas)", "fisica": True, "moral": False},
    "612": {"descripcion": "Personas Físicas con Actividades Empresariales y Profesionales", "fisica": True, "moral": False},
    "614": {"descripcion": "Ingresos por intereses", "fisica": True, "moral": False},
    "615": {"descripcion": "Régimen de los ingresos por obtención de premios", "fisica": True, "moral": False},
    "616": {"descripcion": "Sin obligaciones fiscales", "fisica": True, "moral": False},
    "620": {"descripcion": "Sociedades Cooperativas de Producción que optan por diferir sus ingresos", "fisica": False, "moral": True},
    "621": {"descripcion": "Incorporación Fiscal", "fisica": True, "moral": False},
    "622": {"descripcion": "Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras", "fisica": False, "moral": True},
    "623": {"descripcion": "Opcional para Grupos de Sociedades", "fisica": False, "moral": True},
    "624": {"descripcion": "Coordinados", "fisica": False, "moral": True},
    "625": {"descripcion": "Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas", "fisica": True, "moral": False},
    "626": {"descripcion": "Régimen Simplificado de Confianza", "fisica": True, "moral": True},
}

USOS_CFDI: dict[str, dict] = {
    "G01": {"descripcion": "Adquisición de mercancías", "fisica": True, "moral": True},
    "G02": {"descripcion": "Devoluciones, descuentos o bonificaciones", "fisica": True, "moral": True},
    "G03": {"descripcion": "Gastos en general", "fisica": True, "moral": True},
    "I01": {"descripcion": "Construcciones", "fisica": True, "moral": True},
    "I02": {"descripcion": "Mobiliario y equipo de oficina por inversiones", "fisica": True, "moral": True},
    "I03": {"descripcion": "Equipo de transporte", "fisica": True, "moral": True},
    "I04": {"descripcion": "Equipo de computo y accesorios", "fisica": True, "moral": True},
    "I05": {"descripcion": "Dados, troqueles, moldes, matrices y herramental", "fisica": True, "moral": True},
    "I06": {"descripcion": "Comunicaciones telefónicas", "fisica": True, "moral": True},
    "I07": {"descripcion": "Comunicaciones satelitales", "fisica": True, "moral": True},
    "I08": {"descripcion": "Otra maquinaria y equipo", "fisica": True, "moral": True},
    "D01": {"descripcion": "Honorarios médicos, dentales y gastos hospitalarios", "fisica": True, "moral": False},
    "D02": {"descripcion": "Gastos médicos por incapacidad o discapacidad", "fisica": True, "moral": False},
    "D03": {"descripcion": "Gastos funerales", "fisica": True, "moral": False},
    "D04": {"descripcion": "Donativos", "fisica": True, "moral": False},
    "D05": {"descripcion": "Intereses reales pagados por créditos hipotecarios (casa habitación)", "fisica": True, "moral": False},
    "D06": {"descripcion": "Aportaciones voluntarias al SAR", "fisica": True, "moral": False},
    "D07": {"descripcion": "Primas por seguros de gastos médicos", "fisica": True, "moral": False},
    "D08": {"descripcion": "Gastos de transportación escolar obligatoria", "fisica": True, "moral": False},
    "D09": {"descripcion": "Depósitos en cuentas para el ahorro, primas de planes de pensiones", "fisica": True, "moral": False},
    "D10": {"descripcion": "Pagos por servicios educativos (colegiaturas)", "fisica": True, "moral": False},
    "S01": {"descripcion": "Sin efectos fiscales", "fisica": True, "moral": True},
}

FORMAS_PAGO: dict[str, str] = {
    "01": "Efectivo",
    "02": "Cheque nominativo",
    "03": "Transferencia electrónica de fondos",
    "04": "Tarjeta de crédito",
    "05": "Monedero electrónico",
    "06": "Dinero electrónico",
    "08": "Vales de despensa",
    "12": "Dación en pago",
    "13": "Pago por subrogación",
    "14": "Pago por consignación",
    "15": "Condonación",
    "17": "Compensación",
    "23": "Novación",
    "24": "Confusión",
    "25": "Remisión de deuda",
    "26": "Prescripción o caducidad",
    "27": "A satisfacción del acreedor",
    "28": "Tarjeta de débito",
    "29": "Tarjeta de servicios",
    "30": "Aplicación de anticipos",
    "31": "Intermediario pagos",
    "99": "Por definir",
}

METODOS_PAGO: dict[str, str] = {
    "PUE": "Pago en una sola exhibición",
    "PPD": "Pago en parcialidades o diferido",
}

OBJETOS_IMPUESTO: dict[str, str] = {
    "01": "No objeto de impuesto",
    "02": "Sí objeto de impuesto",
    "03": "Sí objeto del impuesto y no obligado al desglose",
    "04": "Sí objeto del impuesto y no causa impuesto",
}

TIPOS_COMPROBANTE: dict[str, str] = {
    "I": "Ingreso",
    "E": "Egreso",
}

MONEDAS: dict[str, str] = {
    "MXN": "Peso Mexicano",
    "USD": "Dólar americano",
    "EUR": "Euro",
}

EXPORTACION: dict[str, str] = {
    "01": "No aplica",
    "02": "Definitiva con clave A1",
    "03": "Temporal",
}

MOTIVOS_CANCELACION: dict[str, str] = {
    "01": "Comprobante emitido con errores con relación",
    "02": "Comprobante emitido con errores sin relación",
    "03": "No se llevó a cabo la operación",
    "04": "Operación nominativa relacionada en una factura global",
}

# Trasladados: tasas válidas que la UI ofrece por concepto.
TASAS_IVA = ["0.160000", "0.080000", "0.000000", "exento"]
TASAS_IEPS = ["0.000000", "0.030000", "0.060000", "0.070000", "0.080000", "0.090000",
              "0.250000", "0.265000", "0.300000", "0.500000", "0.530000", "1.600000"]

RFC_PUBLICO_GENERAL = "XAXX010101000"
RFC_EXTRANJERO = "XEXX010101000"


def all_catalogs() -> dict:
    return {
        "regimenes_fiscales": REGIMENES_FISCALES,
        "usos_cfdi": USOS_CFDI,
        "formas_pago": FORMAS_PAGO,
        "metodos_pago": METODOS_PAGO,
        "objetos_impuesto": OBJETOS_IMPUESTO,
        "tipos_comprobante": TIPOS_COMPROBANTE,
        "monedas": MONEDAS,
        "exportacion": EXPORTACION,
        "motivos_cancelacion": MOTIVOS_CANCELACION,
        "tasas_iva": TASAS_IVA,
        "tasas_ieps": TASAS_IEPS,
    }
