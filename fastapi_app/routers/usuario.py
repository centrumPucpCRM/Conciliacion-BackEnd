
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
    import bcrypt
    user = db.query(Usuario).filter(Usuario.nombre == nombre).first()
    if not user or not bcrypt.checkpw(clave.encode('utf-8'), user.clave.encode('utf-8')):
        permisos = [p.descripcion for p in getattr(user, "permisos", []) if hasattr(p, "descripcion")]
        carteras = [c.nombre for c in getattr(user, "carteras", []) if hasattr(c, "nombre")]
        return {
            "usuario": {
                "idUsuario": user.id,
                "permisos": permisos,
                "carteras": carteras
            }
        }
    raise HTTPException(status_code=401, detail="Credenciales inválidas")
