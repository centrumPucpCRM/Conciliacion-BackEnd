from pydantic import BaseModel
class Solicitud(BaseModel):
    id: int
    descripcion: str
    class Config:
        orm_mode = True
