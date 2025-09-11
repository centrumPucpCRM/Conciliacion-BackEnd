from pydantic import BaseModel
from typing import Optional

class LogBase(BaseModel):
    id_solicitud: int
    id_propuesta: Optional[int]
    id_usuario_generador: Optional[int]
    id_usuario_receptor: Optional[int]
    aceptado_por_responsable: Optional[bool]
    tipo_solicitud: Optional[str]
    valor_solicitud: Optional[str]
    comentario: Optional[str]
    id_propuesta_programa: Optional[int]
    id_propuesta_oportunidad: Optional[int]
    monto_propuesto: Optional[float]
    monto_objetado: Optional[float]

class LogCreate(LogBase):
    pass

class Log(LogBase):
    id: int
    class Config:
        orm_mode = True
