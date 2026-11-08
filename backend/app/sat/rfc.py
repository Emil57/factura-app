"""RFC helpers: format validation and taxpayer type detection."""

from __future__ import annotations

import re

from .catalogs import RFC_EXTRANJERO, RFC_PUBLICO_GENERAL

# Persona moral: 3 letters + date + 3 homoclave. Persona física: 4 letters + date + 3.
_RFC_RE = re.compile(r"^([A-ZÑ&]{3,4})(\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])([A-Z\d]{2}[A\d])$")


def normalize_rfc(rfc: str) -> str:
    return rfc.strip().upper().replace(" ", "").replace("-", "")


def is_valid_rfc(rfc: str) -> bool:
    return bool(_RFC_RE.match(normalize_rfc(rfc)))


def tipo_persona(rfc: str) -> str:
    """Return 'fisica' (13 chars) or 'moral' (12 chars)."""
    rfc = normalize_rfc(rfc)
    if not is_valid_rfc(rfc):
        raise ValueError(f"RFC con formato inválido: {rfc}")
    return "moral" if len(rfc) == 12 else "fisica"


def is_generic_rfc(rfc: str) -> bool:
    return normalize_rfc(rfc) in (RFC_PUBLICO_GENERAL, RFC_EXTRANJERO)
