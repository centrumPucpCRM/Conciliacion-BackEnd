from pydantic import BaseModel
from typing import Optional

class CarteraBase(BaseModel):
    nombre: str

class CarteraCreate(CarteraBase):
    pass

class Cartera(CarteraBase):
    id_cartera: int
    class Config:
        orm_mode = True
