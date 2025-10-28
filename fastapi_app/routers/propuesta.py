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
    Obtiene todos los estados de propuesta disponibles con sus IDs y nombres.
    Útil para frontend para mostrar opciones de filtrado.
    """
    estados = PropuestaFilterService.get_available_states(db)
    estado_lov = PropuestaFilterService.get_estado_lov()
    return {
        "estados": estados,
        "estado_lov": estado_lov,
        "excluidos_por_defecto": PropuestaFilterService.EXCLUDED_STATES_BY_DEFAULT
    }


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
        valid_estado_names, errors = PropuestaFilterService.validate_state_names(estado)
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


@router.patch("/avanzar-estado")
def avanzar_estado_propuesta(
    body: dict = Body(..., example={"idUsuario": 1, "idPropuesta": 2}),
    db: Session = Depends(get_db),
):
    """
    Avanza el estado de la propuesta en +1
    Validaciones:
    - Si el usuario es JP: cierra todas sus solicitudes aceptadas (abierta=False)
    - Al final, independientemente del rol: verifica que no haya solicitudes abiertas pendientes antes de avanzar el estado
    """
    id_usuario = body.get("idUsuario")
    propuesta_id = body.get("idPropuesta")
    # Buscar usuario y sus roles
    usuario = db.query(Usuario).filter(Usuario.id == id_usuario).first()
    propuesta = db.query(Propuesta).filter(Propuesta.id == propuesta_id).first()
    # Verificar roles del usuario
    roles_usuario = [rol.nombre for rol in usuario.roles]
    
    # Si el usuario es JP (no es DAF)
    if "daf.supervisor" not in roles_usuario:
        # Buscar todas las solicitudes del usuario para esta propuesta que NO son de tipo APROBACION_JP
        solicitudes_usuario = db.query(SolicitudModel).join(ValorSolicitud).join(
            TipoSolicitud, SolicitudModel.tipoSolicitud
        ).filter(
            or_(
                SolicitudModel.idUsuarioReceptor == id_usuario,
                SolicitudModel.idUsuarioGenerador == id_usuario
            ),
            SolicitudModel.idPropuesta == propuesta_id,
            SolicitudModel.abierta == True,
            TipoSolicitud.nombre != "APROBACION_JP"
        ).all()
        
        if solicitudes_usuario:
            # Verificar si TODAS las solicitudes están en estado ACEPTADO
            todas_aceptadas = all(solicitud.valorSolicitud.nombre == "ACEPTADO" for solicitud in solicitudes_usuario)
            
            if todas_aceptadas:
                # Cerrar todas las solicitudes
                for solicitud in solicitudes_usuario:
                    solicitud.abierta = False
                db.commit()
            else:
                print(f"Usuario JP: tiene {len(solicitudes_usuario)} solicitud(es) pero NO todas están aceptadas. No se cierran.")
        else:
            print(f"Usuario JP: no tiene solicitudes abiertas (excepto APROBACION_JP) para esta propuesta")
    
    # VALIDACIÓN FINAL: Verificar que TODAS las solicitudes del usuario DAF estén ACEPTADAS
    # Solo validar si el estado de la propuesta NO es "GENERADA"
    if propuesta.estadoPropuesta and propuesta.estadoPropuesta.nombre == "PRECONCILIADA":
        # Buscar usuarios con rol DAF - Supervisor
        usuarios_daf = db.query(Usuario).join(Usuario.roles).filter(
            Rol.nombre == "DAF - Supervisor"
        ).all()
        if usuarios_daf:
            # Verificar si algún usuario DAF tiene solicitudes que NO están aceptadas
            for usuario_daf in usuarios_daf:
                # Buscar TODAS las solicitudes abiertas del usuario DAF para esta propuesta
                solicitudes_daf = db.query(SolicitudModel).join(ValorSolicitud).filter(
                    or_(
                        SolicitudModel.idUsuarioReceptor == usuario_daf.id,
                        SolicitudModel.idUsuarioGenerador == usuario_daf.id
                    ),
                    SolicitudModel.idPropuesta == propuesta_id,
                ).all()
                if solicitudes_daf:
                    # Verificar que TODAS estén en estado ACEPTADO
                    todas_aceptadas_daf = all(solicitud.valorSolicitud.nombre == "ACEPTADO" for solicitud in solicitudes_daf)
                    
                    if not todas_aceptadas_daf:
                        # Contar cuántas NO están aceptadas
                        no_aceptadas = [s for s in solicitudes_daf if s.valorSolicitud.nombre != "ACEPTADO"]
                        return {
                            "msg": f"No se puede avanzar el estado. El usuario DAF '{usuario_daf.nombre}' tiene {len(no_aceptadas)} solicitud(es) que NO están aceptadas. Todas deben estar en estado ACEPTADO."
                        }
        print(f"Validación final pasada: todos los usuarios DAF tienen todas sus solicitudes aceptadas")
    else:
        print(f"Estado de propuesta es GENERADA, se omite validación de solicitudes DAF")
    
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
