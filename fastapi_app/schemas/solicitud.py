from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SolicitudBase(BaseModel):
    id_propuesta: int
    id_usuario_generador: int
    id_usuario_receptor: int
    aceptado_por_responsable: Optional[bool]
    tipo_solicitud: str
    valor_solicitud: str
    comentario: Optional[str]

class SolicitudCreate(SolicitudBase):
    pass

class Solicitud(SolicitudBase):
    id_solicitud: int
    creado_en: Optional[datetime]
    class Config:
        orm_mode = True

# New schema for creating a client solicitud with propuesta oportunidad
class SolicitudPropuestaOportunidadInfo(BaseModel):
    id_propuesta_oportunidad: int
    monto_propuesto: Optional[float] = None
    monto_objetado: Optional[float] = None

class SolicitudClienteCreate(BaseModel):
    """Schema for creating a solicitud with client information"""
    id_propuesta: int
    id_usuario_generador: int
    id_usuario_receptor: int
    tipo_solicitud: str
    comentario: Optional[str] = None
    propuestas_oportunidades: List[SolicitudPropuestaOportunidadInfo]
    
    class Config:
        orm_mode = True
        
# Schema for creating solicitud with propuesta programa
class SolicitudPropuestaProgramaCreate(BaseModel):
    """Schema for creating a solicitud for propuesta programa exclusion"""
    id_propuesta: int
    id_propuesta_programa: int
    id_usuario_generador: int
    id_usuario_receptor: int
    comentario: Optional[str] = None
    
    class Config:
        orm_mode = True

class SolicitudClienteResponse(BaseModel):
    """Response schema after creating a client solicitud"""
    id_solicitud: int
    id_propuesta: int
    id_usuario_generador: int
    id_usuario_receptor: int
    aceptado_por_responsable: bool
    tipo_solicitud: str
    valor_solicitud: str
    comentario: Optional[str] = None
    creado_en: datetime
    abierta: bool = False
    mensaje: str = "Solicitud de cliente creada correctamente"
    
    class Config:
        orm_mode = True
        
class SolicitudPropuestaProgramaResponse(BaseModel):
    """Response schema after creating a propuesta programa exclusion solicitud"""
    id_solicitud: int
    id_propuesta: int
    id_propuesta_programa: int
    id_usuario_generador: int
    id_usuario_receptor: int
    aceptado_por_responsable: bool
    tipo_solicitud: str
    valor_solicitud: str
    comentario: Optional[str] = None
    creado_en: datetime
    abierta: bool = True
    mensaje: str = "Solicitud de exclusión de programa creada correctamente"
    
    class Config:
        orm_mode = True
