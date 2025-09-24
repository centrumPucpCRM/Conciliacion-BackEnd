
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, date

class SolicitudOportunidad(BaseModel):
    idOportunidad: int
    montoPropuesto: Optional[float]
    montoObjetado: Optional[float]

class SolicitudPrograma(BaseModel):
    idPrograma: int
    fechaInaguracionPropuesta: Optional[date]
    fechaInaguracionObjetada: Optional[date]

class SolicitudOut(BaseModel):
    id: int
    idUsuarioReceptor: Optional[int]
    idUsuarioGenerador: Optional[int]
    abierta: Optional[bool]
    tipoSolicitud: Optional[str]
    valorSolicitud: Optional[str]
    idPropuesta: Optional[int]
    comentario: Optional[str]
    creadoEn: Optional[datetime]
    oportunidad: Optional[SolicitudOportunidad]
    programa: Optional[SolicitudPrograma]

    class Config:
        orm_mode = True
