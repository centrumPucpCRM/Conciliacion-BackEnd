"""
Router (controller) for Vendedores bounded context.
This is the interface layer that handles HTTP requests and responses.
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
from pydantic import BaseModel, Field

from ..application.services import VendedorService
from ..infrastructure.adapters import VendedorRepositoryAdapter, VacacionServiceAdapter


# Configuration - External API URLs
VENDOR_API_URL = "https://qkb7scw3iamis77inurjjggjee0mrivx.lambda-url.us-east-1.on.aws/"
VACATION_API_URL = "https://s5dmd2j4ext5tgbrgbcxlkpvfm0vkxjv.lambda-url.us-east-1.on.aws/"


# Initialize adapters and service
_vendedor_repository = VendedorRepositoryAdapter(VENDOR_API_URL)
_vacacion_service = VacacionServiceAdapter(VACATION_API_URL)
_vendedor_service = VendedorService(_vendedor_repository, _vacacion_service)


# Request/Response schemas
class ActualizarVacacionesRequest(BaseModel):
    """Schema for vacation status update request."""
    resource_user_id: str = Field(..., description="Party number del vendedor")
    CTREnVacaciones_c: bool = Field(..., description="True si está en vacaciones, False si no")


# Router setup
router = APIRouter(
    prefix="/vendedores",
    tags=["Vendedores"]
)


@router.get("/", summary="Listar todos los vendedores")
async def listar_vendedores() -> list[Dict[str, Any]]:
    """
    Endpoint para obtener la lista de todos los vendedores.
    
    Returns:
        list[Dict[str, Any]]: Lista de vendedores con sus datos
        
    Raises:
        HTTPException: Si hay un error al obtener los datos
    """
    try:
        vendedores = await _vendedor_service.listar_vendedores()
        return vendedores
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener vendedores: {str(e)}"
        )


@router.patch("/vacaciones", summary="Actualizar estado de vacaciones")
async def actualizar_vacaciones(
    request: ActualizarVacacionesRequest = Body(...)
) -> Dict[str, Any]:
    """
    Endpoint para actualizar el estado de vacaciones de un vendedor.
    Este endpoint realiza un PATCH a la API externa para cambiar el estado.
    
    Args:
        request: Datos de la solicitud con party_number y estado de vacaciones
        
    Returns:
        Dict[str, Any]: Respuesta de la operación
        
    Raises:
        HTTPException: Si hay un error al actualizar el estado
    """
    try:
        result = await _vendedor_service.actualizar_vacaciones(
            party_number=request.resource_user_id,
            en_vacaciones=request.CTREnVacaciones_c
        )
        return {
            "success": True,
            "message": f"Estado de vacaciones actualizado correctamente",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar estado de vacaciones: {str(e)}"
        )

