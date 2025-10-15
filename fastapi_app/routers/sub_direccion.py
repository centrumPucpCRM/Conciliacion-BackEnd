from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import distinct

from ..database import get_db
from ..models.programa import Programa
from ..models.usuario import Usuario

router = APIRouter(prefix="/sub-direccion", tags=["Sub-Dirección"])


@router.get("/listar/usuario")
def listar_por_usuario(
    user_id: int = Query(..., description="ID del usuario", alias="user_id"),
    db: Session = Depends(get_db),
):
    """
    Lista las subdirecciones únicas asociadas a un usuario específico.
    El usuario debe ser jefe de producto de al menos un programa.
    """
    # Obtener subdirecciones únicas donde el usuario es jefe de producto
    subdirecciones = (
        db.query(distinct(Programa.subdireccion))
        .filter(Programa.idJefeProducto == user_id)
        .filter(Programa.subdireccion.isnot(None))
        .order_by(Programa.subdireccion)
        .all()
    )
    
    # Construir la respuesta con subdirecciones únicas
    items = [
        {
            "sub-direccion": subdir[0]
        }
        for subdir in subdirecciones
    ]
    
    return {
        "items": items
    }

