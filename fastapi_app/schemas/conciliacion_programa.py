from pydantic import BaseModel
from typing import Optional

class ConciliacionProgramaBase(BaseModel):
    id_conciliacion: int
    pago_proyectado: Optional[float]

class ConciliacionProgramaCreate(ConciliacionProgramaBase):
    pass

class ConciliacionPrograma(ConciliacionProgramaBase):
    id_conciliacion_programa: int
    class Config:
        orm_mode = True
