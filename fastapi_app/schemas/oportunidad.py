from pydantic import BaseModel
from typing import Optional

class OportunidadBase(BaseModel):
    id_programa: int
    nombre: str
    etapa_venta: Optional[str]
    contacto: Optional[bool]
    monto: Optional[float]
    posible_atipico: Optional[bool]
    becado: Optional[bool]
    conciliado: Optional[bool]

class OportunidadCreate(OportunidadBase):
    pass

class Oportunidad(OportunidadBase):
    id_oportunidad: int
    class Config:
        orm_mode = True
