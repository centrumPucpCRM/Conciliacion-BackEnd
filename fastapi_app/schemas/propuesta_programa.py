from pydantic import BaseModel
from typing import Optional

class PropuestaProgramaBase(BaseModel):
    id_propuesta: int
    id_programa: int
    monto_propuesto: Optional[float]

class PropuestaProgramaCreate(PropuestaProgramaBase):
    pass

class PropuestaPrograma(PropuestaProgramaBase):
    id_propuesta_programa: int
    class Config:
        orm_mode = True
