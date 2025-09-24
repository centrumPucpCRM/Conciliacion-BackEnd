from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.cartera import Cartera as CarteraModel
from ..models.usuario import Usuario as UsuarioModel

router = APIRouter(prefix="/cartera", tags=["Cartera"])


@router.get("/listar")
def listar_carteras(db: Session = Depends(get_db)):
    """
    Devuelve todas las carteras sin paginación.
    """
    rows = db.query(CarteraModel.id, CarteraModel.nombre).all()
    items = [{"id": r.id, "cartera": r.nombre} for r in rows]
    return {"items": items}


@router.get("/listar/{user_id}")
def listar_carteras_por_usuario(user_id: int, db: Session = Depends(get_db)):
    """
    Devuelve todas las carteras asociadas a un usuario específico (sin paginación).
    """
    rows = (
        db.query(CarteraModel.id, CarteraModel.nombre)
        .join(CarteraModel.usuarios)
        .filter(UsuarioModel.id == user_id)
        .all()
    )
    items = [{"id": r.id, "cartera": r.nombre} for r in rows]
    return {"items": items}
