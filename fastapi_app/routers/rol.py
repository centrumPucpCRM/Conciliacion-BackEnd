from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi_app.database import get_db
from fastapi_app.models.rol_permiso import Rol

router = APIRouter(prefix="/rol", tags=["Rol"])

@router.get("/roles-usuarios-carteras", response_model=list)
def listar_usuarios_por_rol(db: Session = Depends(get_db)):
    roles = db.query(Rol).all()
    resultado = []
    for rol in roles:
        usuarios_list = []
        for u in rol.usuarios:
            carteras_list = []
            for c in u.carteras:
                carteras_list.append({
                    "id_cartera": c.id,
                    "nombre": c.nombre,
                    "descripcion": getattr(c, "descripcion", None)
                })
            usuarios_list.append({
                "id_usuario": u.id,
                "dni": getattr(u, "documentoIdentidad", None),
                "correo": u.correo,
                "nombres": u.nombre,
                "celular": None,  # Si tienes campo celular, cámbialo aquí
                "carteras": carteras_list
            })
        resultado.append({
            "id_rol": rol.id,
            "nombre": rol.nombre,
            "usuarios": usuarios_list
        })
    return resultado