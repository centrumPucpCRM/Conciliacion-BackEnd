from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Literal
from datetime import date, datetime
from enum import Enum


class EstadoVacaciones(str, Enum):
    """Estados permitidos para periodos y vacaciones extras"""
    PLANIFICADO = "planificado"
    ACTIVO = "activo"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"


class PeriodoVacaciones(BaseModel):
    """Modelo para un periodo de vacaciones con estado y observación"""
    inicio: str = Field(..., description="Fecha de inicio en formato YYYY-MM-DD")
    fin: str = Field(..., description="Fecha de fin en formato YYYY-MM-DD")
    estado: Optional[Literal["planificado", "activo", "finalizado", "cancelado"]] = Field(
        None, 
        description="Estado del periodo. Se calcula automáticamente si no se proporciona"
    )
    observacion: Optional[str] = Field(
        None, 
        description="Observación sobre el periodo. Obligatoria para cambios de estado o fechas"
    )
    
    @validator('inicio', 'fin')
    def validate_date_format(cls, v):
        """Valida que la fecha tenga formato YYYY-MM-DD"""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('La fecha debe tener formato YYYY-MM-DD')


class VacacionExtra(BaseModel):
    """Modelo para una vacación extra (médico u otros)"""
    inicio: str = Field(..., description="Fecha de inicio en formato YYYY-MM-DD")
    fin: str = Field(..., description="Fecha de fin en formato YYYY-MM-DD")
    estado: Optional[Literal["planificado", "activo", "finalizado", "cancelado"]] = Field(
        None,
        description="Estado de la vacación extra. Se calcula automáticamente si no se proporciona"
    )
    observacion: Optional[str] = Field(
        None,
        description="Observación sobre la vacación extra. Obligatoria para cambios de estado o fechas"
    )
    
    @validator('inicio', 'fin')
    def validate_date_format(cls, v):
        """Valida que la fecha tenga formato YYYY-MM-DD"""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('La fecha debe tener formato YYYY-MM-DD')


class VacacionesExtras(BaseModel):
    """Modelo para vacaciones extras organizadas por tipo"""
    medico: Optional[List[VacacionExtra]] = Field(default_factory=list, description="Vacaciones por motivo médico")
    otros: Optional[List[VacacionExtra]] = Field(default_factory=list, description="Otras vacaciones extras")


class UsuarioMarketingCreate(BaseModel):
    """Schema para crear un usuario de marketing"""
    nombre: str = Field(..., min_length=1, max_length=150)
    party_id: int = Field(..., gt=0)
    party_number: str = Field(..., min_length=1, max_length=50)
    correo: str = Field(..., min_length=1, max_length=150)
    vacaciones: bool = Field(default=False)
    id_usuario: Optional[int] = Field(None, gt=0)
    dias_pendientes: Optional[Dict[str, int]] = Field(None, description="Ejemplo: {'2025': 66, '2026': 93}")
    periodos: Optional[List[PeriodoVacaciones]] = Field(None, description="Lista de periodos de vacaciones")

    @validator('correo')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Correo debe tener formato válido')
        return v.lower()


class UsuarioMarketingUpdate(BaseModel):
    """Schema para actualizar un usuario de marketing"""
    nombre: Optional[str] = Field(None, min_length=1, max_length=150)
    party_id: Optional[int] = Field(None, gt=0)
    party_number: Optional[str] = Field(None, min_length=1, max_length=50)
    correo: Optional[str] = Field(None, min_length=1, max_length=150)
    vacaciones: Optional[bool] = None
    id_usuario: Optional[int] = Field(None, gt=0)
    dias_pendientes: Optional[Dict[str, int]] = None
    periodos: Optional[List[PeriodoVacaciones]] = Field(None, description="Lista de periodos de vacaciones con estado y observación")
    vacaciones_extras: Optional[VacacionesExtras] = Field(None, description="Vacaciones extras organizadas por tipo")

    @validator('correo')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Correo debe tener formato válido')
        return v.lower() if v else v


class UsuarioMarketingResponse(BaseModel):
    """Schema para respuesta de usuario de marketing"""
    id: int
    nombre: str
    party_id: int
    party_number: str
    correo: str
    vacaciones: bool
    id_usuario: Optional[int]
    dias_pendientes: Optional[Dict[str, int]]
    periodos: Optional[List[Dict]] = Field(default_factory=list, description="Lista de periodos de vacaciones con estado y observación")
    vacaciones_extras: Optional[Dict[str, List[Dict]]] = Field(
        default_factory=dict,
        description="Vacaciones extras organizadas por tipo: {'medico': [...], 'otros': [...]}"
    )

    class Config:
        from_attributes = True


class UsuarioMarketingListResponse(BaseModel):
    """Schema para respuesta de listado con paginación - Compatible con diseño de oportunidad/propuesta"""
    items: List[UsuarioMarketingResponse]
    total: int
    page: int
    size: int
    pages: int


class EventoCalendarioVacaciones(BaseModel):
    """Schema para un evento de vacaciones en el calendario"""
    id_usuario: int
    nombre: str
    correo: str
    party_number: str
    tipo: Literal["periodo", "medico", "otros"]
    inicio: str
    fin: str
    estado: Literal["planificado", "activo", "finalizado", "cancelado"]
    observacion: Optional[str] = None
    dias: int  # Número de días del periodo


class CalendarioVacacionesResponse(BaseModel):
    """Schema para respuesta del calendario de vacaciones"""
    eventos: List[EventoCalendarioVacaciones]
    total: int
    fecha_inicio: str
    fecha_fin: str
