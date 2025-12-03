from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List, Dict, Any
import logging
import json
import httpx

from ..database import get_db
from ..models.usuario_marketing import UsuarioMarketing
from ..schemas.usuario_marketing import (
    UsuarioMarketingCreate,
    UsuarioMarketingUpdate,
    UsuarioMarketingResponse,
    UsuarioMarketingListResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usuario-marketing", tags=["Usuario Marketing"])

# URL del servicio de vendedores
VENDEDORES_SERVICE_URL = "https://qkb7scw3iamis77inurjjggjee0mrivx.lambda-url.us-east-1.on.aws/"


def validate_json_field(data: dict, field_name: str) -> bool:
    """Valida que un campo JSON sea serializable"""
    try:
        if data and field_name in data and data[field_name] is not None:
            json.dumps(data[field_name])
        return True
    except (TypeError, ValueError) as e:
        logger.error(f"Error validando JSON en campo {field_name}: {str(e)}")
        return False


@router.post("/crear", response_model=dict)
def crear_usuario_marketing(
    usuario: UsuarioMarketingCreate,
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo usuario de marketing.
    
    Campos obligatorios:
    - nombre
    - party_id
    - party_number
    - correo
    - vacaciones (por defecto False)
    
    Campos opcionales:
    - id_usuario
    - dias_pendientes (JSON con formato {"2025": 66, "2026": 93})
    - periodos (JSON array con formato [{"inicio": "2025-01-15", "fin": "2025-01-20"}])
    """
    try:
        # Validar que no exista otro usuario con el mismo party_number
        existing = db.query(UsuarioMarketing).filter(
            UsuarioMarketing.party_number == usuario.party_number
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un usuario con party_number: {usuario.party_number}"
            )
        
        # Validar campos JSON si están presentes
        usuario_dict = usuario.dict()
        if not validate_json_field(usuario_dict, 'dias_pendientes'):
            raise HTTPException(
                status_code=400,
                detail="El campo 'dias_pendientes' contiene un JSON inválido"
            )
        
        if not validate_json_field(usuario_dict, 'periodos'):
            raise HTTPException(
                status_code=400,
                detail="El campo 'periodos' contiene un JSON inválido"
            )
        
        # Convertir periodos a dict si es necesario
        periodos_data = None
        if usuario.periodos:
            periodos_data = [p.dict() if hasattr(p, 'dict') else p for p in usuario.periodos]
        
        # Crear el usuario
        nuevo_usuario = UsuarioMarketing(
            nombre=usuario.nombre,
            party_id=usuario.party_id,
            party_number=usuario.party_number,
            correo=usuario.correo,
            vacaciones=usuario.vacaciones,
            id_usuario=usuario.id_usuario,
            dias_pendientes=usuario.dias_pendientes,
            periodos=periodos_data
        )
        
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        
        logger.info(f"Usuario de marketing creado: {nuevo_usuario.id} - {nuevo_usuario.nombre}")
        
        return {
            "status": "success",
            "mensaje": "Usuario de marketing creado exitosamente",
            "data": UsuarioMarketingResponse.from_orm(nuevo_usuario)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando usuario de marketing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al crear usuario de marketing: {str(e)}"
        )


@router.put("/actualizar/{usuario_id}", response_model=dict)
def actualizar_usuario_marketing(
    usuario_id: int,
    usuario_update: UsuarioMarketingUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualizar un usuario de marketing por su ID.
    
    Todos los campos son opcionales. Solo se actualizarán los campos enviados.
    """
    try:
        # Buscar el usuario
        usuario = db.query(UsuarioMarketing).filter(
            UsuarioMarketing.id == usuario_id
        ).first()
        
        if not usuario:
            raise HTTPException(
                status_code=404,
                detail=f"Usuario de marketing con id {usuario_id} no encontrado"
            )
        
        # Preparar datos de actualización
        update_data = usuario_update.dict(exclude_unset=True)
        
        # Validar campos JSON si están presentes
        if not validate_json_field(update_data, 'dias_pendientes'):
            raise HTTPException(
                status_code=400,
                detail="El campo 'dias_pendientes' contiene un JSON inválido"
            )
        
        if not validate_json_field(update_data, 'periodos'):
            raise HTTPException(
                status_code=400,
                detail="El campo 'periodos' contiene un JSON inválido"
            )
        
        # Validar party_number único si se está actualizando
        if 'party_number' in update_data:
            existing = db.query(UsuarioMarketing).filter(
                UsuarioMarketing.party_number == update_data['party_number'],
                UsuarioMarketing.id != usuario_id
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ya existe otro usuario con party_number: {update_data['party_number']}"
                )
        
        # Convertir periodos a dict si es necesario
        if 'periodos' in update_data and update_data['periodos'] is not None:
            update_data['periodos'] = [
                p.dict() if hasattr(p, 'dict') else p 
                for p in update_data['periodos']
            ]
        
        # Actualizar campos
        for field, value in update_data.items():
            setattr(usuario, field, value)
        
        db.commit()
        db.refresh(usuario)
        
        logger.info(f"Usuario de marketing actualizado: {usuario.id} - {usuario.nombre}")
        
        return {
            "status": "success",
            "mensaje": "Usuario de marketing actualizado exitosamente",
            "data": UsuarioMarketingResponse.from_orm(usuario)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando usuario de marketing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar usuario de marketing: {str(e)}"
        )


@router.get("/obtener/{usuario_id}", response_model=dict)
def obtener_usuario_marketing(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener un usuario de marketing por su ID.
    """
    try:
        usuario = db.query(UsuarioMarketing).filter(
            UsuarioMarketing.id == usuario_id
        ).first()
        
        if not usuario:
            raise HTTPException(
                status_code=404,
                detail=f"Usuario de marketing con id {usuario_id} no encontrado"
            )
        
        return {
            "status": "success",
            "mensaje": "Usuario encontrado",
            "data": UsuarioMarketingResponse.from_orm(usuario)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo usuario de marketing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener usuario de marketing: {str(e)}"
        )


@router.get("/listar", response_model=UsuarioMarketingListResponse)
def listar_usuarios_marketing(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(50, ge=1, le=100, description="Cantidad de registros por página"),
    party_id: Optional[int] = Query(None, description="Filtrar por party_id"),
    correo: Optional[str] = Query(None, description="Filtrar por correo (búsqueda parcial)"),
    buscar: Optional[str] = Query(None, description="Búsqueda general por nombre, correo o party_number"),
    db: Session = Depends(get_db)
):
    """
    Listar usuarios de marketing con paginación y filtros opcionales.
    
    Parámetros:
    - page: Número de página (inicia en 1)
    - size: Cantidad de registros por página (máximo 100)
    - party_id: Filtrar por party_id exacto
    - correo: Filtrar por correo (búsqueda parcial)
    - buscar: Búsqueda general en nombre, correo o party_number
    """
    try:
        # Query base
        query = db.query(UsuarioMarketing)
        
        # Aplicar filtros
        if party_id:
            query = query.filter(UsuarioMarketing.party_id == party_id)
        
        if correo:
            query = query.filter(UsuarioMarketing.correo.ilike(f"%{correo}%"))
        
        if buscar:
            search_pattern = f"%{buscar}%"
            query = query.filter(
                or_(
                    UsuarioMarketing.nombre.ilike(search_pattern),
                    UsuarioMarketing.correo.ilike(search_pattern),
                    UsuarioMarketing.party_number.ilike(search_pattern)
                )
            )
        
        # Contar total
        total = query.count()
        
        # Aplicar paginación
        offset = (page - 1) * size
        usuarios = query.offset(offset).limit(size).all()
        
        # Calcular total de páginas
        pages = (total + size - 1) // size if size else 0
        
        # Crear items en formato estándar
        items = [UsuarioMarketingResponse.from_orm(u) for u in usuarios]
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
        }
        
    except Exception as e:
        logger.error(f"Error listando usuarios de marketing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al listar usuarios de marketing: {str(e)}"
        )


@router.delete("/eliminar/{usuario_id}", response_model=dict)
def eliminar_usuario_marketing(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    """
    Eliminar un usuario de marketing por su ID.
    """
    try:
        usuario = db.query(UsuarioMarketing).filter(
            UsuarioMarketing.id == usuario_id
        ).first()
        
        if not usuario:
            raise HTTPException(
                status_code=404,
                detail=f"Usuario de marketing con id {usuario_id} no encontrado"
            )
        
        nombre = usuario.nombre
        db.delete(usuario)
        db.commit()
        
        logger.info(f"Usuario de marketing eliminado: {usuario_id} - {nombre}")
        
        return {
            "status": "success",
            "mensaje": f"Usuario de marketing '{nombre}' eliminado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando usuario de marketing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al eliminar usuario de marketing: {str(e)}"
        )


@router.post("/sincronizar-desde-servicio", response_model=dict)
async def sincronizar_usuarios_desde_servicio(
    db: Session = Depends(get_db)
):
    """
    [DEPRECADO] Use /user-crm-ventas en su lugar.
    
    Sincroniza los usuarios de marketing desde el servicio externo de vendedores.
    """
    logger.warning("Endpoint deprecado: /sincronizar-desde-servicio. Use /user-crm-ventas")
    return await sincronizar_usuarios_crm_ventas(db)


@router.post("/user-crm-ventas", response_model=dict)
async def sincronizar_usuarios_crm_ventas(
    db: Session = Depends(get_db)
):
    """
    Sincroniza los usuarios de marketing desde el CRM de ventas externo.
    
    Este endpoint:
    1. Llama al servicio externo para obtener la lista de vendedores del CRM
    2. Por cada vendedor, crea o actualiza el registro en usuario_marketing
    3. La combinación (party_id, party_number) es única
    
    Returns:
        Dict con status, mensaje y estadísticas de la operación
    """
    try:
        # Paso 1: Obtener datos del servicio externo
        logger.info("Iniciando sincronización desde CRM de ventas")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(VENDEDORES_SERVICE_URL)
            response.raise_for_status()
            data = response.json()
        
        # El servicio Lambda devuelve directamente una lista
        if isinstance(data, list):
            vendedores = data
        elif isinstance(data, dict) and 'items' in data:
            vendedores = data.get('items', [])
        else:
            raise HTTPException(
                status_code=500,
                detail="Formato de respuesta inválido del servicio de vendedores"
            )
        
        if not isinstance(vendedores, list):
            raise HTTPException(
                status_code=500,
                detail="La lista de vendedores tiene formato inválido"
            )
        
        logger.info(f"Se obtuvieron {len(vendedores)} vendedores del CRM de ventas")
        
        # Paso 2: Procesar cada vendedor
        creados = 0
        actualizados = 0
        errores = []
        
        for vendedor_data in vendedores:
            try:
                # Extraer datos del vendedor
                nombre = vendedor_data.get("PartyName", "")
                party_id = vendedor_data.get("ResourcePartyId")
                party_number = vendedor_data.get("ResourcePartyNumber", "")
                correo = vendedor_data.get("ResourceEmail", "")
                # Manejar valores nulos en vacaciones - por defecto False
                vacaciones_raw = vendedor_data.get("CTREnVacaciones_c")
                vacaciones = bool(vacaciones_raw) if vacaciones_raw is not None else False
                
                # Validar campos obligatorios
                if not nombre or not party_id or not party_number or not correo:
                    errores.append({
                        "party_number": party_number or "N/A",
                        "error": "Faltan campos obligatorios"
                    })
                    continue
                
                # Convertir party_id a entero
                try:
                    party_id = int(party_id)
                except (ValueError, TypeError):
                    errores.append({
                        "party_number": party_number,
                        "error": f"party_id inválido: {party_id}"
                    })
                    continue
                
                # Buscar si existe un registro con la misma combinación
                usuario_existente = db.query(UsuarioMarketing).filter(
                    UsuarioMarketing.party_id == party_id,
                    UsuarioMarketing.party_number == party_number
                ).first()
                
                if usuario_existente:
                    # Actualizar registro existente
                    usuario_existente.nombre = nombre
                    usuario_existente.correo = correo
                    usuario_existente.vacaciones = vacaciones
                    actualizados += 1
                    logger.debug(f"Actualizado: {nombre} ({party_number})")
                else:
                    # Crear nuevo registro
                    nuevo_usuario = UsuarioMarketing(
                        nombre=nombre,
                        party_id=party_id,
                        party_number=party_number,
                        correo=correo,
                        vacaciones=vacaciones
                    )
                    db.add(nuevo_usuario)
                    creados += 1
                    logger.debug(f"Creado: {nombre} ({party_number})")
                
            except Exception as e:
                errores.append({
                    "party_number": vendedor_data.get("ResourcePartyNumber", "N/A"),
                    "error": str(e)
                })
                logger.error(f"Error procesando vendedor: {str(e)}")
                continue
        
        # Commit de todos los cambios
        db.commit()
        
        logger.info(f"Sincronización completada: {creados} creados, {actualizados} actualizados, {len(errores)} errores")
        
        return {
            "status": "success",
            "mensaje": "Sincronización completada desde CRM de ventas",
            "data": {
                "total_procesados": len(vendedores),
                "creados": creados,
                "actualizados": actualizados,
                "errores": len(errores),
                "detalles_errores": errores[:10] if errores else []  # Solo primeros 10 errores
            }
        }
        
    except httpx.HTTPError as e:
        logger.error(f"Error al conectar con CRM de ventas: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Error al conectar con el CRM de ventas: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error en sincronización: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno en sincronización: {str(e)}"
        )
