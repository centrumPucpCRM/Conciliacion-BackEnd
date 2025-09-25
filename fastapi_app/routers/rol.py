from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi_app.database import get_db
from fastapi_app.models.rol_permiso import Rol

router = APIRouter(prefix="/rol", tags=["Rol"])

@router.get("/roles-usuarios-carteras", response_model=list)
def listar_usuarios_por_rol(
    idUsuario: int = Query(..., description="ID del usuario consultante"),
    db: Session = Depends(get_db)
):
    from fastapi_app.models.usuario import Usuario
    usuario = db.query(Usuario).get(idUsuario)
    if not usuario:
        return []
    es_admin = any(r.nombre == "Administrador" for r in usuario.roles)
    es_subdirector = any(r.nombre == "Comercial - Subdirector" for r in usuario.roles)
    resultado = []
    if es_admin:
        roles = db.query(Rol).all()
    elif es_subdirector:
        roles = db.query(Rol).filter(Rol.nombre == "Comercial - Subdirector").all()
    else:
        return []
    for rol in roles:
        usuarios_list = []
        for u in rol.usuarios:
            usuarios_list.append({
                "id_usuario": u.id,
                "dni": getattr(u, "documentoIdentidad", None),
                "correo": u.correo,
                "nombres": u.nombre,
                "celular": None
            })
        resultado.append({
            "id_rol": rol.id,
            "nombre": rol.nombre,
            "usuarios": usuarios_list
        })
    return resultado