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
from ..models.programa import Programa as ProgramaModel
from ..models.oportunidad import Oportunidad
from datetime import datetime

router = APIRouter(prefix="/propuesta", tags=["Propuesta"])


@router.get("/{propuesta_id}/programas-conciliacion")
def obtener_programas_conciliacion(
    propuesta_id: int,
    user_id: Optional[int] = Query(None, description="ID del usuario para filtrar programas por rol"),
    db: Session = Depends(get_db),
):
    """
    Obtiene los programas de una propuesta separados en mes_conciliado y meses_anteriores.
    Igual que informacion_preconciliacion pero para la vista de Conciliaciones.
    """
    propuesta = db.query(Propuesta).filter(Propuesta.id == propuesta_id).first()
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")

    fecha_propuesta = propuesta.fechaPropuesta
    if not fecha_propuesta:
        raise HTTPException(status_code=400, detail="La propuesta no tiene fecha")

    # Calcular mes conciliado (mes anterior a la fecha de propuesta)
    if fecha_propuesta.month == 1:
        mes_conciliado = 12
        anio_conciliado = fecha_propuesta.year - 1
    else:
        mes_conciliado = fecha_propuesta.month - 1
        anio_conciliado = fecha_propuesta.year

    # Calcular tres meses anteriores al mes conciliado (offsets 2, 3, 4)
    meses_anteriores = []
    for offset in [2, 3, 4]:
        mes = fecha_propuesta.month - offset
        anio = fecha_propuesta.year
        while mes <= 0:
            mes += 12
            anio -= 1
        meses_anteriores.append((mes, anio))

    # Filtrar programas según rol del usuario
    if user_id:
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        roles_usuario = {rol.nombre for rol in usuario.roles} if usuario and usuario.roles else set()

        roles_daf = {"DAF - Supervisor", "DAF - Subdirector", "DAF - Admin"}
        if roles_usuario & roles_daf:
            programas_all = db.query(ProgramaModel).filter(
                ProgramaModel.idPropuesta == propuesta_id
            ).order_by(ProgramaModel.fechaInaguracionPropuesta.desc()).all()
        elif "Comercial - Subdirector" in roles_usuario or "Comercial - Jefe de producto" in roles_usuario:
            condiciones = []
            if "Comercial - Jefe de producto" in roles_usuario:
                condiciones.append(ProgramaModel.idJefeProducto == user_id)
            if "Comercial - Subdirector" in roles_usuario:
                condiciones.append(ProgramaModel.idSubdirector == user_id)
            programas_all = db.query(ProgramaModel).filter(
                ProgramaModel.idPropuesta == propuesta_id,
                or_(*condiciones)
            ).order_by(ProgramaModel.fechaInaguracionPropuesta.desc()).all()
        else:
            programas_all = []
    else:
        programas_all = db.query(ProgramaModel).filter(
            ProgramaModel.idPropuesta == propuesta_id
        ).order_by(ProgramaModel.fechaInaguracionPropuesta.desc()).all()

    # Separar programas por mes
    programas_mes_conciliado = [
        p for p in programas_all
        if p.fechaInaguracionPropuesta
        and p.fechaInaguracionPropuesta.month == mes_conciliado
        and p.fechaInaguracionPropuesta.year == anio_conciliado
    ]
    programas_tres_meses = [
        p for p in programas_all
        if p.fechaInaguracionPropuesta
        and any(
            p.fechaInaguracionPropuesta.month == m and p.fechaInaguracionPropuesta.year == a
            for m, a in meses_anteriores
        )
    ]

    # Excluir oportunidades eliminadas y en etapas no válidas
    etapas_excluir = ["1 - Interés", "2 - Calificación", "5 - Cerrada/Perdida", "Agregado CRM"]
    oportunidades_all = db.query(Oportunidad).filter(
        Oportunidad.idPropuesta == propuesta_id,
        Oportunidad.etapaVentaPropuesta.notin_(etapas_excluir),
        Oportunidad.eliminado == False
    ).all()

    oportunidades_por_programa = {}
    for o in oportunidades_all:
        oportunidades_por_programa.setdefault(o.idPrograma, []).append(o)

    def build_programa_item(p):
        oportunidades = oportunidades_por_programa.get(p.id, [])
        monto_opty = sum(o.montoPropuesto or 0 for o in oportunidades)
        count_opty = len(oportunidades)

        alumnos = []
        for o in oportunidades:
            monto_editado = o.montoPropuesto != o.monto if o.monto else False
            alumnos.append({
                "id": o.id,
                "nombre": o.nombre,
                "descuento": o.descuento,
                "monto": o.monto,
                "montoPropuesto": o.montoPropuesto,
                "montoEditado": bool(monto_editado),
                "moneda": o.moneda,
                "etapaVentaPropuesta": o.etapaVentaPropuesta,
                "becado": bool(o.becado),
                "posibleAtipico": bool(o.posibleAtipico),
                "conciliado": bool(o.conciliado),
            })

        return {
            "id": p.id,
            "codigo": p.codigo,
            "nombre": p.nombre,
            "subdireccion": p.subdireccion,
            "cartera": p.cartera,
            "mes": p.mes,
            "fechaDeInaguracion": p.fechaInaguracionPropuesta,
            "metaDeVenta": p.metaDeVenta,
            "metaDeAlumnos": p.metaDeAlumnos,
            "alumnosReales": count_opty,
            "montoReal": monto_opty,
            "enRiesgo": bool(p.enRiesgo),
            "comentario": p.comentario,
            "fijoFueraDeCounter": p.fijoFueraDeCounter or 0,
            "montoFijoFueraDeCounter": p.montoFijoFueraDeCounter or 0.0,
            "alumnos": alumnos,
        }

    items_conciliado = [build_programa_item(p) for p in programas_mes_conciliado]
    items_anteriores = [build_programa_item(p) for p in programas_tres_meses]

    return {
        "propuesta": {
            "id": propuesta.id,
            "nombre": propuesta.nombre,
            "fechaPropuesta": propuesta.fechaPropuesta,
            "horaPropuesta": propuesta.horaPropuesta,
            "estado": propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else None,
        },
        "mesConciliado": items_conciliado,
        "mesesAnteriores": items_anteriores,
    }


@router.post("/{propuesta_id}/sync-todos-fijo-fuera-counter")
def sync_todos_fijo_fuera_counter(propuesta_id: int, db: Session = Depends(get_db)):
    """
    Consulta Oracle Sales Cloud y actualiza el conteo de 'Fijo fuera de counter'
    para todos los programas de una propuesta.
    """
    from ..services.crm_service import obtener_fijos_fuera_counter

    propuesta = db.query(Propuesta).filter(Propuesta.id == propuesta_id).first()
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")

    programas = db.query(ProgramaModel).filter(
        ProgramaModel.idPropuesta == propuesta_id,
        ProgramaModel.codigo.isnot(None),
    ).all()

    resultados = []
    errores = 0

    for p in programas:
        try:
            resultado = obtener_fijos_fuera_counter(p.codigo)
            p.fijoFueraDeCounter = resultado["count"]
            p.montoFijoFueraDeCounter = resultado["monto"]
            resultados.append({
                "idPrograma": p.id,
                "fijoFueraDeCounter": resultado["count"],
                "montoFijoFueraDeCounter": resultado["monto"],
            })
        except Exception as e:
            errores += 1
            resultados.append({"idPrograma": p.id, "error": str(e)})

    db.commit()

    return {
        "actualizados": len(resultados) - errores,
        "errores": errores,
        "resultados": resultados,
    }


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


@router.get("/estados-conciliaciones")
def obtener_estados_conciliaciones(db: Session = Depends(get_db)):
    """
    Obtiene el conteo de propuestas para la vista de Conciliaciones.
    Returns:
        - conciliadas: conteo de propuestas en estado CONCILIADA
        - proyectadas: conteo de propuestas en estado PROYECTADA
        - canceladas: conteo de propuestas en estado CANCELADA
    """
    from ..models.propuesta import EstadoPropuesta as EstadoPropuestaModel
    conciliadas = db.query(Propuesta).join(EstadoPropuestaModel).filter(EstadoPropuestaModel.nombre == "CONCILIADA").count()
    proyectadas = db.query(Propuesta).join(EstadoPropuestaModel).filter(EstadoPropuestaModel.nombre == "PROYECTADA").count()
    canceladas = db.query(Propuesta).join(EstadoPropuestaModel).filter(EstadoPropuestaModel.nombre == "CANCELADA").count()
    return {"conciliadas": conciliadas, "proyectadas": proyectadas, "canceladas": canceladas}


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


@router.patch("/conciliar")
def conciliar_propuesta(
    body: dict = Body(
        ...,
        example={
            "idPropuesta": 1
        }
    ),
    db: Session = Depends(get_db)
):
    """
    Concilia una propuesta cambiando su estado de PRECONCILIADA a CONCILIADA
    """
    id_propuesta = body.get("idPropuesta")
    
    if not id_propuesta:
        raise HTTPException(status_code=400, detail="El campo 'idPropuesta' es requerido")
    
    # Buscar el estado CONCILIADA en la base de datos
    from ..models.propuesta import EstadoPropuesta
    estado_conciliada = db.query(EstadoPropuesta).filter(EstadoPropuesta.nombre == "CONCILIADA").first()
    
    if not estado_conciliada:
        raise HTTPException(status_code=500, detail="Estado CONCILIADA no encontrado en la base de datos")
    
    # Buscar propuesta
    propuesta = db.query(Propuesta).filter(Propuesta.id == id_propuesta).first()
    
    if not propuesta:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    
    # Verificar que la propuesta esté en estado PRECONCILIADA
    estado_actual_nombre = propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else None
    if estado_actual_nombre != "PRECONCILIADA":
        raise HTTPException(
            status_code=400, 
            detail=f"La propuesta debe estar en estado PRECONCILIADA para ser conciliada. Estado actual: {estado_actual_nombre}"
        )
    
    # Guardar estado anterior para la respuesta
    estado_anterior_id = propuesta.estadoPropuesta_id
    estado_anterior_nombre = estado_actual_nombre
    
    # Cambiar estado a CONCILIADA
    propuesta.estadoPropuesta_id = estado_conciliada.id

    # Marcar como conciliadas todas las oportunidades no eliminadas de esta propuesta
    db.query(Oportunidad).filter(
        Oportunidad.idPropuesta == id_propuesta,
        Oportunidad.eliminado == False,
    ).update({"conciliado": True}, synchronize_session="fetch")

    db.commit()
    db.refresh(propuesta)
    
    return {
        "msg": "Propuesta conciliada exitosamente",
        "idPropuesta": propuesta.id,
        "estadoAnterior": {
            "id": estado_anterior_id,
            "nombre": estado_anterior_nombre
        },
        "estadoNuevo": {
            "id": propuesta.estadoPropuesta_id,
            "nombre": propuesta.estadoPropuesta.nombre if propuesta.estadoPropuesta else "CONCILIADA"
        }
    }
