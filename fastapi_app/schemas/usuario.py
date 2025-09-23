from pydantic import BaseModel
class Usuario(BaseModel):
    id: int
    nombre: str
    correo: str
    class Config:
        orm_mode = True
