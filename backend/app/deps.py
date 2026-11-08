from __future__ import annotations

import json
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import LogActividad, Usuario
from .security import decode_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> Usuario:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o expirada")
    user = db.get(Usuario, int(payload["sub"]))
    if not user or not user.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inactivo")
    return user


def require_roles(*roles: str) -> Callable:
    def checker(user: Usuario = Depends(current_user)) -> Usuario:
        if "Admin" in user.role_names or any(r in user.role_names for r in roles):
            return user
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para esta acción")
    return checker


def audit(db: Session, request: Request | None, user: Usuario | None, accion: str, tabla: str,
          registro_id: int | None, antes: dict | None = None, despues: dict | None = None) -> None:
    db.add(LogActividad(
        usuario_id=user.id if user else None,
        accion=accion,
        tabla_afectada=tabla,
        registro_id=registro_id,
        valor_anterior=json.dumps(antes, default=str, ensure_ascii=False) if antes else None,
        valor_nuevo=json.dumps(despues, default=str, ensure_ascii=False) if despues else None,
        direccion_ip=request.client.host if request and request.client else None,
    ))
