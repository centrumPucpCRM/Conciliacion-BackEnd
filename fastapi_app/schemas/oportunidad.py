from pydantic import BaseModel
class Oportunidad(BaseModel):
    id: int
    nombre: str
    class Config:
        orm_mode = True
