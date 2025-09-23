from pydantic import BaseModel
class Propuesta(BaseModel):
    id: int
    nombre: str
    class Config:
        orm_mode = True
