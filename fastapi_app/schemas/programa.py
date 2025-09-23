from pydantic import BaseModel
class Programa(BaseModel):
    id: int
    nombre: str
    class Config:
        orm_mode = True
