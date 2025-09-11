from pydantic import BaseModel
from typing import Optional

class ConciliacionBase(BaseModel):
    fecha: str
    estado_conciliacion: str

class ConciliacionCreate(ConciliacionBase):
    pass

class Conciliacion(ConciliacionBase):
    id_conciliacion: int
    class Config:
        orm_mode = True
