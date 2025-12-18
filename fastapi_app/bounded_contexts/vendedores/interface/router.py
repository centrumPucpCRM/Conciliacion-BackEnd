"""
Router (controller) for Vendedores bounded context.
This is the interface layer that handles HTTP requests and responses.
"""
from fastapi import APIRouter, HTTPException, Body, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel, Field
import logging
import httpx

from ..application.services import VendedorService
from ..infrastructure.adapters import VendedorRepositoryAdapter, VacacionServiceAdapter
from fastapi_app.database import get_db
from fastapi_app.models.usuario_marketing import UsuarioMarketing

logger = logging.getLogger(__name__)


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


async def sincronizar_usuario_marketing_desde_servicio(
    db: Session,
    party_number: str = None
) -> Dict[str, Any]:
    """
    Sincroniza los datos de usuario_marketing desde el servicio externo de vendedores.
    Si se proporciona party_number, solo sincroniza ese usuario específico.
    Si no, sincroniza todos los usuarios.
    
    Args:
        db: Sesión de base de datos
        party_number: Opcional. Party number específico a sincronizar
        
    Returns:
        Dict con estadísticas de la sincronización
    """
    try:
        logger.info(f"Sincronizando usuario_marketing desde servicio externo (party_number: {party_number or 'todos'})")
        
        # Obtener datos del servicio externo
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(VENDOR_API_URL)
            response.raise_for_status()
            data = response.json()
        
        # El servicio Lambda devuelve directamente una lista
        if isinstance(data, list):
            vendedores = data
        elif isinstance(data, dict) and 'items' in data:
            vendedores = data.get('items', [])
        else:
            raise ValueError("Formato de respuesta inválido del servicio de vendedores")
        
        # Filtrar por party_number si se especificó
        if party_number:
            vendedores = [v for v in vendedores if v.get("ResourcePartyNumber") == party_number]
            if not vendedores:
                logger.warning(f"No se encontró vendedor con party_number: {party_number}")
                return {
                    "creados": 0,
                    "actualizados": 0,
                    "errores": 0
                }
        
        # Procesar vendedores
        creados = 0
        actualizados = 0
        errores = 0
        
        for vendedor_data in vendedores:
            try:
                nombre = vendedor_data.get("PartyName", "")
                party_id = vendedor_data.get("ResourcePartyId")
                resource_party_number = vendedor_data.get("ResourcePartyNumber", "")
                correo = vendedor_data.get("ResourceEmail", "")
                vacaciones_raw = vendedor_data.get("CTREnVacaciones_c")
                vacaciones = bool(vacaciones_raw) if vacaciones_raw is not None else False
                
                # Validar campos obligatorios
                if not nombre or not party_id or not resource_party_number or not correo:
                    errores += 1
                    logger.warning(f"Vendedor con datos incompletos: {resource_party_number}")
                    continue
                
                # Convertir party_id a entero
                try:
                    party_id = int(party_id)
                except (ValueError, TypeError):
                    errores += 1
                    logger.warning(f"party_id inválido para {resource_party_number}: {party_id}")
                    continue
                
                # Buscar usuario existente
                usuario_marketing = db.query(UsuarioMarketing).filter(
                    UsuarioMarketing.party_id == party_id,
                    UsuarioMarketing.party_number == resource_party_number
                ).first()
                
                if usuario_marketing:
                    # Actualizar existente
                    usuario_marketing.nombre = nombre
                    usuario_marketing.correo = correo
                    usuario_marketing.vacaciones = vacaciones
                    actualizados += 1
                else:
                    # Crear nuevo
                    nuevo_usuario = UsuarioMarketing(
                        nombre=nombre,
                        party_id=party_id,
                        party_number=resource_party_number,
                        correo=correo,
                        vacaciones=vacaciones
                    )
                    db.add(nuevo_usuario)
                    creados += 1
                
            except Exception as e:
                errores += 1
                logger.error(f"Error procesando vendedor {vendedor_data.get('ResourcePartyNumber', 'N/A')}: {str(e)}")
                continue
        
        # Commit de todos los cambios
        db.commit()
        logger.info(f"Sincronización completada: {creados} creados, {actualizados} actualizados, {errores} errores")
        
        return {
            "creados": creados,
            "actualizados": actualizados,
            "errores": errores
        }
        
    except httpx.HTTPError as e:
        logger.error(f"Error al conectar con servicio de vendedores: {str(e)}")
        raise Exception(f"Error al conectar con el servicio de vendedores: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error en sincronización: {str(e)}")
        raise


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
    request: ActualizarVacacionesRequest = Body(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Endpoint para actualizar el estado de vacaciones de un vendedor.
    Este endpoint:
    1. Actualiza el estado en el servicio externo de vacaciones (Lambda)
    2. Llama al servicio externo de vendedores para obtener datos actualizados
    3. Sincroniza la tabla usuario_marketing con los datos actualizados del servicio externo
    
    Args:
        request: Datos de la solicitud con party_number y estado de vacaciones
        db: Sesión de base de datos
        
    Returns:
        Dict[str, Any]: Respuesta de la operación
        
    Raises:
        HTTPException: Si hay un error al actualizar el estado
    """
    try:
        # Determinar acción para logging
        accion = "iniciar" if request.CTREnVacaciones_c else "finalizar"
        logger.info(f"[{accion.upper()} VACACIONES] Actualizando estado de vacaciones para party_number: {request.resource_user_id} (CTREnVacaciones_c={request.CTREnVacaciones_c})")
        
        # Paso 1: Actualizar estado en el servicio externo de vacaciones (Lambda)
        result = await _vendedor_service.actualizar_vacaciones(
            party_number=request.resource_user_id,
            en_vacaciones=request.CTREnVacaciones_c
        )
        logger.info(f"[{accion.upper()} VACACIONES] Estado actualizado en Lambda de vacaciones para party_number: {request.resource_user_id}")
        
        # Paso 2: Sincronizar datos desde el servicio externo de vendedores
        # Esto asegura que la tabla usuario_marketing tenga los datos más actualizados
        # Funciona igual tanto para iniciar como para finalizar vacaciones
        try:
            logger.info(f"[{accion.upper()} VACACIONES] Sincronizando usuario_marketing desde servicio externo de vendedores para party_number: {request.resource_user_id}")
            sync_result = await sincronizar_usuario_marketing_desde_servicio(
                db=db,
                party_number=request.resource_user_id
            )
            logger.info(f"[{accion.upper()} VACACIONES] Sincronización completada: {sync_result}")
        except Exception as sync_error:
            logger.error(f"[{accion.upper()} VACACIONES] Error al sincronizar usuario_marketing: {str(sync_error)}")
            # No lanzamos error aquí para no fallar la operación si el servicio externo se actualizó correctamente
            # Pero registramos el error para debugging
        
        # Mensaje descriptivo según la acción
        mensaje = f"Vacaciones {'iniciadas' if request.CTREnVacaciones_c else 'finalizadas'} correctamente"
        
        return {
            "success": True,
            "message": mensaje,
            "data": result,
            "sync_result": sync_result if 'sync_result' in locals() else None,
            "action": accion,
            "party_number": request.resource_user_id
        }
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error al actualizar estado de vacaciones: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar estado de vacaciones: {str(e)}"
        )

