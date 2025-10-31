from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.orm import load_only, selectinload
from sqlalchemy import or_
from typing import List, Optional
from ..database import get_db
from ..models.propuesta import Propuesta
from ..models.cartera import Cartera
from ..models.solicitud import Solicitud as SolicitudModel
from ..models.solicitud import ValorSolicitud, TipoSolicitud
from ..models.usuario import Usuario
from ..models.rol_permiso import Rol
from ..schemas.propuesta import PropuestaListadoPage
from ..services.propuesta_filter_service import PropuestaFilterService
from datetime import datetime

router = APIRouter(prefix="/propuesta", tags=["Propuesta"])

@router.get("/{propuesta_id}/detalle")
def obtener_resumen_propuesta(
    propuesta_id: int,
    db: Session = Depends(get_db),
):
    propuesta = (
        db.query(Propuesta)
        .options(load_only(Propuesta.nombre, Propuesta.fechaPropuesta, Propuesta.horaPropuesta))
        .join(Propuesta.estadoPropuesta)
        .filter(Propuesta.id == propuesta_id)
        .first()
    )

    if not propuesta:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")

    return {
        "nombre": propuesta.nombre,
        "fechaPropuesta": propuesta.fechaPropuesta,
        "horaPropuesta": propuesta.horaPropuesta,
        "estadoPropuesta": propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else None,
    }


@router.get("/estados")
def obtener_estados_propuesta(db: Session = Depends(get_db)):
    """
    Obtiene el conteo de propuestas por categoría de estado.
    
    Returns:
        - activos: conteo de propuestas en estados activos (todos excepto CONCILIADA y CANCELADA)
        - conciliadas: conteo de propuestas en estado CONCILIADA
        - canceladas: conteo de propuestas en estado CANCELADA
    """
    counts = PropuestaFilterService.get_estado_counts(db)
    return counts


@router.get("/listar", response_model=PropuestaListadoPage)
def listar_propuestas(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1),
    fechaDesde: str = Query(None, description="Fecha desde (YYYY-MM-DD)", alias="fechaDesde"),
    fechaHasta: str = Query(None, description="Fecha hasta (YYYY-MM-DD)", alias="fechaHasta"),
    nombre: str = Query(None, description="Filtrar por nombre de propuesta (búsqueda parcial)", alias="nombre"),
    estado: Optional[List[str]] = Query(None, description="Filtrar por nombres de estado de propuesta (ej: CONCILIADA, CANCELADA)", alias="estado"),
    db: Session = Depends(get_db),
):
    """
    Lista propuestas con filtros aplicados.
    
    Reglas de filtrado de estados:
    - Sin parámetro estado: muestra todas las propuestas excepto CONCILIADA y CANCELADA
    - Con parámetro estado: muestra únicamente las propuestas de los estados especificados
    
    Estados disponibles: PROGRAMADA, GENERADA, PRECONCILIADA, APROBADA, CONCILIADA, CANCELADA
    """
    # Validar nombres de estado si se proporcionan
    if estado:
        # Asegurar que estado sea una lista
        if isinstance(estado, str):
            estado_list = [estado]
        else:
            estado_list = estado
        
        valid_estado_names, errors = PropuestaFilterService.validate_state_names(estado_list)
        if errors:
            raise HTTPException(status_code=400, detail=f"Estados inválidos: {', '.join(errors)}")
        estado_names = valid_estado_names
    else:
        estado_names = None

    # Query base con carga de relaciones necesarias
    base_query = db.query(Propuesta).options(
        selectinload(Propuesta.estadoPropuesta),
        selectinload(Propuesta.carteras).load_only(Cartera.nombre),
    )

    # Aplicar filtro de estados usando el servicio
    base_query = PropuestaFilterService.apply_state_filter(base_query, estado_names)

    # Filtrado por fechas
    if fechaDesde:
        try:
            fecha_desde_dt = datetime.strptime(fechaDesde, "%Y-%m-%d")
            base_query = base_query.filter(Propuesta.fechaPropuesta >= fecha_desde_dt)
        except Exception:
            pass
    if fechaHasta:
        try:
            fecha_hasta_dt = datetime.strptime(fechaHasta, "%Y-%m-%d")
            base_query = base_query.filter(Propuesta.fechaPropuesta <= fecha_hasta_dt)
        except Exception:
            pass
    
    # Filtrado por nombre
    if nombre:
        base_query = base_query.filter(Propuesta.nombre.ilike(f"%{nombre}%"))

    total = base_query.count()
    offset = (page - 1) * size

    propuestas: List[Propuesta] = (
        base_query.order_by(Propuesta.id.desc()).offset(offset).limit(size).all()
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


@router.patch("/avanzar-estado")
def avanzar_estado_propuesta(
    body: dict = Body(..., example={"idUsuario": 1, "idPropuesta": 2}),
    db: Session = Depends(get_db),
):
    """
    Avanza el estado de la propuesta en +1
    """
    propuesta_id = body.get("idPropuesta")
    
    # Buscar propuesta
    propuesta = db.query(Propuesta).filter(Propuesta.id == propuesta_id).first()
    
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    
    # Incrementar el estado en +1
    nuevo_estado_id = propuesta.estadoPropuesta_id + 1
    propuesta.estadoPropuesta_id = nuevo_estado_id
    db.commit()
    db.refresh(propuesta)
    
    return {
        "msg": "Estado de propuesta actualizado correctamente",
        "idPropuesta": propuesta.id,
        "estadoAnterior": propuesta.estadoPropuesta_id - 1,
        "estadoNuevo": propuesta.estadoPropuesta_id,
        "nombreEstado": propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else None
    }


@router.patch("/cancelar")
def cancelar_propuesta(
    body: dict = Body(..., example={"id": 1}),
    db: Session = Depends(get_db),
):
    """
    Cancela una propuesta cambiando su estado a CANCELADA
    """
    propuesta_id = body.get("id")
    
    if not propuesta_id:
        raise HTTPException(status_code=400, detail="El campo 'id' es requerido")
    
    # Buscar el estado CANCELADA en la base de datos
    from ..models.propuesta import EstadoPropuesta
    estado_cancelada = db.query(EstadoPropuesta).filter(EstadoPropuesta.nombre == "CANCELADA").first()
    
    if not estado_cancelada:
        raise HTTPException(status_code=500, detail="Estado CANCELADA no encontrado en la base de datos")
    
    # Buscar propuesta
    propuesta = db.query(Propuesta).filter(Propuesta.id == propuesta_id).first()
    
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    
    # Verificar que la propuesta no esté ya cancelada
    if propuesta.estadoPropuesta_id == estado_cancelada.id:
        raise HTTPException(status_code=400, detail="La propuesta ya está cancelada")
    
    # Guardar estado anterior para la respuesta
    estado_anterior_id = propuesta.estadoPropuesta_id
    estado_anterior_nombre = propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else None
    
    # Cambiar estado a CANCELADA
    propuesta.estadoPropuesta_id = estado_cancelada.id
    db.commit()
    db.refresh(propuesta)
    
    return {
        "msg": "Propuesta cancelada exitosamente",
        "idPropuesta": propuesta.id,
        "estadoAnterior": {
            "id": estado_anterior_id,
            "nombre": estado_anterior_nombre
        },
        "estadoNuevo": {
            "id": propuesta.estadoPropuesta_id,
            "nombre": propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else "CANCELADA"
        }
    }
