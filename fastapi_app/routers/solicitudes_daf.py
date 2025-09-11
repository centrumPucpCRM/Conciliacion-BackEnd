from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from ..database import get_db
from ..models.solicitud import Solicitud, TIPO_SOLICITUD_VALORES, VALOR_SOLICITUD_VALORES
from ..models.solicitud_propuesta_oportunidad import SolicitudPropuestaOportunidad
from ..models.solicitud_propuesta_programa import SolicitudPropuestaPrograma as SolicitudPPModel
from ..schemas.solicitudes_daf import SolicitudAlumnoDafMontoCreate, SolicitudAlumnoDafMontoResponse
from ..schemas.solicitud import SolicitudPropuestaProgramaCreate, SolicitudPropuestaProgramaResponse
import datetime

router = APIRouter(
    prefix="/solicitudes/daf/oportunidad/monto",
    tags=["Solicitudes DAF"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=SolicitudAlumnoDafMontoResponse)
def create_solicitud_alumno_daf_monto(
    solicitud_data: SolicitudAlumnoDafMontoCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new request to change a student's amount by DAF
    
    This endpoint creates entries in both the Solicitud and SolicitudPropuestaOportunidad tables
    """
    try:
        # Create the main Solicitud record
        nueva_solicitud = Solicitud(
            id_propuesta=solicitud_data.id_propuesta,
            id_usuario_generador=solicitud_data.id_usuario_generador,
            id_usuario_receptor=solicitud_data.id_usuario_receptor,
            aceptado_por_responsable=False,  # By default is False as requested
            tipo_solicitud="EDICION_ALUMNO",  # As specified, this is for student editing
            valor_solicitud="PENDIENTE",  # Default value, to be updated by the approver
            comentario=solicitud_data.comentario if solicitud_data.comentario else "Cambio de monto propuesto por DAF",
            creado_en=datetime.datetime.now()
        )
        
        db.add(nueva_solicitud)
        db.flush()  # This gives us the id_solicitud without committing
        
        # Create the SolicitudPropuestaOportunidad record linked to the main solicitud
        nueva_solicitud_oportunidad = SolicitudPropuestaOportunidad(
            id_solicitud=nueva_solicitud.id_solicitud,
            id_propuesta_oportunidad=solicitud_data.id_propuesta_oportunidad,
            monto_propuesto=solicitud_data.monto_propuesto,
            monto_objetado=solicitud_data.monto_objetado
        )
        
        db.add(nueva_solicitud_oportunidad)
        db.commit()
        db.refresh(nueva_solicitud)
        db.refresh(nueva_solicitud_oportunidad)
        
        # Create the response with all required fields
        return SolicitudAlumnoDafMontoResponse(
            id_solicitud=nueva_solicitud.id_solicitud,
            id_propuesta=nueva_solicitud.id_propuesta,
            id_propuesta_oportunidad=nueva_solicitud_oportunidad.id_propuesta_oportunidad,
            id_usuario_generador=nueva_solicitud.id_usuario_generador,
            id_usuario_receptor=nueva_solicitud.id_usuario_receptor,
            aceptado_por_responsable=nueva_solicitud.aceptado_por_responsable,
            tipo_solicitud=nueva_solicitud.tipo_solicitud,
            valor_solicitud=nueva_solicitud.valor_solicitud,
            comentario=nueva_solicitud.comentario,
            monto_propuesto=nueva_solicitud_oportunidad.monto_propuesto,
            monto_objetado=nueva_solicitud_oportunidad.monto_objetado
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando solicitud: {str(e)}"
        )

# DAF solicitudes router for program exclusion
programa_router = APIRouter(
    prefix="/solicitudes/daf/programa",
    tags=["Solicitudes DAF"],
    responses={404: {"description": "Not found"}}
)

# Enhanced schema for response with propuesta oportunidades
class SolicitudOportunidadDetail(BaseModel):
    id: int
    id_propuesta_oportunidad: int
    monto_propuesto: Optional[float] = None
    monto_objetado: Optional[float] = None
    
    class Config:
        orm_mode = True
        
class SolicitudClienteDetailResponse(BaseModel):
    id_solicitud: int
    id_propuesta: int
    id_usuario_generador: int
    id_usuario_receptor: int
    aceptado_por_responsable: bool
    tipo_solicitud: str
    valor_solicitud: str
    comentario: Optional[str]
    creado_en: Optional[datetime.datetime]
    abierta: Optional[bool]
    propuestas_oportunidades: List[SolicitudOportunidadDetail] = []
    
    class Config:
        orm_mode = True

@programa_router.post("/exclusion", response_model=SolicitudPropuestaProgramaResponse)
def create_solicitud_exclusion_programa(
    solicitud_data: SolicitudPropuestaProgramaCreate, 
    db: Session = Depends(get_db)
):
    """
    Create a solicitud for propuesta programa exclusion
    
    This endpoint creates a solicitud with EXCLUSION_PROGRAMA type and links it to a propuesta_programa
    """
    try:
        # Create the main Solicitud record
        nueva_solicitud = Solicitud(
            id_propuesta=solicitud_data.id_propuesta,
            id_usuario_generador=solicitud_data.id_usuario_generador,
            id_usuario_receptor=solicitud_data.id_usuario_receptor,
            aceptado_por_responsable=False,  # By default is False
            tipo_solicitud="EXCLUSION_PROGRAMA",  # Fixed value as requested
            valor_solicitud="PENDIENTE",  # Valor por defecto en lugar de None
            comentario=solicitud_data.comentario if solicitud_data.comentario else "Solicitud de exclusión de programa",
            creado_en=datetime.datetime.now(),
            abierta=True  # Set to True as requested
        )
        
        db.add(nueva_solicitud)
        db.flush()  # This gives us the id_solicitud without committing
        
        # Create the SolicitudPropuestaPrograma record linked to the main solicitud
        nueva_solicitud_programa = SolicitudPPModel(
            id_solicitud=nueva_solicitud.id_solicitud,
            id_propuesta_programa=solicitud_data.id_propuesta_programa
        )
        
        db.add(nueva_solicitud_programa)
        db.commit()
        db.refresh(nueva_solicitud)
        db.refresh(nueva_solicitud_programa)
        
        # Create the response with all required fields
        return SolicitudPropuestaProgramaResponse(
            id_solicitud=nueva_solicitud.id_solicitud,
            id_propuesta=nueva_solicitud.id_propuesta,
            id_propuesta_programa=nueva_solicitud_programa.id_propuesta_programa,
            id_usuario_generador=nueva_solicitud.id_usuario_generador,
            id_usuario_receptor=nueva_solicitud.id_usuario_receptor,
            aceptado_por_responsable=nueva_solicitud.aceptado_por_responsable,
            tipo_solicitud=nueva_solicitud.tipo_solicitud,
            valor_solicitud=nueva_solicitud.valor_solicitud or "",  # Handle null value
            comentario=nueva_solicitud.comentario,
            creado_en=nueva_solicitud.creado_en,
            abierta=nueva_solicitud.abierta
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando solicitud de exclusión de programa: {str(e)}"
        )
