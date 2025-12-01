"""
Ejemplo de router de conciliaciones usando arquitectura hexagonal con DDD.

Este router muestra cómo usar el bounded context de JWT Authentication
siguiendo principios de arquitectura hexagonal y DDD.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi_app.database import get_db
from fastapi_app.bounded_contexts.jwt_auth.interface.dependencies import (
    get_current_user,
    get_current_user_id_str,
    get_current_user_email_str
)
from fastapi_app.bounded_contexts.jwt_auth.domain.entities import AuthenticatedUser

router = APIRouter(prefix="/conciliacion", tags=["Conciliacion JWT (Hexagonal)"])


@router.get("/listar")
async def listar_conciliaciones(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista conciliaciones del usuario autenticado.
    
    Este endpoint usa el bounded context de JWT Authentication con arquitectura hexagonal.
    El usuario autenticado se obtiene mediante la dependencia get_current_user.
    
    Args:
        user: Usuario autenticado (entidad de dominio)
        db: Sesión de base de datos
        
    Returns:
        Lista de conciliaciones del usuario
    """
    user_id = str(user.user_id)
    email = str(user.email)
    
    # Ejemplo: Aquí iría tu lógica para obtener conciliaciones
    # conciliaciones = db.query(Conciliacion).filter(
    #     Conciliacion.user_id == user_id
    # ).all()
    
    return {
        "message": "Endpoint protegido con JWT (Arquitectura Hexagonal + DDD)",
        "user": user.to_dict(),
        "conciliaciones": [
            {
                "id": 1,
                "descripcion": "Conciliación ejemplo 1",
                "usuario_id": user_id,
                "usuario_email": email
            },
            {
                "id": 2,
                "descripcion": "Conciliación ejemplo 2",
                "usuario_id": user_id,
                "usuario_email": email
            }
        ]
    }


@router.get("/{conciliacion_id}")
async def obtener_conciliacion(
    conciliacion_id: int,
    user_id: str = Depends(get_current_user_id_str),
    db: Session = Depends(get_db)
):
    """
    Obtiene una conciliación específica del usuario autenticado.
    
    Este endpoint muestra cómo usar get_current_user_id_str para obtener
    solo el ID del usuario como string.
    
    Args:
        conciliacion_id: ID de la conciliación
        user_id: ID del usuario autenticado (string)
        db: Sesión de base de datos
        
    Returns:
        Detalles de la conciliación
    """
    # Ejemplo: Aquí iría tu lógica
    # conciliacion = db.query(Conciliacion).filter(
    #     Conciliacion.id == conciliacion_id,
    #     Conciliacion.user_id == user_id
    # ).first()
    
    return {
        "id": conciliacion_id,
        "user_id": user_id,
        "descripcion": f"Conciliación {conciliacion_id} del usuario {user_id}"
    }


@router.post("/crear")
async def crear_conciliacion(
    datos: dict,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crea una nueva conciliación para el usuario autenticado.
    
    Este endpoint muestra cómo usar la entidad AuthenticatedUser completa
    para acceder a toda la información del usuario.
    
    Args:
        datos: Datos de la conciliación a crear
        user: Usuario autenticado (entidad de dominio)
        db: Sesión de base de datos
        
    Returns:
        Conciliación creada
    """
    user_id = str(user.user_id)
    email = str(user.email)
    
    # Ejemplo: Aquí iría tu lógica para crear la conciliación
    # nueva_conciliacion = Conciliacion(
    #     user_id=user_id,
    #     user_email=email,
    #     ...datos...
    # )
    # db.add(nueva_conciliacion)
    # db.commit()
    
    return {
        "message": "Conciliación creada",
        "user": user.to_dict(),
        "datos": datos
    }

