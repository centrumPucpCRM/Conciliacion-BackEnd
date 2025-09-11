from pydantic import BaseModel
from typing import Optional

class RolBase(BaseModel):
    nombre: str

class RolCreate(RolBase):
    pass

class Rol(RolBase):
    id_rol: int
    class Config:
        orm_mode = True

class PermisoBase(BaseModel):
    descripcion: str

class PermisoCreate(PermisoBase):
    pass

class Permiso(PermisoBase):
    id_permiso: int
    class Config:
        orm_mode = True

class RolPermisoBase(BaseModel):
    rol: str
    permiso: str

class RolPermisoCreate(RolPermisoBase):
    pass

class RolPermiso(RolPermisoBase):
    id: int
    class Config:
        orm_mode = True
