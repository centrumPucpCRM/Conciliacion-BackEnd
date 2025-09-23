from pydantic import BaseModel
class Cartera(BaseModel):
    id: int
    nombre: str
    class Config:
        orm_mode = True
