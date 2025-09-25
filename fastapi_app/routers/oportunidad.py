from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ..database import get_db
from ..models.oportunidad import Oportunidad

router = APIRouter(prefix="/oportunidad", tags=["Oportunidad"])


# TODO: Implementar user_id cuando se implemente el token
@router.get("/listar")
def listar_oportunidades(
    propuesta_id: int = Query(..., alias="propuesta_id"),
    programa_id: int = Query(..., alias="programa_id"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Lista oportunidades filtradas por propuesta y programa con paginación.
    """
    query = (
        db.query(
            Oportunidad.nombre,
            Oportunidad.documentoIdentidad,
            Oportunidad.monto,
            Oportunidad.posibleAtipico,
            Oportunidad.montoPropuesto,
        )
        .filter(Oportunidad.idPropuesta == propuesta_id)
        .filter(Oportunidad.idPrograma == programa_id)
        .filter((Oportunidad.eliminado == False) | (Oportunidad.eliminado.is_(None)))
    )

    total = query.count()
    offset = (page - 1) * size
    rows = query.offset(offset).limit(size).all()

    items = [
        {
            "nombre": r.nombre,
            "documentoIdentidad": r.documentoIdentidad,
            "monto": r.monto,
            "posibleAtipico": r.posibleAtipico,
            "montoPropuesto": r.montoPropuesto,
        }
        for r in rows
    ]

    pages = (total + size - 1) // size if size else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }
