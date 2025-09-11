from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.rol_permiso import Rol
from pydantic import BaseModel
from typing import List

router = APIRouter(
    prefix="/roles",
    tags=["Roles"],
    responses={404: {"description": "No encontrado"}},
)

# Dependencia para obtener la sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Esquema para devolver roles
class RolSchema(BaseModel):
    id_rol: int
    nombre: str
    
    class Config:
        from_attributes = True

# Endpoint para obtener todos los roles
@router.get("/", response_model=List[RolSchema])
def obtener_roles(db: Session = Depends(get_db)):
    roles = db.query(Rol).all()
    return roles
