
from pydantic import model_validator

# Schemas para entrada de SolicitudAlumno y SolicitudPrograma
class SolicitudAlumnoIn(BaseModel):
    tipo_solicitud: str
    idUsuarioGenerador: int
    idOportunidad: int
    montoPropuesto: float = None
    montoObjetado: float = None

    @model_validator(mode="after")
    def validar_campos(self):
        if self.tipo_solicitud == "AGREGAR_ALUMNO":
            if self.montoPropuesto is None or self.montoObjetado is None:
                raise ValueError("montoPropuesto y montoObjetado son requeridos para AGREGAR_ALUMNO")
        return self

class SolicitudProgramaIn(BaseModel):
    tipo_solicitud: str
    idUsuarioGenerador: int
    idPrograma: int

    @model_validator(mode="after")
    def validar_campos(self):
        if self.tipo_solicitud == "EXCLUSION_PROGRAMA":
            if self.idPrograma is None:
                raise ValueError("idPrograma es requerido para EXCLUSION_PROGRAMA")
        elif self.tipo_solicitud == "FECHA_CAMBIADA":
            # Pendiente, no implementado
            pass
        return self

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

class Solicitud(BaseModel):
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
