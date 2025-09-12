from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SolicitudAprobacionAlumnoCreate(BaseModel):
    """Schema for creating a student edit solicitud"""
    id_propuesta: int
    id_propuesta_oportunidad: int
    id_usuario_generador: int
    id_usuario_receptor: int
    monto_propuesto: float
    monto_objetado: Optional[float]
    comentario: Optional[str] = None

class SolicitudAprobacionAlumnoResponse(BaseModel):
    """Response schema for student edit solicitudes"""
    id_solicitud: int
    id_propuesta: int
    id_propuesta_oportunidad: int
    id_usuario_generador: int
    id_usuario_receptor: int
    aceptado_por_responsable: bool
    tipo_solicitud: str
    valor_solicitud: str
    monto_propuesto: float
    monto_objetado: Optional[float]
    comentario: Optional[str] = None
    creado_en: datetime
    abierta: bool = True
    mensaje: str = "Solicitud de edición de alumno creada correctamente"

    class Config:
        orm_mode = True

class SolicitudAprobacionJPResponse(BaseModel):
    """Response schema for JP approval solicitudes"""
    id_solicitud: int
    id_propuesta: int
    id_usuario_generador: int
    id_usuario_receptor: int
    aceptado_por_responsable: bool
    tipo_solicitud: str
    valor_solicitud: str
    comentario: Optional[str] = None
    creado_en: datetime
    abierta: bool = True
    mensaje: str = "Solicitud de aprobación JP creada correctamente"
    
    class Config:
        orm_mode = True