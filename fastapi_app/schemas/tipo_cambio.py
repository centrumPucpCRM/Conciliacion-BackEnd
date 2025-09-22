from pydantic import BaseModel
class TipoCambio(BaseModel):
    id: int
    valor: float
    class Config:
        orm_mode = True
