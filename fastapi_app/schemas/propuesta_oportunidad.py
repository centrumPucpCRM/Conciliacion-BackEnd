from pydantic import BaseModel
from typing import Optional

class PropuestaOportunidadBase(BaseModel):
    id_propuesta: int
    id_oportunidad: int
    id_propuesta_programa: Optional[int]
    id_tipo_cambio: Optional[int]
    monto_propuesto: Optional[float]
    etapa_venta_propuesto: Optional[str]

class PropuestaOportunidadCreate(PropuestaOportunidadBase):
    pass

class PropuestaOportunidad(PropuestaOportunidadBase):
    id_propuesta_oportunidad: int
    class Config:
        orm_mode = True
