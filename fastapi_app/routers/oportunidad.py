
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
    etapas_excluir = ["1 - Interés", "2 - Calificación", "5 - Cerrada/Perdida"]
    query = (
        db.query(Oportunidad)
        .filter(Oportunidad.idPropuesta == propuesta_id)
        .filter(Oportunidad.idPrograma == programa_id)
        .filter((Oportunidad.eliminado == False) | (Oportunidad.eliminado.is_(None)))
        .filter(~Oportunidad.etapaVentaPropuesta.in_(etapas_excluir))
    )

    total = query.count()
    offset = (page - 1) * size
    rows = query.offset(offset).limit(size).all()

    items = [
        {
            "id": r.id,
            "documentoIdentidad": r.documentoIdentidad,
            "nombre": r.nombre,
            "descuento": r.descuento,
            "monto": r.monto,
            "montoPropuesto": r.montoPropuesto,
            "moneda": r.moneda,
            "fechaMatriculaPropuesta": r.fechaMatriculaPropuesta,
            "posibleAtipico": r.posibleAtipico,
            "becado": r.becado,
            "partyNumber": r.partyNumber,
            "conciliado": r.conciliado,
            "tipoCambioEquivalencia": r.tipoCambio.equivalencia if r.tipoCambio else None,
            "etapaVentaPropuesta": r.etapaVentaPropuesta,
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
@router.get("/listar/disponibles")
def listar_oportunidades_disponibles(
    propuesta_id: int = Query(..., alias="propuesta_id"),
    programa_id: int = Query(..., alias="programa_id"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Lista oportunidades filtradas por propuesta y programa con paginación, incluyendo solo las etapas de etapas_excluir.
    """
    etapas_incluir = ["1 - Interés", "2 - Calificación", "5 - Cerrada/Perdida"]
    query = (
        db.query(Oportunidad)
        .filter(Oportunidad.idPropuesta == propuesta_id)
        .filter(Oportunidad.idPrograma == programa_id)
        .filter((Oportunidad.eliminado == False) | (Oportunidad.eliminado.is_(None)))
        .filter(Oportunidad.etapaVentaPropuesta.in_(etapas_incluir))
    )

    total = query.count()
    offset = (page - 1) * size
    rows = query.offset(offset).limit(size).all()

    items = [
        {
            "id": r.id,
            "documentoIdentidad": r.documentoIdentidad,
            "nombre": r.nombre,
            "descuento": r.descuento,
            "monto": r.monto,
            "montoPropuesto": r.montoPropuesto,
            "moneda": r.moneda,
            "fechaMatriculaPropuesta": r.fechaMatriculaPropuesta,
            "posibleAtipico": r.posibleAtipico,
            "becado": r.becado,
            "partyNumber": r.partyNumber,
            "conciliado": r.conciliado,
            "tipoCambioEquivalencia": r.tipoCambio.equivalencia if r.tipoCambio else None,
            "etapaVentaPropuesta": r.etapaVentaPropuesta,
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