
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ..database import get_db
from ..models.oportunidad import Oportunidad
from ..models.solicitud import Solicitud as SolicitudModel
from ..models.solicitud_x_oportunidad import SolicitudXOportunidad

router = APIRouter(prefix="/oportunidad", tags=["Oportunidad"])

def obtener_oportunidades_con_solicitudes(
    propuesta_id: int,
    programa_id: int,
    db: Session
) -> set:
    """
    Función interna que retorna un set con los IDs de oportunidades que tienen solicitudes asociadas.
    """
    # Obtener todas las solicitudes del usuario y propuesta
    solicitudes = db.query(SolicitudModel).filter(
        SolicitudModel.idPropuesta == propuesta_id
    ).all()
    
    if not solicitudes:
        return set()
    
    # Obtener los IDs de solicitud
    solicitud_ids = [s.id for s in solicitudes]
    
    # Obtener las relaciones solicitud_x_oportunidad
    sxos = db.query(SolicitudXOportunidad).filter(
        SolicitudXOportunidad.idSolicitud.in_(solicitud_ids)
    ).all()
    
    if not sxos:
        return set()
    
    # Obtener los IDs de oportunidad
    oportunidad_ids = [sxo.idOportunidad for sxo in sxos]
    
    # Filtrar oportunidades por programa_id
    oportunidades = db.query(Oportunidad).filter(
        Oportunidad.id.in_(oportunidad_ids),
        Oportunidad.idPrograma == programa_id
    ).all()
    
    # Retornar set de IDs
    return set(op.id for op in oportunidades)

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
    Incluye campo 'editar' que indica si la oportunidad NO tiene solicitudes asociadas (true = puede editar).
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

    # Obtener IDs de oportunidades con solicitudes
    oportunidades_con_solicitudes = obtener_oportunidades_con_solicitudes(
        propuesta_id=propuesta_id,
        programa_id=programa_id,
        db=db
    )

    items = [
        {
            "id": r.id,
            "dni": r.documentoIdentidad,
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
            "editar": r.id not in oportunidades_con_solicitudes,  # True si NO tiene solicitudes
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
    Incluye campo 'editar' que indica si la oportunidad NO tiene solicitudes asociadas (true = puede editar).
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

    # Obtener IDs de oportunidades con solicitudes
    oportunidades_con_solicitudes = obtener_oportunidades_con_solicitudes(
        propuesta_id=propuesta_id,
        programa_id=programa_id,
        db=db
    )

    items = [
        {
            "id": r.id,
            "dni": r.documentoIdentidad,
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
            "editar": r.id not in oportunidades_con_solicitudes,  # True si NO tiene solicitudes
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