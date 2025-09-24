from typing import List, Optional
from datetime import date
from pydantic import BaseModel


class Propuesta(BaseModel):
    id: int
    nombre: str
    class Config:
        orm_mode = True


class PropuestaListado(BaseModel):
    id: int
    nombre: str
    fechaPropuesta: Optional[date] = None
    estado: Optional[str] = None
    carteras: List[str] = []


class PropuestaListadoPage(BaseModel):
    items: List[PropuestaListado]
    total: int
    page: int
    size: int
    pages: int
