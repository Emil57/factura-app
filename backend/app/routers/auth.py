from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user, require_roles
from ..models import Rol, Usuario
from ..schemas import TokenOut, UsuarioIn, UsuarioOut
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/token", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(Usuario).where(Usuario.email == form.username.strip().lower()))
    if not user or not user.activo or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos")
    return TokenOut(access_token=create_token(user.id, user.role_names))


@router.get("/me", response_model=UsuarioOut)
def me(user: Usuario = Depends(current_user)):
    return user


@router.get("/usuarios", response_model=list[UsuarioOut], dependencies=[Depends(require_roles())])
def list_users(db: Session = Depends(get_db)):
    return db.scalars(select(Usuario).order_by(Usuario.id)).all()


@router.post("/usuarios", response_model=UsuarioOut, status_code=201, dependencies=[Depends(require_roles())])
def create_user(data: UsuarioIn, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    if db.scalar(select(Usuario).where(Usuario.email == email)):
        raise HTTPException(409, "Ya existe un usuario con ese correo")
    roles = db.scalars(select(Rol).where(Rol.nombre.in_(data.roles))).all()
    if len(roles) != len(set(data.roles)):
        raise HTTPException(422, "Rol inválido; usa Admin, Usuario o Contador")
    user = Usuario(email=email, nombre=data.nombre, password_hash=hash_password(data.password), roles=list(roles))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
