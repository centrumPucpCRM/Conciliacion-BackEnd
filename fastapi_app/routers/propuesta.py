from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm import load_only, selectinload
from typing import List
from ..database import get_db
from ..models.propuesta import Propuesta
from ..models.cartera import Cartera
from ..schemas.propuesta import PropuestaListadoPage

router = APIRouter(prefix="/propuesta", tags=["Propuesta"])


@router.get("/listar", response_model=PropuestaListadoPage)
def listar_propuestas(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1),
    db: Session = Depends(get_db),
):
    # Query base con carga de relaciones necesarias
    base_query = (
        db.query(Propuesta)
        .options(
            selectinload(Propuesta.estadoPropuesta),
            selectinload(Propuesta.carteras).load_only(Cartera.nombre),
        )
    )

    total = base_query.count()
    offset = (page - 1) * size

    propuestas: List[Propuesta] = (
        base_query.order_by(Propuesta.id).offset(offset).limit(size).all()
    )

    items = [
        {
            "id": p.id,
            "nombre": p.nombre,
            "fechaPropuesta": p.fechaPropuesta,
            "estado": p.estadoPropuesta.nombre if p.estadoPropuesta else None,
            "carteras": [c.nombre for c in p.carteras] if p.carteras else [],
        }
        for p in propuestas
    ]

    pages = (total + size - 1) // size if size else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }
