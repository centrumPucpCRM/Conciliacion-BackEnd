from pydantic import BaseModel
class Conciliacion(BaseModel):
    id: int
    fechaConciliacion: str
    class Config:
        orm_mode = True
