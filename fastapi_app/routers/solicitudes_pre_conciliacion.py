
from fastapi import Body
from ..models.propuesta_oportunidad import PropuestaOportunidad
# Endpoint para actualizar cualquier campo de PropuestaOportunidad por id

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from fastapi.responses import JSONResponse

from ..database import get_db
from ..models.solicitud import Solicitud
from ..models.propuesta import Propuesta
from ..models.usuario import Usuario
from ..models.solicitud_propuesta_programa import SolicitudPropuestaPrograma
from ..models.solicitud_propuesta_oportunidad import SolicitudPropuestaOportunidad

router = APIRouter(
    prefix="/solicitudes-pre-conciliacion",
    tags=["solicitudes-pre-conciliacion"],
    responses={404: {"description": "No encontrado"}},
)
@router.get("/propuesta/{id_propuesta}/usuario/{id_usuario}")
def get_solicitudes_by_propuesta_and_usuario(
    id_propuesta: int, 
    id_usuario: int, 
    db: Session = Depends(get_db)
):
    """
    Obtiene todas las solicitudes de una propuesta específica relacionadas con un usuario.
    """
    # Verificar que la propuesta existe
    propuesta = db.query(Propuesta).filter(Propuesta.id_propuesta == id_propuesta).first()
    if not propuesta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Propuesta con ID {id_propuesta} no encontrada"
        )
    
    # Verificar que el usuario existe
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {id_usuario} no encontrado"
        )
    
    # Buscar solicitudes de esta propuesta donde el usuario es generador o receptor
    solicitudes = db.query(Solicitud).filter(
        Solicitud.id_propuesta == id_propuesta,
        ((Solicitud.id_usuario_generador == id_usuario) | 
            (Solicitud.id_usuario_receptor == id_usuario))
    ).all()

    solicitud_ids = [s.id_solicitud for s in solicitudes]

    # Solicitudes Propuesta Oportunidad
    from ..models.propuesta_oportunidad import PropuestaOportunidad
    from ..models.oportunidad import Oportunidad
    from ..models.programa import Programa

    solicitudes_oportunidad = db.query(SolicitudPropuestaOportunidad).filter(
        SolicitudPropuestaOportunidad.id_solicitud.in_(solicitud_ids)
    ).all()
    result_oportunidad = []
    for s in solicitudes_oportunidad:
        solicitud = next((sol for sol in solicitudes if sol.id_solicitud == s.id_solicitud), None)
        nombre_alumno = None
        dni_alumno = None
        nombre_programa = None
        monto_oportunidad = None
        punto_minimo_apertura = None
        
        # Buscar la oportunidad y el programa
        po = db.query(PropuestaOportunidad).filter(PropuestaOportunidad.id_propuesta_oportunidad == s.id_propuesta_oportunidad).first()
        if po:
            oportunidad = db.query(Oportunidad).filter(Oportunidad.id_oportunidad == po.id_oportunidad).first()
            if oportunidad:
                nombre_alumno = oportunidad.nombre
                dni_alumno = oportunidad.documento_identidad
                monto_oportunidad = oportunidad.monto
            
            # Buscar el programa a través de PropuestaPrograma
            if po.id_propuesta_programa:
                from ..models.propuesta_programa import PropuestaPrograma
                pp = db.query(PropuestaPrograma).filter(PropuestaPrograma.id_propuesta_programa == po.id_propuesta_programa).first()
                if pp:
                    programa = db.query(Programa).filter(Programa.id_programa == pp.id_programa).first()
                    if programa:
                        nombre_programa = programa.nombre
                        punto_minimo_apertura = programa.punto_minimo_apertura
        if solicitud:
            result_oportunidad.append({
                "id": s.id,
                "id_solicitud": s.id_solicitud,
                "id_propuesta_oportunidad": s.id_propuesta_oportunidad,
                "monto_propuesto": getattr(s, "monto_propuesto", None),
                "monto_objetado": getattr(s, "monto_objetado", None),
                "monto": monto_oportunidad,
                "nombre_alumno": nombre_alumno,
                "dni_alumno": dni_alumno,
                "nombre_programa": nombre_programa,
                "punto_minimo_apertura": punto_minimo_apertura,
                "solicitud": {
                    "id_solicitud": solicitud.id_solicitud,
                    "id_propuesta": solicitud.id_propuesta,
                    "id_usuario_generador": solicitud.id_usuario_generador,
                    "id_usuario_receptor": solicitud.id_usuario_receptor,
                    "aceptado_por_responsable": solicitud.aceptado_por_responsable,
                    "tipo_solicitud": solicitud.tipo_solicitud,
                    "valor_solicitud": solicitud.valor_solicitud,
                    "comentario": solicitud.comentario,
                    "creado_en": solicitud.creado_en,
                    "abierta": solicitud.abierta
                }
            })

    # Solicitudes Propuesta Programa
    from ..models.propuesta_programa import PropuestaPrograma
    solicitudes_programa = db.query(SolicitudPropuestaPrograma).filter(
        SolicitudPropuestaPrograma.id_solicitud.in_(solicitud_ids)
    ).all()
    result_programa = []
    for s in solicitudes_programa:
        solicitud = next((sol for sol in solicitudes if sol.id_solicitud == s.id_solicitud), None)
        nombre_programa = None
        punto_minimo_apertura = None
        alumnos_matriculados = []
        
        pp = db.query(PropuestaPrograma).filter(PropuestaPrograma.id_propuesta_programa == s.id_propuesta_programa).first()
        if pp:
            programa = db.query(Programa).filter(Programa.id_programa == pp.id_programa).first()
            if programa:
                nombre_programa = programa.nombre
                punto_minimo_apertura = programa.punto_minimo_apertura
                
                # Buscar todos los alumnos matriculados para este programa
                from ..models.oportunidad import Oportunidad
                
                # Inicializar contador para alumnos matriculados en los estados requeridos
                alumnos_matriculados = 0
                
                # Obtener todas las oportunidades del programa
                oportunidades = db.query(Oportunidad).filter(
                    Oportunidad.id_programa == programa.id_programa,
                    Oportunidad.fecha_matricula.isnot(None)  # Solo alumnos matriculados
                ).all()
                
                # Contar las oportunidades que tienen los estados específicos
                for oportunidad in oportunidades:
                    # Buscar la propuesta oportunidad asociada a este alumno para esta propuesta
                    propuesta_oportunidad = db.query(PropuestaOportunidad).filter(
                        PropuestaOportunidad.id_oportunidad == oportunidad.id_oportunidad,
                        PropuestaOportunidad.id_propuesta == id_propuesta
                    ).first()
                    
                    # Verificar si tiene uno de los estados requeridos
                    if propuesta_oportunidad and propuesta_oportunidad.etapa_venta_propuesto in [
                        "3 - Matrícula", 
                        "4 - Cerrada/Ganada"
                    ]:
                        alumnos_matriculados += 1
        
        if solicitud:
            result_programa.append({
                "id": s.id,
                "id_solicitud": s.id_solicitud,
                "id_propuesta_programa": s.id_propuesta_programa,
                "nombre_programa": nombre_programa,
                "punto_minimo_apertura": punto_minimo_apertura,
                "alumnos_matriculados": alumnos_matriculados,  # Ahora es un número entero (contador)
                "solicitud": {
                    "id_solicitud": solicitud.id_solicitud,
                    "id_propuesta": solicitud.id_propuesta,
                    "id_usuario_generador": solicitud.id_usuario_generador,
                    "id_usuario_receptor": solicitud.id_usuario_receptor,
                    "aceptado_por_responsable": solicitud.aceptado_por_responsable,
                    "tipo_solicitud": solicitud.tipo_solicitud,
                    "valor_solicitud": solicitud.valor_solicitud,
                    "comentario": solicitud.comentario,
                    "creado_en": solicitud.creado_en,
                    "abierta": solicitud.abierta
                }
            })

    # Identificar las solicitudes que no están en ninguna de las dos categorías anteriores
    solicitudes_procesadas_ids = set(s["id_solicitud"] for s in result_oportunidad) | set(s["id_solicitud"] for s in result_programa)
    solicitudes_generales = []
    
    for solicitud in solicitudes:
        if solicitud.id_solicitud not in solicitudes_procesadas_ids:
            solicitudes_generales.append({
                "id_solicitud": solicitud.id_solicitud,
                "id_propuesta": solicitud.id_propuesta,
                "id_usuario_generador": solicitud.id_usuario_generador,
                "id_usuario_receptor": solicitud.id_usuario_receptor,
                "aceptado_por_responsable": solicitud.aceptado_por_responsable,
                "tipo_solicitud": solicitud.tipo_solicitud,
                "valor_solicitud": solicitud.valor_solicitud,
                "comentario": solicitud.comentario,
                "creado_en": solicitud.creado_en,
                "abierta": solicitud.abierta
            })

    return {
        "solicitudesPropuestaOportunidad": result_oportunidad,
        "solicitudesPropuestaPrograma": result_programa,
        "solicitudesGenerales": solicitudes_generales
    }
@router.patch("/solicitud/{id_solicitud}")
def update_solicitud_by_id(
    id_solicitud: int,
    fields: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Actualiza cualquier campo de la solicitud por su id_solicitud.
    Recibe un diccionario {campo: valor} y actualiza solo esos campos.
    """
    solicitud = db.query(Solicitud).filter(Solicitud.id_solicitud == id_solicitud).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail=f"Solicitud con ID {id_solicitud} no encontrada")

    # Campos válidos para cada entidad
    campos_solicitud = {"id_usuario_generador", "id_usuario_receptor", "comentario","valor_solicitud"}
    campos_spo = {"monto_propuesto", "monto_objetado"}
    updated = {}
    # Actualizar campos de Solicitud
    for campo, valor in fields.items():
        if campo in campos_solicitud:
            setattr(solicitud, campo, valor)
            updated[campo] = valor
        elif campo in campos_spo:
            spo = db.query(SolicitudPropuestaOportunidad).filter(SolicitudPropuestaOportunidad.id_solicitud == id_solicitud).first()
            if not spo:
                raise HTTPException(status_code=404, detail=f"SolicitudPropuestaOportunidad con id_solicitud {id_solicitud} no encontrada")
            setattr(spo, campo, valor)
            updated[campo] = valor
        else:
            raise HTTPException(status_code=400, detail=f"Campo '{campo}' no es válido para actualización")
    db.commit()
    db.refresh(solicitud)
    # Si se actualizó SPO, refrescar también
    if any(campo in campos_spo for campo in fields):
        spo = db.query(SolicitudPropuestaOportunidad).filter(SolicitudPropuestaOportunidad.id_solicitud == id_solicitud).first()
        if spo:
            db.refresh(spo)
    return updated