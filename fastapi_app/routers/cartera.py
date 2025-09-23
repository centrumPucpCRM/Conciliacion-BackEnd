from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.cartera import Cartera as CarteraModel

router = APIRouter(prefix="/cartera", tags=["Cartera"])


@router.get("/listar")
def listar_carteras(db: Session = Depends(get_db)):
    """
    Devuelve todas las carteras sin paginación.
    """
    rows = db.query(CarteraModel.id, CarteraModel.nombre).all()
    items = [{"id": r.id, "cartera": r.nombre} for r in rows]
    return {"items": items}
