from fastapi_app.models.rol_permiso import Rol
from fastapi_app.models.cartera import Cartera

from typing import List
from fastapi_app.models.usuario import Usuario
from fastapi_app.schemas.usuario import Usuario as UsuarioSchema


from fastapi import APIRouter, Body, HTTPException, Depends
from sqlalchemy.orm import Session
from fastapi_app.database import get_db
from fastapi_app.models.usuario import Usuario

router = APIRouter(prefix="/usuario", tags=["Usuario"])

@router.post("/login")
def login_usuario(
    data: dict = Body(..., example={"nombre": "admin", "clave": "admin"}),
    db: Session = Depends(get_db)
):
    nombre = data.get("nombre")
    clave = data.get("clave")
    user = db.query(Usuario).filter(Usuario.nombre == nombre).first()
    if user and hasattr(user, "clave") and user.clave == clave:
        # Get direct permissions
        direct_perms = set(p.descripcion for p in getattr(user, "permisos", []) if hasattr(p, "descripcion"))
        # Get permissions from roles
        role_perms = set()
        for rol in getattr(user, "roles", []):
            for p in getattr(rol, "permisos", []):
                if hasattr(p, "descripcion"):
                    role_perms.add(p.descripcion)
        permisos = list(direct_perms | role_perms)
        return {
            "usuario": {
                "idUsuario": user.id,
                "permisos": permisos
            }
        }
    raise HTTPException(status_code=401, detail="Credenciales inválidas")


