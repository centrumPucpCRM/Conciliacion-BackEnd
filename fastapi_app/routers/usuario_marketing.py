from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List, Dict, Any
import logging
import json
import httpx
from pydantic import BaseModel, Field
from datetime import datetime, date, timedelta

from ..database import get_db
from ..models.usuario_marketing import UsuarioMarketing
from ..schemas.usuario_marketing import (
    UsuarioMarketingCreate,
    UsuarioMarketingUpdate,
    UsuarioMarketingResponse,
    UsuarioMarketingListResponse,
    PeriodoVacaciones,
    CalendarioVacacionesResponse,
    EventoCalendarioVacaciones
)
from ..utils.vacaciones_utils import (
    calcular_estado_vacaciones,
    procesar_periodos_con_estado,
    procesar_vacaciones_extras_con_estado,
    validar_observacion_requerida
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usuario-marketing", tags=["Usuario Marketing"])


# Schema para importar datos de vacaciones
class ImportarVacacionesRequest(BaseModel):
    """Schema para importar datos de vacaciones desde Excel"""
    data: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Diccionario con correo como clave y datos de vacaciones como valor"
    )


def generar_party_ids_y_party_numbers(db: Session, cantidad: int) -> list[tuple[int, str]]:
    """
    Genera múltiples party_id y party_number únicos para nuevos usuarios de forma eficiente.
    
    Args:
        db: Sesión de base de datos
        cantidad: Cantidad de party_id/party_number a generar
    
    Returns:
        list: Lista de tuplas (party_id, party_number)
    """
    # Obtener todos los party_numbers y party_ids existentes (una sola consulta cada una)
    party_numbers_existentes = set(
        row[0] for row in db.query(UsuarioMarketing.party_number).filter(
            func.length(UsuarioMarketing.party_number) == 5
        ).all() if row[0]
    )
    
    party_ids_existentes = set(
        row[0] for row in db.query(UsuarioMarketing.party_id).filter(
            UsuarioMarketing.party_id >= 3000000000000
        ).all() if row[0]
    )
    
    # Extraer los dígitos únicos usados (1-9) de party_numbers con dígitos iguales
    digitos_usados = set()
    for party_num in party_numbers_existentes:
        if party_num.isdigit() and len(party_num) == 5:
            if all(d == party_num[0] for d in party_num):
                digitos_usados.add(int(party_num[0]))
    
    resultados = []
    siguiente_digito = 1
    contador_secuencial = 1
    
    while len(resultados) < cantidad:
        # Intentar usar dígitos del 1-9 primero
        if siguiente_digito <= 9:
            if siguiente_digito not in digitos_usados:
                nuevo_party_number = str(siguiente_digito) * 5
                digitos_7 = str(siguiente_digito) * 7
                nuevo_party_id = 3000000000000 + int(digitos_7)
                
                # Verificar que no esté en uso
                if nuevo_party_id not in party_ids_existentes and nuevo_party_number not in party_numbers_existentes:
                    resultados.append((nuevo_party_id, nuevo_party_number))
                    party_ids_existentes.add(nuevo_party_id)
                    party_numbers_existentes.add(nuevo_party_number)
                    digitos_usados.add(siguiente_digito)
            
            siguiente_digito += 1
        else:
            # Si se agotaron los dígitos 1-9, usar un contador secuencial
            # Generar party_id: 30000000 + contador secuencial de 7 dígitos
            # Generar party_number: contador de 5 dígitos (empezando desde 10000)
            nuevo_party_id = 3000000000000 + (1000000 + contador_secuencial)
            nuevo_party_number = str(10000 + contador_secuencial).zfill(5)
            
            # Verificar que no esté en uso
            if nuevo_party_id not in party_ids_existentes and nuevo_party_number not in party_numbers_existentes:
                resultados.append((nuevo_party_id, nuevo_party_number))
                party_ids_existentes.add(nuevo_party_id)
                party_numbers_existentes.add(nuevo_party_number)
            
            contador_secuencial += 1
            
            # Protección contra bucles infinitos
            if contador_secuencial > 999999:
                raise Exception(f"No se pudieron generar {cantidad} party_id/party_number únicos")
    
    return resultados

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


def procesar_usuario_para_respuesta(usuario: UsuarioMarketing) -> Dict[str, Any]:
    """
    Procesa un usuario de marketing para la respuesta, calculando estados automáticamente.
    
    Args:
        usuario: Instancia de UsuarioMarketing
    
    Returns:
        Diccionario con los datos procesados listos para la respuesta
    """
    # Procesar periodos con estados calculados
    periodos_procesados = procesar_periodos_con_estado(
        usuario.periodos if usuario.periodos else None,
        recalcular_estados=True
    )
    
    # Procesar vacaciones extras con estados calculados
    vacaciones_extras_procesadas = procesar_vacaciones_extras_con_estado(
        usuario.vacaciones_extras if hasattr(usuario, 'vacaciones_extras') and usuario.vacaciones_extras else None,
        recalcular_estados=True
    )
    
    # Construir respuesta
    respuesta = {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "party_id": usuario.party_id,
        "party_number": usuario.party_number,
        "correo": usuario.correo,
        "vacaciones": usuario.vacaciones,
        "id_usuario": usuario.id_usuario,
        "dias_pendientes": usuario.dias_pendientes,
        "periodos": periodos_procesados,
        "vacaciones_extras": vacaciones_extras_procesadas
    }
    
    return respuesta


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
        
        # Procesar usuario para respuesta con estados calculados
        usuario_procesado = procesar_usuario_para_respuesta(nuevo_usuario)
        
        return {
            "status": "success",
            "mensaje": "Usuario de marketing creado exitosamente",
            "data": usuario_procesado
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
        
        # Procesar usuario para respuesta con estados calculados
        usuario_procesado = procesar_usuario_para_respuesta(usuario)
        
        return {
            "status": "success",
            "mensaje": "Usuario de marketing actualizado exitosamente",
            "data": usuario_procesado
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
        
        # Procesar usuario para respuesta con estados calculados
        usuario_procesado = procesar_usuario_para_respuesta(usuario)
        
        return {
            "status": "success",
            "mensaje": "Usuario encontrado",
            "data": usuario_procesado
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
    size: int = Query(50, ge=1, le=1000, description="Cantidad de registros por página (máximo 1000)"),
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
        
        # Procesar usuarios para respuesta con estados calculados
        items = [procesar_usuario_para_respuesta(u) for u in usuarios]
        
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
        logger.info(f"Iniciando sincronización desde servicio de vendedores: {VENDEDORES_SERVICE_URL}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(VENDEDORES_SERVICE_URL)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Respuesta recibida del servicio de vendedores: {len(data) if isinstance(data, list) else 'formato no lista'}")
        
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
        
        # Paso 2: Validar y preparar datos
        vendedores_validos = []
        errores = []
        
        for vendedor_data in vendedores:
            try:
                nombre = vendedor_data.get("PartyName", "")
                party_id = vendedor_data.get("ResourcePartyId")
                party_number = vendedor_data.get("ResourcePartyNumber", "")
                correo = vendedor_data.get("ResourceEmail", "")
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
                
                vendedores_validos.append({
                    "nombre": nombre,
                    "party_id": party_id,
                    "party_number": party_number,
                    "correo": correo,
                    "vacaciones": vacaciones
                })
                
            except Exception as e:
                errores.append({
                    "party_number": vendedor_data.get("ResourcePartyNumber", "N/A"),
                    "error": str(e)
                })
                continue
        
        logger.info(f"Validados {len(vendedores_validos)} vendedores correctamente")
        
        # Paso 3: Obtener todos los usuarios existentes en una sola consulta
        party_ids = [v["party_id"] for v in vendedores_validos]
        party_numbers = [v["party_number"] for v in vendedores_validos]
        
        usuarios_existentes = db.query(UsuarioMarketing).filter(
            UsuarioMarketing.party_id.in_(party_ids),
            UsuarioMarketing.party_number.in_(party_numbers)
        ).all()
        
        # Crear un diccionario para búsqueda rápida
        usuarios_dict = {
            (u.party_id, u.party_number): u 
            for u in usuarios_existentes
        }
        
        logger.info(f"Encontrados {len(usuarios_existentes)} usuarios existentes en BD")
        
        # Paso 4: Procesar en lotes y actualizar tabla usuario_marketing
        creados = 0
        actualizados = 0
        nuevos_usuarios = []
        
        logger.info(f"Procesando {len(vendedores_validos)} vendedores para actualizar tabla usuario_marketing")
        
        for vendedor in vendedores_validos:
            key = (vendedor["party_id"], vendedor["party_number"])
            
            if key in usuarios_dict:
                # Actualizar existente en tabla usuario_marketing
                usuario = usuarios_dict[key]
                usuario.nombre = vendedor["nombre"]
                usuario.correo = vendedor["correo"]
                usuario.vacaciones = vendedor["vacaciones"]
                actualizados += 1
            else:
                # Preparar para crear nuevo registro en tabla usuario_marketing
                nuevos_usuarios.append(UsuarioMarketing(
                    nombre=vendedor["nombre"],
                    party_id=vendedor["party_id"],
                    party_number=vendedor["party_number"],
                    correo=vendedor["correo"],
                    vacaciones=vendedor["vacaciones"]
                ))
                creados += 1
        
        # Paso 5: Inserción masiva de nuevos usuarios en tabla usuario_marketing
        if nuevos_usuarios:
            db.bulk_save_objects(nuevos_usuarios)
            logger.info(f"Insertados {len(nuevos_usuarios)} nuevos usuarios en tabla usuario_marketing")
        
        # Commit único de todos los cambios en tabla usuario_marketing
        db.commit()
        logger.info(f"Cambios en tabla usuario_marketing confirmados exitosamente")
        
        logger.info(f"Sincronización completada: {creados} creados, {actualizados} actualizados, {len(errores)} errores en tabla usuario_marketing")
        
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


@router.post("/importar-vacaciones", response_model=dict)
async def importar_datos_vacaciones(
    request: ImportarVacacionesRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Importa datos de vacaciones desde Excel y actualiza/crea registros en usuario_marketing.
    Optimizado para procesar grandes volúmenes de datos usando operaciones por lotes.
    
    El formato esperado es:
    {
        "correo@ejemplo.com": {
            "nombre": "Nombre Completo",
            "diasPendientes": {"2025": 74, "2026": 104},
            "periodos": [
                {"inicio": "2026-01-02", "fin": "2026-01-04"},
                ...
            ]
        }
    }
    
    Si el correo existe, actualiza: nombre, dias_pendientes, periodos
    Si no existe, crea un nuevo registro con party_id y party_number generados automáticamente.
    """
    try:
        total_usuarios = len(request.data)
        logger.info(f"Iniciando importación de datos de vacaciones para {total_usuarios} usuarios")
        
        # Paso 1: Preparar datos y validar
        correos_lower = []
        datos_procesados = {}
        errores = []
        
        for correo, datos in request.data.items():
            correo_lower = correo.lower().strip()
            nombre = datos.get("nombre", "")
            
            if not nombre:
                errores.append({
                    "correo": correo_lower,
                    "error": "El campo 'nombre' es obligatorio"
                })
                continue
            
            correos_lower.append(correo_lower)
            datos_procesados[correo_lower] = {
                "nombre": nombre,
                "dias_pendientes": datos.get("diasPendientes", {}),
                "periodos": datos.get("periodos", [])
            }
        
        if not correos_lower:
            return {
                "status": "error",
                "mensaje": "No hay datos válidos para procesar",
                "data": {
                    "total_procesados": total_usuarios,
                    "creados": 0,
                    "actualizados": 0,
                    "errores": len(errores),
                    "detalles_errores": errores
                }
            }
        
        # Paso 2: Obtener todos los usuarios existentes en una sola consulta (optimizado)
        usuarios_existentes = db.query(UsuarioMarketing).filter(
            func.lower(UsuarioMarketing.correo).in_(correos_lower)
        ).all()
        
        # Crear diccionario para búsqueda rápida O(1)
        usuarios_dict = {usuario.correo.lower(): usuario for usuario in usuarios_existentes}
        
        # Paso 3: Separar usuarios a actualizar y crear
        usuarios_a_actualizar = []
        usuarios_a_crear = []
        correos_a_crear = []
        
        for correo_lower, datos in datos_procesados.items():
            if correo_lower in usuarios_dict:
                usuarios_a_actualizar.append((correo_lower, datos, usuarios_dict[correo_lower]))
            else:
                correos_a_crear.append(correo_lower)
                usuarios_a_crear.append((correo_lower, datos))
        
        # Paso 4: Generar todos los party_id/party_number necesarios de una vez
        party_ids_numbers = []
        if correos_a_crear:
            party_ids_numbers = generar_party_ids_y_party_numbers(db, len(correos_a_crear))
        
        # Paso 5: Preparar datos para bulk update
        updates = []
        for correo_lower, datos, usuario in usuarios_a_actualizar:
            # Procesar periodos con estados y observaciones
            periodos_formateados = None
            if datos["periodos"]:
                periodos_formateados = []
                for p in datos["periodos"]:
                    periodo_procesado = {
                        "inicio": p.get("inicio", ""),
                        "fin": p.get("fin", ""),
                        "estado": p.get("estado"),
                        "observacion": p.get("observacion", "sin observaciones")
                    }
                    # Calcular estado si no se proporciona
                    if not periodo_procesado["estado"]:
                        periodo_procesado["estado"] = calcular_estado_vacaciones(
                            inicio=periodo_procesado["inicio"],
                            fin=periodo_procesado["fin"]
                        )
                    periodos_formateados.append(periodo_procesado)
            
            # Procesar vacaciones extras si vienen en los datos
            vacaciones_extras_formateadas = None
            if datos.get("vacaciones_extras"):
                vacaciones_extras_formateadas = {}
                for tipo in ["medico", "otros"]:
                    if tipo in datos["vacaciones_extras"]:
                        vacaciones_tipo = []
                        for ve in datos["vacaciones_extras"][tipo]:
                            ve_procesada = {
                                "inicio": ve.get("inicio", ""),
                                "fin": ve.get("fin", ""),
                                "estado": ve.get("estado"),
                                "observacion": ve.get("observacion", "sin observaciones")
                            }
                            if not ve_procesada["estado"]:
                                ve_procesada["estado"] = calcular_estado_vacaciones(
                                    inicio=ve_procesada["inicio"],
                                    fin=ve_procesada["fin"]
                                )
                            vacaciones_tipo.append(ve_procesada)
                        vacaciones_extras_formateadas[tipo] = vacaciones_tipo
            
            updates.append({
                "id": usuario.id,
                "nombre": datos["nombre"],
                "dias_pendientes": datos["dias_pendientes"] if datos["dias_pendientes"] else None,
                "periodos": periodos_formateados,
                "vacaciones_extras": vacaciones_extras_formateadas if vacaciones_extras_formateadas else usuario.vacaciones_extras
            })
        
        # Paso 6: Preparar datos para bulk insert
        inserts = []
        for idx, (correo_lower, datos) in enumerate(usuarios_a_crear):
            party_id, party_number = party_ids_numbers[idx]
            
            # Procesar periodos con estados y observaciones
            periodos_formateados = None
            if datos["periodos"]:
                periodos_formateados = []
                for p in datos["periodos"]:
                    periodo_procesado = {
                        "inicio": p.get("inicio", ""),
                        "fin": p.get("fin", ""),
                        "estado": p.get("estado"),
                        "observacion": p.get("observacion", "sin observaciones")
                    }
                    # Calcular estado si no se proporciona
                    if not periodo_procesado["estado"]:
                        periodo_procesado["estado"] = calcular_estado_vacaciones(
                            inicio=periodo_procesado["inicio"],
                            fin=periodo_procesado["fin"]
                        )
                    periodos_formateados.append(periodo_procesado)
            
            # Procesar vacaciones extras si vienen en los datos
            vacaciones_extras_formateadas = None
            if datos.get("vacaciones_extras"):
                vacaciones_extras_formateadas = {}
                for tipo in ["medico", "otros"]:
                    if tipo in datos["vacaciones_extras"]:
                        vacaciones_tipo = []
                        for ve in datos["vacaciones_extras"][tipo]:
                            ve_procesada = {
                                "inicio": ve.get("inicio", ""),
                                "fin": ve.get("fin", ""),
                                "estado": ve.get("estado"),
                                "observacion": ve.get("observacion", "sin observaciones")
                            }
                            if not ve_procesada["estado"]:
                                ve_procesada["estado"] = calcular_estado_vacaciones(
                                    inicio=ve_procesada["inicio"],
                                    fin=ve_procesada["fin"]
                                )
                            vacaciones_tipo.append(ve_procesada)
                        vacaciones_extras_formateadas[tipo] = vacaciones_tipo
            
            inserts.append({
                "nombre": datos["nombre"],
                "party_id": party_id,
                "party_number": party_number,
                "correo": correo_lower,
                "vacaciones": False,
                "id_usuario": None,
                "dias_pendientes": datos["dias_pendientes"] if datos["dias_pendientes"] else None,
                "periodos": periodos_formateados,
                "vacaciones_extras": vacaciones_extras_formateadas
            })
        
        # Paso 7: Ejecutar bulk operations
        actualizados = 0
        if updates:
            # Bulk update: actualizar todos los registros en una sola operación
            # Usar bulk_update_mappings para mejor performance
            db.bulk_update_mappings(UsuarioMarketing, updates)
            actualizados = len(updates)
        
        creados = 0
        if inserts:
            # Bulk insert usando bulk_insert_mappings
            db.bulk_insert_mappings(UsuarioMarketing, inserts)
            creados = len(inserts)
        
        # Paso 8: Commit único de todos los cambios
        db.commit()
        
        logger.info(f"Importación completada: {creados} creados, {actualizados} actualizados, {len(errores)} errores")
        
        return {
            "status": "success",
            "mensaje": "Datos de vacaciones importados correctamente",
            "data": {
                "total_procesados": total_usuarios,
                "creados": creados,
                "actualizados": actualizados,
                "errores": len(errores),
                "detalles_errores": errores[:10] if errores else []  # Solo primeros 10 errores
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error en importación de datos de vacaciones: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al importar datos de vacaciones: {str(e)}"
        )


@router.put("/{usuario_id}/periodos-vacaciones", response_model=dict)
def actualizar_periodos_vacaciones(
    usuario_id: int,
    periodos: Optional[List[Dict[str, Any]]] = Body(None),
    vacaciones_extras: Optional[Dict[str, List[Dict[str, Any]]]] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Actualiza los periodos de vacaciones y vacaciones extras de un usuario.
    Valida estados y observaciones según reglas de negocio.
    
    Args:
        usuario_id: ID del usuario
        periodos: Lista de periodos con estructura: [{"inicio": "...", "fin": "...", "estado": "...", "observacion": "..."}]
        vacaciones_extras: Diccionario con estructura: {"medico": [...], "otros": [...]}
        db: Sesión de base de datos
    
    Returns:
        Dict con el usuario actualizado
    """
    try:
        # Buscar usuario
        usuario = db.query(UsuarioMarketing).filter(
            UsuarioMarketing.id == usuario_id
        ).first()
        
        if not usuario:
            raise HTTPException(
                status_code=404,
                detail=f"Usuario de marketing con id {usuario_id} no encontrado"
            )
        
        # Procesar periodos con validación
        periodos_procesados = None
        if periodos is not None:
            periodos_procesados = []
            periodos_anteriores = usuario.periodos if usuario.periodos else []
            periodos_dict_anteriores = {i: p for i, p in enumerate(periodos_anteriores)}
            
            for idx, periodo_nuevo in enumerate(periodos):
                # Validar observación si hay cambios
                periodo_anterior = periodos_dict_anteriores.get(idx)
                if periodo_anterior:
                    es_valido, mensaje_error = validar_observacion_requerida(
                        periodo_anterior,
                        periodo_nuevo,
                        "actualizar"
                    )
                    if not es_valido:
                        raise HTTPException(status_code=400, detail=mensaje_error)
                
                # Calcular estado si no se proporciona
                estado = periodo_nuevo.get("estado")
                if not estado or estado not in ["planificado", "activo", "finalizado", "cancelado"]:
                    estado = calcular_estado_vacaciones(
                        inicio=periodo_nuevo.get("inicio", ""),
                        fin=periodo_nuevo.get("fin", ""),
                        es_cancelado=periodo_nuevo.get("estado") == "cancelado"
                    )
                
                periodos_procesados.append({
                    "inicio": periodo_nuevo.get("inicio", ""),
                    "fin": periodo_nuevo.get("fin", ""),
                    "estado": estado,
                    "observacion": periodo_nuevo.get("observacion", "sin observaciones")
                })
        
        # Procesar vacaciones extras con validación
        vacaciones_extras_procesadas = None
        if vacaciones_extras is not None:
            vacaciones_extras_procesadas = {}
            vacaciones_extras_anteriores = usuario.vacaciones_extras if hasattr(usuario, 'vacaciones_extras') and usuario.vacaciones_extras else {}
            
            for tipo in ["medico", "otros"]:
                if tipo in vacaciones_extras:
                    vacaciones_tipo = []
                    vacaciones_anteriores_tipo = vacaciones_extras_anteriores.get(tipo, [])
                    vacaciones_dict_anteriores = {i: v for i, v in enumerate(vacaciones_anteriores_tipo)}
                    
                    for idx, ve_nueva in enumerate(vacaciones_extras[tipo]):
                        # Validar observación si hay cambios
                        ve_anterior = vacaciones_dict_anteriores.get(idx)
                        if ve_anterior:
                            es_valido, mensaje_error = validar_observacion_requerida(
                                ve_anterior,
                                ve_nueva,
                                "actualizar"
                            )
                            if not es_valido:
                                raise HTTPException(status_code=400, detail=mensaje_error)
                        
                        # Calcular estado si no se proporciona
                        estado = ve_nueva.get("estado")
                        if not estado or estado not in ["planificado", "activo", "finalizado", "cancelado"]:
                            estado = calcular_estado_vacaciones(
                                inicio=ve_nueva.get("inicio", ""),
                                fin=ve_nueva.get("fin", ""),
                                es_cancelado=ve_nueva.get("estado") == "cancelado"
                            )
                        
                        vacaciones_tipo.append({
                            "inicio": ve_nueva.get("inicio", ""),
                            "fin": ve_nueva.get("fin", ""),
                            "estado": estado,
                            "observacion": ve_nueva.get("observacion", "sin observaciones")
                        })
                    
                    vacaciones_extras_procesadas[tipo] = vacaciones_tipo
        
        # Actualizar usuario
        if periodos_procesados is not None:
            usuario.periodos = periodos_procesados
        if vacaciones_extras_procesadas is not None:
            usuario.vacaciones_extras = vacaciones_extras_procesadas
        
        db.commit()
        db.refresh(usuario)
        
        logger.info(f"Periodos y vacaciones extras actualizados para usuario: {usuario.id} - {usuario.nombre}")
        
        # Procesar usuario para respuesta
        usuario_procesado = procesar_usuario_para_respuesta(usuario)
        
        return {
            "status": "success",
            "mensaje": "Periodos y vacaciones extras actualizados exitosamente",
            "data": usuario_procesado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al actualizar periodos y vacaciones extras: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar periodos y vacaciones extras: {str(e)}"
        )


@router.get("/calendario", response_model=CalendarioVacacionesResponse)
def obtener_calendario_vacaciones(
    fecha_inicio: str = Query(..., description="Fecha de inicio del rango (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha de fin del rango (YYYY-MM-DD)"),
    estado: Optional[str] = Query(None, description="Filtrar por estado: planificado, activo, finalizado, cancelado"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo: periodo, medico, otros"),
    usuario_id: Optional[int] = Query(None, description="Filtrar por ID de usuario"),
    db: Session = Depends(get_db)
):
    """
    Endpoint optimizado para obtener eventos de vacaciones para el calendario.
    Unifica periodos y vacaciones_extras en una sola respuesta normalizada.
    
    Args:
        fecha_inicio: Fecha de inicio del rango a consultar (YYYY-MM-DD)
        fecha_fin: Fecha de fin del rango a consultar (YYYY-MM-DD)
        estado: Opcional - Filtrar por estado específico
        tipo: Opcional - Filtrar por tipo (periodo, medico, otros)
        usuario_id: Opcional - Filtrar por usuario específico
        db: Sesión de base de datos
    
    Returns:
        CalendarioVacacionesResponse con eventos normalizados listos para el calendario
    """
    try:
        # Validar y parsear fechas
        try:
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )
        
        if fecha_inicio_obj > fecha_fin_obj:
            raise HTTPException(
                status_code=400,
                detail="La fecha de inicio no puede ser posterior a la fecha de fin"
            )
        
        # Validar filtros opcionales
        estados_permitidos = ["planificado", "activo", "finalizado", "cancelado"]
        if estado and estado not in estados_permitidos:
            raise HTTPException(
                status_code=400,
                detail=f"Estado inválido. Debe ser uno de: {', '.join(estados_permitidos)}"
            )
        
        tipos_permitidos = ["periodo", "medico", "otros"]
        if tipo and tipo not in tipos_permitidos:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo inválido. Debe ser uno de: {', '.join(tipos_permitidos)}"
            )
        
        # Consultar usuarios (con filtro opcional por usuario_id)
        # Solo cargar campos necesarios para optimizar
        query = db.query(
            UsuarioMarketing.id,
            UsuarioMarketing.nombre,
            UsuarioMarketing.correo,
            UsuarioMarketing.party_number,
            UsuarioMarketing.periodos,
            UsuarioMarketing.vacaciones_extras
        )
        if usuario_id:
            query = query.filter(UsuarioMarketing.id == usuario_id)
        
        usuarios = query.all()
        
        eventos: List[EventoCalendarioVacaciones] = []
        fecha_actual = date.today()
        
        # Procesar cada usuario de forma optimizada
        for usuario in usuarios:
            # Procesar periodos de forma más eficiente
            if usuario.periodos:
                for periodo in usuario.periodos:
                    if not isinstance(periodo, dict):
                        continue
                    
                    try:
                        periodo_inicio_str = periodo.get("inicio")
                        periodo_fin_str = periodo.get("fin")
                        
                        if not periodo_inicio_str or not periodo_fin_str:
                            continue
                        
                        periodo_inicio = datetime.strptime(periodo_inicio_str, '%Y-%m-%d').date()
                        periodo_fin = datetime.strptime(periodo_fin_str, '%Y-%m-%d').date()
                        
                        # Verificar solapamiento ANTES de procesar estado (optimización temprana)
                        if periodo_fin < fecha_inicio_obj or periodo_inicio > fecha_fin_obj:
                            continue
                        
                        # Calcular estado de forma optimizada
                        periodo_estado = periodo.get("estado")
                        if not periodo_estado or periodo_estado != "cancelado":
                            # Solo recalcular si no está cancelado
                            if periodo_inicio > fecha_actual:
                                periodo_estado = "planificado"
                            elif periodo_inicio <= fecha_actual <= periodo_fin:
                                periodo_estado = "activo"
                            else:
                                periodo_estado = "finalizado"
                        
                        # Aplicar filtros
                        if estado and periodo_estado != estado:
                            continue
                        
                        if tipo and tipo != "periodo":
                            continue
                        
                        # Calcular días
                        dias = (periodo_fin - periodo_inicio).days + 1
                        
                        eventos.append(EventoCalendarioVacaciones(
                            id_usuario=usuario.id,
                            nombre=usuario.nombre,
                            correo=usuario.correo,
                            party_number=usuario.party_number,
                            tipo="periodo",
                            inicio=periodo_inicio_str,
                            fin=periodo_fin_str,
                            estado=periodo_estado,
                            observacion=periodo.get("observacion"),
                            dias=dias
                        ))
                    except (ValueError, KeyError, TypeError) as e:
                        logger.debug(f"Error procesando periodo del usuario {usuario.id}: {str(e)}")
                        continue
            
            # Procesar vacaciones extras de forma optimizada
            if usuario.vacaciones_extras:
                for tipo_ve in ["medico", "otros"]:
                    if tipo and tipo != tipo_ve:
                        continue
                    
                    vacaciones_tipo = usuario.vacaciones_extras.get(tipo_ve, [])
                    if not vacaciones_tipo:
                        continue
                    
                    for ve in vacaciones_tipo:
                        if not isinstance(ve, dict):
                            continue
                        
                        try:
                            ve_inicio_str = ve.get("inicio")
                            ve_fin_str = ve.get("fin")
                            
                            if not ve_inicio_str or not ve_fin_str:
                                continue
                            
                            ve_inicio = datetime.strptime(ve_inicio_str, '%Y-%m-%d').date()
                            ve_fin = datetime.strptime(ve_fin_str, '%Y-%m-%d').date()
                            
                            # Verificar solapamiento ANTES de procesar estado
                            if ve_fin < fecha_inicio_obj or ve_inicio > fecha_fin_obj:
                                continue
                            
                            # Calcular estado de forma optimizada
                            ve_estado = ve.get("estado")
                            if not ve_estado or ve_estado != "cancelado":
                                if ve_inicio > fecha_actual:
                                    ve_estado = "planificado"
                                elif ve_inicio <= fecha_actual <= ve_fin:
                                    ve_estado = "activo"
                                else:
                                    ve_estado = "finalizado"
                            
                            # Aplicar filtros
                            if estado and ve_estado != estado:
                                continue
                            
                            # Calcular días
                            dias = (ve_fin - ve_inicio).days + 1
                            
                            eventos.append(EventoCalendarioVacaciones(
                                id_usuario=usuario.id,
                                nombre=usuario.nombre,
                                correo=usuario.correo,
                                party_number=usuario.party_number,
                                tipo=tipo_ve,
                                inicio=ve_inicio_str,
                                fin=ve_fin_str,
                                estado=ve_estado,
                                observacion=ve.get("observacion"),
                                dias=dias
                            ))
                        except (ValueError, KeyError, TypeError) as e:
                            logger.debug(f"Error procesando vacación extra {tipo_ve} del usuario {usuario.id}: {str(e)}")
                            continue
        
        logger.info(f"Calendario generado: {len(eventos)} eventos entre {fecha_inicio} y {fecha_fin}")
        
        return CalendarioVacacionesResponse(
            eventos=eventos,
            total=len(eventos),
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener calendario de vacaciones: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener calendario de vacaciones: {str(e)}"
        )
