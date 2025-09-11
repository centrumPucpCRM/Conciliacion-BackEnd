from pydantic import BaseModel
from typing import Optional

class UsuarioBase(BaseModel):
    dni: Optional[str]
    correo: str
    nombres: str
    celular: Optional[str]
    rol: str
    cartera: Optional[str]

class UsuarioCreate(UsuarioBase):
    pass

class Usuario(UsuarioBase):
    id_usuario: int
    class Config:
        orm_mode = True
