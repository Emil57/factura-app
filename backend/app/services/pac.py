"""PAC (Proveedor Autorizado de Certificación) clients.

`FacturamaPAC` talks to Facturama's API Multiemisor so the app can stamp for any RFC
whose CSD was uploaded. `MockPAC` lets you develop without credentials: it returns a
random UUID and an unsigned XML clearly marked as having no fiscal validity.
"""

from __future__ import annotations

import base64
import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime, timezone

from ..config import settings


class PACError(Exception):
    def __init__(self, message: str, detail: object | None = None):
        super().__init__(message)
        self.detail = detail


@dataclass
class StampResult:
    pac_id: str
    uuid: str
    fecha_timbrado: datetime
    xml: str


@dataclass
class CancelResult:
    status: str  # "canceled" | "pending" | "active"
    message: str
    acuse_xml: str | None = None


class BasePAC:
    name = "base"

    def upload_csd(self, rfc: str, cer_b64: str, key_b64: str, password: str) -> None:
        raise NotImplementedError

    def stamp(self, payload: dict, preview_xml: str) -> StampResult:
        raise NotImplementedError

    def download(self, pac_id: str, fmt: str) -> bytes:
        raise NotImplementedError

    def cancel(self, pac_id: str, motivo: str, uuid_sustitucion: str | None) -> CancelResult:
        raise NotImplementedError


class MockPAC(BasePAC):
    name = "mock"

    def upload_csd(self, rfc, cer_b64, key_b64, password):
        return None

    def stamp(self, payload, preview_xml):
        new_uuid = str(uuidlib.uuid4()).upper()
        xml = preview_xml.replace("__UUID__", new_uuid)
        return StampResult(pac_id=f"mock-{new_uuid}", uuid=new_uuid,
                           fecha_timbrado=datetime.now(timezone.utc), xml=xml)

    def download(self, pac_id, fmt):
        raise PACError("El PAC simulado no genera PDF; descarga el XML o configura Facturama")

    def cancel(self, pac_id, motivo, uuid_sustitucion):
        return CancelResult(status="canceled", message="Cancelado (simulado)")


class FacturamaPAC(BasePAC):
    name = "facturama"

    def __init__(self, user: str, password: str, sandbox: bool = True, timeout: float = 60.0):
        import httpx  # imported lazily so pure modules/tests don't need it

        base = "https://apisandbox.facturama.mx" if sandbox else "https://api.facturama.mx"
        self._client = httpx.Client(base_url=base, auth=(user, password), timeout=timeout)

    def _check(self, resp):
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except ValueError:
                detail = resp.text
            message = detail.get("Message") if isinstance(detail, dict) else None
            raise PACError(message or f"Facturama respondió {resp.status_code}", detail)
        return resp

    def upload_csd(self, rfc, cer_b64, key_b64, password):
        body = {"Rfc": rfc, "Certificate": cer_b64, "PrivateKey": key_b64, "PrivateKeyPassword": password}
        resp = self._client.post("/api-lite/csds", json=body)
        if resp.status_code == 400 and "existe" in resp.text.lower():
            resp = self._client.put(f"/api-lite/csds/{rfc}", json=body)
        self._check(resp)

    def stamp(self, payload, preview_xml):
        data = self._check(self._client.post("/api-lite/4/cfdis", json=payload)).json()
        stamp = data.get("TaxStamp") or data.get("Complement", {}).get("TaxStamp") or {}
        xml = base64.b64decode(data["XmlBase64"]).decode("utf-8") if data.get("XmlBase64") else ""
        fecha = stamp.get("Date")
        return StampResult(
            pac_id=data["Id"],
            uuid=stamp.get("Uuid", ""),
            fecha_timbrado=datetime.fromisoformat(fecha) if fecha else datetime.now(timezone.utc),
            xml=xml,
        )

    def download(self, pac_id, fmt):
        # Multiemisor documents are of type "issuedLite"; response is {"Content": base64, ...}.
        data = self._check(self._client.get(f"/cfdi/{fmt}/issuedLite/{pac_id}")).json()
        return base64.b64decode(data["Content"])

    def cancel(self, pac_id, motivo, uuid_sustitucion):
        params = {"motive": motivo}
        if motivo == "01" and uuid_sustitucion:
            params["uuidReplacement"] = uuid_sustitucion
        data = self._check(self._client.delete(f"/api-lite/cfdis/{pac_id}", params=params)).json()
        acuse = data.get("AcuseXmlBase64")
        return CancelResult(
            status=data.get("Status", "pending"),
            message=data.get("Message", ""),
            acuse_xml=base64.b64decode(acuse).decode("utf-8") if acuse else None,
        )


def get_pac() -> BasePAC:
    if settings.pac_provider == "facturama":
        if not settings.facturama_user or not settings.facturama_password:
            raise PACError("Configura FACTURAMA_USER y FACTURAMA_PASSWORD")
        return FacturamaPAC(settings.facturama_user, settings.facturama_password, settings.facturama_sandbox)
    return MockPAC()
