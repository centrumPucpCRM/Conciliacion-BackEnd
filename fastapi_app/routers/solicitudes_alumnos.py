from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.solicitud import Solicitud
from ..schemas.solicitudes_jp import SolicitudAprobacionAlumnoCreate, SolicitudAprobacionAlumnoResponse
import datetime

router = APIRouter(
    prefix="/solicitudes/alumnos",
    tags=["Solicitudes Alumnos"],
    responses={404: {"description": "Not found"}},
)

@router.post("/edicion", response_model=SolicitudAprobacionAlumnoResponse)
def create_solicitud_edicion_alumno(
    solicitud_data: SolicitudAprobacionAlumnoCreate,
    db: Session = Depends(get_db)
):
    """
    Crear una solicitud de edición de alumno
    """
    try:
        nueva_solicitud = Solicitud(
            id_propuesta=solicitud_data.id_propuesta,
            id_usuario_generador=solicitud_data.id_usuario_generador,
            id_usuario_receptor=solicitud_data.id_usuario_receptor,
            aceptado_por_responsable=False,
            tipo_solicitud="EDICION_ALUMNO",
            valor_solicitud="PENDIENTE",
            comentario=solicitud_data.comentario,
            creado_en=datetime.datetime.now(),
            abierta=True
        )
        db.add(nueva_solicitud)
        db.commit()
        db.refresh(nueva_solicitud)
        return SolicitudAprobacionAlumnoResponse(
            id_solicitud=nueva_solicitud.id_solicitud,
            id_propuesta=nueva_solicitud.id_propuesta,
            id_propuesta_oportunidad=solicitud_data.id_propuesta_oportunidad,
            id_usuario_generador=nueva_solicitud.id_usuario_generador,
            id_usuario_receptor=nueva_solicitud.id_usuario_receptor,
            aceptado_por_responsable=nueva_solicitud.aceptado_por_responsable,
            tipo_solicitud=nueva_solicitud.tipo_solicitud,
            valor_solicitud=nueva_solicitud.valor_solicitud,
            monto_propuesto=solicitud_data.monto_propuesto,
            monto_objetado=solicitud_data.monto_objetado,
            comentario=nueva_solicitud.comentario,
            creado_en=nueva_solicitud.creado_en,
            abierta=nueva_solicitud.abierta
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando solicitud de edición de alumno: {str(e)}"
        )