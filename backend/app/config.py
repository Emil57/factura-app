"""Settings read from environment variables (see backend/.env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "si", "sí")


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL", "postgresql+psycopg://factura:factura@localhost:5432/factura"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "cambia-este-secreto"))
    jwt_minutes: int = field(default_factory=lambda: int(os.getenv("JWT_MINUTES", "480")))
    cors_origins: list[str] = field(default_factory=lambda: [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()])

    admin_email: str = field(default_factory=lambda: os.getenv("ADMIN_EMAIL", "admin@factura.local"))
    admin_password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", "admin1234"))

    pac_provider: str = field(default_factory=lambda: os.getenv("PAC_PROVIDER", "mock"))  # mock | facturama
    facturama_user: str = field(default_factory=lambda: os.getenv("FACTURAMA_USER", ""))
    facturama_password: str = field(default_factory=lambda: os.getenv("FACTURAMA_PASSWORD", ""))
    facturama_sandbox: bool = field(default_factory=lambda: _bool("FACTURAMA_SANDBOX", True))


settings = Settings()
