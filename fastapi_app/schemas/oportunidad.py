from typing import Optional
from pydantic import BaseModel


class Oportunidad(BaseModel):
    id: int
    nombre: str
    optyNumber: Optional[str] = None
    optyId: Optional[str] = None

    class Config:
        orm_mode = True
