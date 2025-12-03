from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from datetime import date


class PeriodoVacaciones(BaseModel):
    """Modelo para un periodo de vacaciones"""
    inicio: str = Field(..., description="Fecha de inicio en formato YYYY-MM-DD")
    fin: str = Field(..., description="Fecha de fin en formato YYYY-MM-DD")


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
    periodos: Optional[List[PeriodoVacaciones]] = None

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
    periodos: Optional[List[Dict]]

    class Config:
        from_attributes = True
        orm_mode = True


class UsuarioMarketingListResponse(BaseModel):
    """Schema para respuesta de listado con paginación - Compatible con diseño de oportunidad/propuesta"""
    items: List[UsuarioMarketingResponse]
    total: int
    page: int
    size: int
    pages: int
