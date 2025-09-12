from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from ..database import get_db
from ..models.solicitud import Solicitud
from ..schemas.solicitudes_jp import SolicitudAprobacionJPResponse, SolicitudAprobacionAlumnoCreate, SolicitudAprobacionAlumnoResponse
import datetime

router = APIRouter(
    prefix="/solicitudes/jp",
    tags=["Solicitudes JP"],
    responses={404: {"description": "Not found"}},
)

class SolicitudAprobacionJPCreate(BaseModel):
    id_propuesta: int
    id_usuario_generador: int
    id_usuario_receptor: int
    tipo_solicitud: str
    comentario: Optional[str] = None
    valor_solicitud: str

@router.post("/aprobacion_subdirector", response_model=SolicitudAprobacionJPResponse)
def create_solicitud_aprobacion_subdirector(
    solicitud_data: SolicitudAprobacionJPCreate,
    db: Session = Depends(get_db)
):
    """
    Crear una solicitud de aprobación JP para subdirector
    """
    try:
        nueva_solicitud = Solicitud(
            id_propuesta=solicitud_data.id_propuesta,
            id_usuario_generador=solicitud_data.id_usuario_generador,
            id_usuario_receptor=solicitud_data.id_usuario_receptor,
            aceptado_por_responsable=False,
            tipo_solicitud=solicitud_data.tipo_solicitud,
            valor_solicitud=solicitud_data.valor_solicitud,
            comentario=solicitud_data.comentario or "Solicitud de aprobación JP para subdirector",
            creado_en=datetime.datetime.now(),
            abierta=True
        )
        db.add(nueva_solicitud)
        db.commit()
        db.refresh(nueva_solicitud)
        return SolicitudAprobacionJPResponse(
            id_solicitud=nueva_solicitud.id_solicitud,
            id_propuesta=nueva_solicitud.id_propuesta,
            id_usuario_generador=nueva_solicitud.id_usuario_generador,
            id_usuario_receptor=nueva_solicitud.id_usuario_receptor,
            aceptado_por_responsable=nueva_solicitud.aceptado_por_responsable,
            tipo_solicitud=nueva_solicitud.tipo_solicitud,
            valor_solicitud=nueva_solicitud.valor_solicitud,
            comentario=nueva_solicitud.comentario,
            creado_en=nueva_solicitud.creado_en,
            abierta=nueva_solicitud.abierta
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando solicitud de aprobación JP para subdirector: {str(e)}"
        )
