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
    propuesta_id: int = Query(..., description="ID de la propuesta", alias="propuesta_id"),
    db: Session = Depends(get_db),
):
    """
    Lista las subdirecciones únicas de los programas donde el usuario tiene permisos
    en una propuesta específica.
    
    Busca programas de la propuesta donde el usuario sea:
    - Jefe de Producto (idJefeProducto)
    - Subdirector (idSubdirector)
    
    Y retorna las subdirecciones únicas de esos programas.
    
    Args:
        user_id: ID del usuario
        propuesta_id: ID de la propuesta
        db: Sesión de base de datos
        
    Returns:
        Dict con formato: {"items": [{"sub-direccion": "nombre"}, ...]}
    """
    # Inicializar servicio
    service = SubDireccionService(db)
    
    # Obtener subdirecciones según permisos del usuario en la propuesta
    subdirecciones = service.obtener_subdirecciones_por_usuario_propuesta(user_id, propuesta_id)
    
    # Formatear y retornar respuesta
    return service.formatear_respuesta(subdirecciones)

