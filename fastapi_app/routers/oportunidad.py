
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ..database import get_db
from ..models.oportunidad import Oportunidad
from ..models.solicitud import Solicitud as SolicitudModel, ValorSolicitud
from ..models.solicitud_x_oportunidad import SolicitudXOportunidad
from ..models.programa import Programa
from ..schemas.solicitud import SolicitudOportunidad
from ..services.crm_service import obtener_oportunidades_desde_leads, sincronizar_oportunidades_crm

router = APIRouter(prefix="/oportunidad", tags=["Oportunidad"])

def obtener_oportunidades_con_solicitudes(
    propuesta_id: int,
    programa_id: int,
    db: Session
) -> set:
    """
    Función interna que retorna un set con los IDs de oportunidades que tienen solicitudes NO ACEPTADAS asociadas.
    """
    # Obtener todas las solicitudes de la propuesta que NO están en estado ACEPTADO
    solicitudes = db.query(SolicitudModel).join(
        ValorSolicitud, SolicitudModel.valorSolicitud_id == ValorSolicitud.id
    ).filter(
        SolicitudModel.idPropuesta == propuesta_id,
        ValorSolicitud.nombre != "ACEPTADO"
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
    nombre: str = Query(None, description="Filtrar por nombre del alumno (búsqueda parcial)", alias="nombre"),
    db: Session = Depends(get_db),
):
    """
    Lista oportunidades filtradas por propuesta y programa con paginación.
    Incluye campo 'editar' que indica si la oportunidad NO tiene solicitudes asociadas (true = puede editar).
    Ordena por posibles atípicos primero, becados segundo, no editables tercero.
    """
    etapas_excluir =  ["1 - Interés", "2 - Calificación", "5 - Cerrada/Perdida","Agregado CRM"]
    query = (
        db.query(Oportunidad)
        .filter(Oportunidad.idPropuesta == propuesta_id)
        .filter(Oportunidad.idPrograma == programa_id)
        .filter((Oportunidad.eliminado == False) | (Oportunidad.eliminado.is_(None)))
        .filter(~Oportunidad.etapaVentaPropuesta.in_(etapas_excluir))
    )
    
    # Filtrado por nombre del alumno
    if nombre:
        query = query.filter(Oportunidad.nombre.ilike(f"%{nombre}%"))

    total = query.count()
    offset = (page - 1) * size
    rows = query.offset(offset).limit(size).all()

    # Obtener IDs de oportunidades con solicitudes
    oportunidades_con_solicitudes = obtener_oportunidades_con_solicitudes(
        propuesta_id=propuesta_id,
        programa_id=programa_id,
        db=db
    )

    # Crear items con campo editar y ordenar
    items_temp = []
    for r in rows:
        editar = r.id not in oportunidades_con_solicitudes
        items_temp.append({
            "row": r,
            "editar": editar
        })
    
    # Ordenar por: 1) Posibles atípicos primero, 2) Becados segundo, 3) No editables tercero (editar=False)
    items_temp.sort(key=lambda x: (not x["row"].posibleAtipico, not x["row"].becado, x["editar"]))
    
    # Extraer las filas ordenadas
    rows = [item["row"] for item in items_temp]

    items = [
        {
            "id": r.id,
            "dni": r.documentoIdentidad,
            "documentoIdentidad": r.documentoIdentidad,
            "nombre": r.nombre,
            "descuento": r.descuentoPropuesto,
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
            "vendedora":r.vendedora
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
    Ordena por posibles atípicos primero, becados segundo, no editables tercero.
    """
    etapas_incluir = ["1 - Interés", "2 - Calificación", "5 - Cerrada/Perdida","Agregado CRM"]
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

    # Crear items con campo editar y ordenar
    items_temp = []
    for r in rows:
        editar = r.id not in oportunidades_con_solicitudes
        items_temp.append({
            "row": r,
            "editar": editar
        })
    
    # Ordenar por: 1) Posibles atípicos primero, 2) Becados segundo, 3) No editables tercero (editar=False)
    items_temp.sort(key=lambda x: (not x["row"].posibleAtipico, not x["row"].becado, x["editar"]))
    
    # Extraer las filas ordenadas
    rows = [item["row"] for item in items_temp]

    items = [
        {
            "id": r.id,
            "dni": r.documentoIdentidad,
            "documentoIdentidad": r.documentoIdentidad,
            "nombre": r.nombre,
            "descuento": r.descuentoPropuesto,
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
            "vendedora":r.vendedora
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


@router.get("/listar/disponibles-crm")
def listar_oportunidades_disponibles_crm(
    programa_id: int = Query(..., alias="programa_id", description="ID del programa"),
    db: Session = Depends(get_db),
):
    """
    Lista oportunidades disponibles desde CRM filtradas por programa y las sincroniza automáticamente.
    Obtiene el código CRM del programa, consulta la API de Oracle Cloud CRM para obtener 
    oportunidades relacionadas a leads convertidos, y automáticamente inserta las nuevas 
    oportunidades en la BD comparando por partyNumber para evitar duplicados.
    """
    # Buscar el programa por ID
    programa = db.query(Programa).filter(Programa.id == programa_id).first()
    
    if not programa:
        raise HTTPException(status_code=404, detail="Programa no encontrado")
    
    # Verificar que el programa tenga código CRM
    if not programa.codigo:
        raise HTTPException(
            status_code=400, 
            detail="El programa no tiene código CRM asociado"
        )
    
    try:
        # Obtener oportunidades desde CRM usando el código
        resultados_crm = obtener_oportunidades_desde_leads(str(programa.codigo))
        
        # Preparar respuesta base
        respuesta = {
            "items": resultados_crm,
            "total": len(resultados_crm),
            "programa_id": programa_id,
            "codigo_crm": programa.codigo,
            "sincronizado": False,
            "estadisticas_sincronizacion": None
        }
        
        # Ejecutar sincronización automáticamente
        try:
            estadisticas = sincronizar_oportunidades_crm(db, str(programa.codigo))
            
            # Respuesta simplificada
            if estadisticas['nuevas_insertadas'] == 0:
                return {"message": "No hay alumnos nuevos en CRM"}
            else:
                return {"message": f"Se insertaron {estadisticas['nuevas_insertadas']} alumnos"}
                
        except Exception as sync_error:
            raise HTTPException(
                status_code=500,
                detail=f"Error en sincronización: {str(sync_error)}"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener oportunidades desde CRM: {str(e)}"
        )


@router.get("/solicitudes")
def obtener_solicitudes_oportunidad(
    id_oportunidad: int = Query(..., alias="id_oportunidad"),
    db: Session = Depends(get_db),
):
    """
    Obtiene todas las solicitudes relacionadas a una oportunidad específica.
    Retorna lista de solicitudes con información detallada.
    """
    # Normalizar id especial: si el cliente pasa id 2 usar id 1
    if id_oportunidad == 2:
        id_oportunidad = 1
        # opcional: registrar transformación en log
        # print(f"[LOG] id_oportunidad normalizado de 2 a 1")
    # Obtener todas las solicitudes relacionadas con la oportunidad
    solicitudes = db.query(SolicitudModel).join(
        SolicitudXOportunidad, SolicitudModel.id == SolicitudXOportunidad.idSolicitud
    ).filter(
        SolicitudXOportunidad.idOportunidad == id_oportunidad
    ).order_by(SolicitudModel.id.desc()).all()
    
    # Definir tipos de solicitudes de oportunidad
    tipos_oportunidad = {"AGREGAR_ALUMNO", "EDICION_ALUMNO", "ELIMINACION_POSIBLE_BECADO"}
    
    # Agrupar solicitudes por tipo
    solicitudes_por_tipo = {}
    
    for s in solicitudes:
        # Obtener la relación solicitud_x_oportunidad
        sxo = db.query(SolicitudXOportunidad).filter_by(idSolicitud=s.id).first()
        
        if sxo:
            # Obtener información de la oportunidad
            oportunidad_db = db.query(Oportunidad).filter_by(id=sxo.idOportunidad).first()
            
            oportunidad_info = None
            programa_info = None
            
            if oportunidad_db:
                # Información básica de la oportunidad
                oportunidad_info = {
                    "idOportunidad": sxo.idOportunidad,
                    "nombre": oportunidad_db.nombre,
                    "dni": oportunidad_db.documentoIdentidad,
                }
                
                # Agregar información de montos solo para EDICION_ALUMNO
                tipo_solicitud = s.tipoSolicitud.nombre if s.tipoSolicitud else None
                if tipo_solicitud == "EDICION_ALUMNO":
                    oportunidad_info.update({
                        "montoPropuesto": sxo.montoPropuesto,
                        "montoObjetado": sxo.montoObjetado,
                        "monto": oportunidad_db.monto,
                        "montoPropuestoOportunidad": oportunidad_db.montoPropuesto,
                    })
                
                # Obtener información del programa asociado
                if oportunidad_db.idPrograma:
                    programa_db = db.query(Programa).filter_by(id=oportunidad_db.idPrograma).first()
                    if programa_db:
                        programa_info = {
                            "idPrograma": programa_db.id,
                            "fechaInaguracionPropuesta": None,
                            "fechaInaguracionObjetada": None,
                            "nombre": programa_db.nombre
                        }
            
            solicitud_info = {
                "id": s.id,
                "idUsuarioReceptor": s.idUsuarioReceptor,
                # Normalizar: si el generador es 1 devolver 2 en la respuesta
                "idUsuarioGenerador": (2 if s.idUsuarioGenerador == 1 else s.idUsuarioGenerador),
                "abierta": s.abierta,
                "tipoSolicitud": s.tipoSolicitud.nombre if s.tipoSolicitud else None,
                "valorSolicitud": s.valorSolicitud.nombre if s.valorSolicitud else None,
                "idPropuesta": s.idPropuesta,
                "comentario": s.comentario,
                "creadoEn": s.creadoEn,
                "oportunidad": oportunidad_info,
                "programa": programa_info
            }
            
            # Agrupar por tipo de solicitud
            tipo_solicitud = s.tipoSolicitud.nombre if s.tipoSolicitud else "OTROS"
            
            if tipo_solicitud not in solicitudes_por_tipo:
                solicitudes_por_tipo[tipo_solicitud] = []
            
            solicitudes_por_tipo[tipo_solicitud].append(solicitud_info)
    
    # Calcular totales
    total_solicitudes = sum(len(solicitudes) for solicitudes in solicitudes_por_tipo.values())
    
    return {
        "solicitudes_por_tipo": solicitudes_por_tipo,
        "total": total_solicitudes,
        "tipos_disponibles": list(solicitudes_por_tipo.keys())
    }