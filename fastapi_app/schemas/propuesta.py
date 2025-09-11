from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CambioEstadoPropuestaResponse(BaseModel):
    """Respuesta para operaciones de cambio de estado de propuesta"""
    id_propuesta: int
    estado_propuesta: str
    mensaje: str
    
    class Config:
        from_attributes = True


class PropuestaBase(BaseModel):
    id_conciliacion: Optional[int]
    nombre: str
    descripcion: Optional[str]
    tipo_propuesta: str
    estado_propuesta: str
    estado: Optional[str] = None  # Alias para frontend
    carteras: List[str] = []

class PropuestaCreate(PropuestaBase):
    pass

class Propuesta(PropuestaBase):
    id_propuesta: int
    creado_en: Optional[datetime]
    estado: Optional[str] = None
    carteras: List[str] = []
    class Config:
        from_attributes = True  # Nuevo nombre para orm_mode en Pydantic v2
    
    @classmethod
    def from_orm(cls, obj):
        data = super().from_orm(obj)
        # Mapear estado
        if data.estado_propuesta == "CANCELADO":
            data.estado = "CANCELADO"
        elif data.estado_propuesta == "CONCILIADA":
            data.estado = "CONCILIADO"
        else:
            data.estado = "ACTIVO"
        return data
