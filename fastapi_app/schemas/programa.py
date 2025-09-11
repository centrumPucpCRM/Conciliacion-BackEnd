from pydantic import BaseModel
from typing import Optional

class ProgramaBase(BaseModel):
    nombre: str

class ProgramaCreate(ProgramaBase):
    pass

class Programa(ProgramaBase):
    id_programa: int
    class Config:
        orm_mode = True
