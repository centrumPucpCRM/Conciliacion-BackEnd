from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from ..database import SessionLocal
from ..models.rol_permiso import Rol
from ..models.usuario import Usuario
from ..models.cartera import Cartera
from pydantic import BaseModel

router = APIRouter(
    prefix="/roles-usuarios-carteras",
    tags=["Roles-Usuarios-Carteras"],
    responses={404: {"description": "No encontrado"}},
)

# Dependencia para obtener la sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Esquema para las carteras
class CarteraSchema(BaseModel):
    id_cartera: int
    nombre: str
    descripcion: Optional[str] = None
    
    class Config:
        orm_mode = True

# Esquema para los usuarios
class UsuarioSchema(BaseModel):
    id_usuario: int
    dni: Optional[str] = None
    correo: str
    nombres: str
    celular: Optional[str] = None
    carteras: List[CarteraSchema]
    
    class Config:
        orm_mode = True

# Esquema para los roles con sus usuarios asociados
class RolUsuariosSchema(BaseModel):
    id_rol: int
    nombre: str
    usuarios: List[UsuarioSchema]
    
    class Config:
        orm_mode = True

# Endpoint para obtener todos los roles con sus usuarios y carteras asociadas
@router.get("/", response_model=List[RolUsuariosSchema])
def obtener_roles_usuarios_carteras(db: Session = Depends(get_db)):
    # Obtenemos todos los roles con sus usuarios asociados y las carteras de cada usuario
    roles = db.query(Rol).options(
        joinedload(Rol.usuarios).joinedload(Usuario.carteras)
    ).all()
    
    if not roles:
        raise HTTPException(status_code=404, detail="No se encontraron roles")
    
    # Aquí realizamos una conversión manual para manejar valores nulos correctamente
    result = []
    for rol in roles:
        rol_dict = {
            "id_rol": rol.id_rol,
            "nombre": rol.nombre,
            "usuarios": []
        }
        
        for usuario in rol.usuarios:
            usuario_dict = {
                "id_usuario": usuario.id_usuario,
                "dni": usuario.dni,
                "correo": usuario.correo,
                "nombres": usuario.nombres,
                "celular": usuario.celular,
                "carteras": []
            }
            
            for cartera in usuario.carteras:
                cartera_dict = {
                    "id_cartera": cartera.id_cartera,
                    "nombre": cartera.nombre,
                    "descripcion": cartera.descripcion
                }
                usuario_dict["carteras"].append(cartera_dict)
                
            rol_dict["usuarios"].append(usuario_dict)
            
        result.append(rol_dict)
    
    return result
