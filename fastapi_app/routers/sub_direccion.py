"""
Router para gestión de subdirecciones.
Expone los endpoints relacionados con subdirecciones y permisos de usuarios.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.sub_direccion_service import SubDireccionService

router = APIRouter(prefix="/sub-direccion", tags=["Sub-Dirección"])


@router.get("/listar/usuario")
def listar_por_usuario(
    user_id: int = Query(..., description="ID del usuario", alias="user_id"),
    db: Session = Depends(get_db),
):
    """
    Lista las subdirecciones únicas asociadas a un usuario específico.
    
    Sistema de permisos en 3 niveles:
    - Nivel 1: Usuarios con acceso total (admin, daf.supervisor, daf.subdirector)
      ven todas las subdirecciones del sistema.
    - Nivel 2: Usuarios con subdirecciones específicas
      ven solo sus subdirecciones asignadas.
    - Nivel 3: Otros usuarios ven subdirecciones donde son jefes de producto.
    
    Args:
        user_id: ID del usuario
        db: Sesión de base de datos
        
    Returns:
        Dict con formato: {"items": [{"sub-direccion": "nombre"}, ...]}
    """
    # Inicializar servicio
    service = SubDireccionService(db)
    
    # Obtener subdirecciones según permisos del usuario
    subdirecciones = service.obtener_subdirecciones_por_usuario(user_id)
    
    # Formatear y retornar respuesta
    return service.formatear_respuesta(subdirecciones)

