from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SolicitudAlumnoDafMontoCreate(BaseModel):
    """
    Schema for creating a request to change a student's amount by DAF
    Only include fields that need to be sent from frontend
    """
    id_propuesta: int
    id_propuesta_oportunidad: int
    id_usuario_generador: int
    id_usuario_receptor: int
    monto_propuesto: float
    monto_objetado: Optional[float] = None
    comentario: Optional[str] = None
    
    class Config:
        orm_mode = True
        
class SolicitudAlumnoDafMontoResponse(BaseModel):
    """
    Response schema after creating a DAF student amount change request
    Include all fields that should be visible in response
    """
    id_solicitud: int
    id_propuesta_oportunidad: int
    monto_propuesto: float
    monto_objetado: Optional[float] = None
    id_propuesta: int
    id_usuario_generador: int
    id_usuario_receptor: int
    aceptado_por_responsable: bool  # Should be visible in response
    tipo_solicitud: str  # Default is "EDICION_ALUMNO" but should be visible
    valor_solicitud: str  # Should be set to "ACEPTADO" initially
    comentario: Optional[str] = None
    creado_en: Optional[datetime] = None
    monto_propuesto: float
    monto_objetado: Optional[float] = None
    mensaje: str = "Solicitud de cambio de monto creada correctamente"
    
    class Config:
        orm_mode = True
