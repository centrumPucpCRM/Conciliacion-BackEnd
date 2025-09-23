
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
    if not nombre or not clave:
        raise HTTPException(status_code=400, detail="Nombre y clave requeridos")
    user = db.query(Usuario).filter(Usuario.nombre == nombre).first()
    if user and hasattr(user, "clave") and user.clave == clave:
        # Permisos directos
        permisos_directos = {p.descripcion for p in getattr(user, "permisos", []) if hasattr(p, "descripcion")}
        # Permisos por roles
        permisos_roles = set()
        for rol in getattr(user, "roles", []):
            for p in getattr(rol, "permisos", []):
                if hasattr(p, "descripcion"):
                    permisos_roles.add(p.descripcion)
        permisos = list(permisos_directos.union(permisos_roles))
        carteras = [c.nombre for c in getattr(user, "carteras", []) if hasattr(c, "nombre")]
        return {
            "usuario": {
                "idUsuario": user.id,
                "permisos": permisos,
                "carteras": carteras
            }
        }
    raise HTTPException(status_code=401, detail="Credenciales inválidas")
