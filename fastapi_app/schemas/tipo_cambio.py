from pydantic import BaseModel
from typing import Optional

class TipoCambioBase(BaseModel):
    moneda_origen: str
    moneda_target: str
    equivalencia: float
    fecha_tipo_cambio: Optional[str]

class TipoCambioCreate(TipoCambioBase):
    pass

class TipoCambio(TipoCambioBase):
    id_tipo_cambio: int
    class Config:
        orm_mode = True
