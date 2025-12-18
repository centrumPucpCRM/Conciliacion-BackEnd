from fastapi_app.models.rol_permiso import Rol
from fastapi_app.models.cartera import Cartera

from typing import List, Optional
from fastapi_app.models.usuario import Usuario
from fastapi_app.schemas.usuario import Usuario as UsuarioSchema


from fastapi import APIRouter, Body, HTTPException, Depends, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_
from fastapi_app.database import get_db
from fastapi_app.models.usuario import Usuario
import logging
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usuario", tags=["Usuario"])

# URL del servicio de autenticación de Google
GOOGLE_AUTH_SERVICE_URL = "http://localhost:8000"

@router.post("/login")
def login_usuario(
    data: dict = Body(..., example={"nombre": "admin", "clave": "admin"}),
    db: Session = Depends(get_db)
):
    """
    Login tradicional del sistema.
    Solo para usuarios locales con nombre y clave.
    """
    nombre = data.get("nombre")
    clave = data.get("clave")
    user = db.query(Usuario).filter(Usuario.nombre == nombre).first()
    
    if user and hasattr(user, "clave") and user.clave == clave:
        # Verificar que el usuario esté activo
        if not user.activo:
            raise HTTPException(
                status_code=403,
                detail="Usuario inactivo. Contacte al administrador."
            )
        
        # Get direct permissions
        direct_perms = set(p.descripcion for p in getattr(user, "permisos", []) if hasattr(p, "descripcion"))
        # Get permissions from roles
        role_perms = set()
        for rol in getattr(user, "roles", []):
            for p in getattr(rol, "permisos", []):
                if hasattr(p, "descripcion"):
                    role_perms.add(p.descripcion)
        permisos = list(direct_perms | role_perms)
        
        return {
            "status": "success",
            "usuario": {
                "idUsuario": user.id,
                "nombre": user.nombre,
                "correo": user.correo,
                "activo": user.activo,
                "tipo": "local",
                "permisos": permisos
            }
        }
    raise HTTPException(status_code=401, detail="Credenciales inválidas")


@router.get("/listar")
async def listar_usuarios(
    incluir_inactivos: bool = False,
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get_db)
):
    """
    Lista todos los usuarios del sistema (locales y de Google) con paginación optimizada.
    
    Los usuarios se distinguen por:
    - Usuarios locales: tienen campo 'clave' no nulo
    - Usuarios de Google: tienen documentoIdentidad que empieza con 'GOOGLE_' y clave nula
    
    También intenta obtener usuarios del servicio de Google (puerto 8000) si está disponible.
    
    Args:
        incluir_inactivos: Si es True, incluye usuarios inactivos (pendientes de aprobación)
        page: Número de página (inicia en 1)
        size: Cantidad de registros por página
        db: Sesión de base de datos
        
    Returns:
        Lista paginada de usuarios con su tipo y estado
    """
    try:
        # Construir query optimizada con eager loading
        query = db.query(Usuario).options(
            selectinload(Usuario.roles),
            selectinload(Usuario.permisos)
        )
        
        if not incluir_inactivos:
            query = query.filter(Usuario.activo == True)
        
        # Contar total de registros
        total = query.count()
        
        # Aplicar paginación
        offset = (page - 1) * size
        usuarios = query.offset(offset).limit(size).all()
        
        usuarios_lista = []
        for user in usuarios:
            # Determinar tipo de usuario
            es_google = (
                user.documentoIdentidad and 
                user.documentoIdentidad.startswith("GOOGLE_") and 
                user.clave is None
            )
            
            # Get permissions (optimizado con eager loading)
            direct_perms = {p.descripcion for p in user.permisos if hasattr(p, "descripcion")}
            role_perms = set()
            for rol in user.roles:
                for p in rol.permisos:
                    if hasattr(p, "descripcion"):
                        role_perms.add(p.descripcion)
            permisos = list(direct_perms | role_perms)
            
            # Get role names (optimizado)
            roles = [rol.nombre for rol in user.roles if hasattr(rol, "nombre")]
            
            usuarios_lista.append({
                "idUsuario": user.id,
                "nombre": user.nombre,
                "correo": user.correo,
                "documentoIdentidad": user.documentoIdentidad,
                "activo": user.activo,
                "tipo": "google" if es_google else "local",
                "permisos": permisos,
                "roles": roles
            })
        
        # Intentar obtener usuarios del servicio de Google (si está disponible)
        usuarios_google_externos = []
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                # Llamar al servicio de Google para obtener usuarios
                response = await client.get(f"{GOOGLE_AUTH_SERVICE_URL}/auth/users")
                if response.status_code == 200:
                    google_users = response.json()
                    # Filtrar usuarios que no están en la BD local
                    correos_locales = {u["correo"] for u in usuarios_lista}
                    for gu in google_users:
                        if gu.get("email") not in correos_locales:
                            usuarios_google_externos.append({
                                "idUsuario": None,
                                "nombre": gu.get("name", gu.get("email", "").split("@")[0]),
                                "correo": gu.get("email"),
                                "documentoIdentidad": f"GOOGLE_{gu.get('id', '')}",
                                "activo": False,  # No están en BD local, por lo tanto inactivos
                                "tipo": "google",
                                "permisos": [],
                                "roles": [],
                                "origen": "servicio_externo"
                            })
        except Exception as google_error:
            # No es crítico si el servicio de Google no está disponible
            logger.debug(f"Servicio de Google no disponible: {google_error}")
        
        # Combinar usuarios locales y externos
        todos_usuarios = usuarios_lista + usuarios_google_externos
        
        # Calcular metadata de paginación
        total_pages = (total + len(usuarios_google_externos) + size - 1) // size
        
        return {
            "usuarios": todos_usuarios,
            "total": total + len(usuarios_google_externos),
            "page": page,
            "size": size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
    except Exception as e:
        logger.error(f"Error al listar usuarios: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener la lista de usuarios")


@router.put("/{usuario_id}/aprobar")
def aprobar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    """
    Aprueba un usuario (activa su cuenta).
    Usado principalmente para aprobar usuarios de Google pendientes.
    
    Args:
        usuario_id: ID del usuario a aprobar
        db: Sesión de base de datos
        
    Returns:
        Usuario aprobado
    """
    try:
        user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        if user.activo:
            return {
                "message": "El usuario ya está activo",
                "usuario": {
                    "idUsuario": user.id,
                    "nombre": user.nombre,
                    "correo": user.correo,
                    "activo": user.activo
                }
            }
        
        # Activar usuario
        user.activo = True
        db.commit()
        db.refresh(user)
        
        logger.info(f"Usuario aprobado: {user.correo} (ID: {user.id})")
        
        return {
            "message": "Usuario aprobado exitosamente",
            "usuario": {
                "idUsuario": user.id,
                "nombre": user.nombre,
                "correo": user.correo,
                "activo": user.activo
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al aprobar usuario: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al aprobar usuario")


@router.put("/{usuario_id}/rechazar")
def rechazar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    """
    Rechaza/desactiva un usuario.
    
    Args:
        usuario_id: ID del usuario a rechazar
        db: Sesión de base de datos
        
    Returns:
        Usuario rechazado
    """
    try:
        user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        if not user.activo:
            return {
                "message": "El usuario ya está inactivo",
                "usuario": {
                    "idUsuario": user.id,
                    "nombre": user.nombre,
                    "correo": user.correo,
                    "activo": user.activo
                }
            }
        
        # Desactivar usuario
        user.activo = False
        db.commit()
        db.refresh(user)
        
        logger.info(f"Usuario desactivado: {user.correo} (ID: {user.id})")
        
        return {
            "message": "Usuario desactivado exitosamente",
            "usuario": {
                "idUsuario": user.id,
                "nombre": user.nombre,
                "correo": user.correo,
                "activo": user.activo
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al rechazar usuario: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al rechazar usuario")


@router.get("/pendientes")
def obtener_usuarios_pendientes(
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de usuarios pendientes de aprobación (activo=False).
    
    Returns:
        Lista de usuarios pendientes
    """
    try:
        usuarios_pendientes = db.query(Usuario).filter(Usuario.activo == False).all()
        
        usuarios_lista = []
        for user in usuarios_pendientes:
            # Determinar tipo de usuario
            es_google = (
                user.documentoIdentidad and 
                user.documentoIdentidad.startswith("GOOGLE_") and 
                user.clave is None
            )
            
            usuarios_lista.append({
                "idUsuario": user.id,
                "nombre": user.nombre,
                "correo": user.correo,
                "documentoIdentidad": user.documentoIdentidad,
                "activo": user.activo,
                "tipo": "google" if es_google else "local"
            })
        
        return {
            "usuarios": usuarios_lista,
            "total": len(usuarios_lista)
        }
        
    except Exception as e:
        logger.error(f"Error al obtener usuarios pendientes: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener usuarios pendientes")


@router.get("/listar/completo")
async def listar_usuarios_completo(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(50, ge=1, le=100, description="Tamaño de página"),
    proviene: Optional[str] = Query(None, description="Filtrar por origen: 'local' o 'google'"),
    buscar: Optional[str] = Query(None, description="Buscar por nombre o correo"),
    db: Session = Depends(get_db)
):
    """
    Lista todos los usuarios del sistema combinando usuarios locales y de Google.
    
    Args:
        page: Número de página (por defecto 1)
        size: Tamaño de página (por defecto 50, máximo 100)
        proviene: Filtrar por origen - 'local' o 'google'
        buscar: Término de búsqueda por nombre o correo
    
    Returns:
        {
            "items": [
                {
                    "idUsuario": 1,
                    "nombre": "usuario",
                    "correo": "usuario@pucp.edu.pe",
                    "documentoIdentidad": null,
                    "activo": true,
                    "tipo": "local",
                    "permisos": ["permiso1", "permiso2"],
                    "roles": ["Rol 1"],
                    "proviene": "local"
                }
            ],
            "total": 10,
            "page": 1,
            "size": 50,
            "pages": 1
        }
    """
    try:
        # ============================================================
        # 1. OBTENER USUARIOS LOCALES DE LA BASE DE DATOS
        # ============================================================
        query = db.query(Usuario).options(
            selectinload(Usuario.permisos),
            selectinload(Usuario.roles).selectinload(Rol.permisos)
        )
        
        # Aplicar búsqueda si existe
        if buscar:
            search_filter = or_(
                Usuario.nombre.ilike(f"%{buscar}%"),
                Usuario.correo.ilike(f"%{buscar}%")
            )
            query = query.filter(search_filter)
        
        usuarios_locales = query.all()
        
        usuarios_lista = []
        for user in usuarios_locales:
            # Determinar tipo de usuario
            es_google = (
                user.documentoIdentidad and 
                user.documentoIdentidad.startswith("GOOGLE_") and 
                user.clave is None
            )
            
            # Get permissions
            direct_perms = {p.descripcion for p in user.permisos if hasattr(p, "descripcion")}
            role_perms = set()
            for rol in user.roles:
                for p in rol.permisos:
                    if hasattr(p, "descripcion"):
                        role_perms.add(p.descripcion)
            permisos = sorted(list(direct_perms | role_perms))
            
            # Get role names
            roles = sorted([rol.nombre for rol in user.roles if hasattr(rol, "nombre")])
            
            usuario_data = {
                "idUsuario": user.id,
                "nombre": user.nombre,
                "correo": user.correo,
                "documentoIdentidad": user.documentoIdentidad,
                "activo": user.activo,
                "tipo": "google" if es_google else "local",
                "permisos": permisos,
                "roles": roles,
                "proviene": "local"  # Todos los usuarios en la BD local provienen de "local"
            }
            
            usuarios_lista.append(usuario_data)
        
        # ============================================================
        # 2. OBTENER USUARIOS DEL SERVICIO DE GOOGLE
        # ============================================================
        usuarios_google_externos = []
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                # Llamar al servicio de autenticación de Google
                response = await client.get(f"{GOOGLE_AUTH_SERVICE_URL}/auth/users/list")
                
                if response.status_code == 200:
                    google_users_data = response.json()
                    google_users = google_users_data.get("users", [])
                    
                    # Obtener correos de usuarios locales para evitar duplicados
                    correos_locales = {u["correo"].lower() for u in usuarios_lista if u["correo"]}
                    
                    for gu in google_users:
                        email = gu.get("email", "")
                        
                        # Solo agregar si no existe en la BD local
                        if email.lower() not in correos_locales:
                            # Aplicar búsqueda si existe
                            if buscar:
                                nombre = gu.get("name", "")
                                if buscar.lower() not in email.lower() and buscar.lower() not in nombre.lower():
                                    continue
                            
                            google_user_id = gu.get('id', '')
                            usuarios_google_externos.append({
                                "idUsuario": google_user_id,  # Usar el ID del servicio auth-google
                                "nombre": gu.get("name", email.split("@")[0]),
                                "correo": email,
                                "documentoIdentidad": f"GOOGLE_{google_user_id}",
                                "activo": False,  # No están en BD local
                                "tipo": "google",
                                "permisos": [],
                                "roles": [],
                                "proviene": "google"
                            })
                
        except httpx.TimeoutException:
            logger.warning("Timeout al conectar con el servicio de Google")
        except httpx.RequestError as e:
            logger.warning(f"Error al conectar con el servicio de Google: {e}")
        except Exception as e:
            logger.error(f"Error inesperado al obtener usuarios de Google: {e}")
        
        # ============================================================
        # 3. COMBINAR Y FILTRAR POR ORIGEN
        # ============================================================
        todos_usuarios = usuarios_lista + usuarios_google_externos
        
        # Filtrar por origen si se especifica
        if proviene:
            proviene_lower = proviene.lower()
            if proviene_lower in ["local", "google"]:
                todos_usuarios = [u for u in todos_usuarios if u["proviene"] == proviene_lower]
        
        # ============================================================
        # 4. APLICAR PAGINACIÓN
        # ============================================================
        total = len(todos_usuarios)
        total_pages = (total + size - 1) // size if total > 0 else 1
        
        # Calcular offset
        offset = (page - 1) * size
        usuarios_paginados = todos_usuarios[offset:offset + size]
        
        return {
            "items": usuarios_paginados,
            "total": total,
            "page": page,
            "size": size,
            "pages": total_pages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al listar usuarios completo: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener la lista completa de usuarios")


@router.get("/clave_crm")
def listar_claves_crm(db: Session = Depends(get_db)):
    """
    Lista todas las claves CRM únicas de la tabla usuario.
    Retorna solo las claves que no son NULL o vacías.
    """
    try:
        # Obtener todas las claves únicas que no sean NULL
        claves = db.query(Usuario.clave).filter(
            Usuario.clave.isnot(None),
            Usuario.clave != ""
        ).distinct().all()
        
        # Convertir a lista simple
        claves_list = [clave[0] for clave in claves if clave[0]]
        
        logger.info(f"Claves CRM encontradas: {len(claves_list)}")
        
        return {
            "claves": sorted(claves_list),  # Ordenadas alfabéticamente
            "total": len(claves_list)
        }
    except Exception as e:
        logger.error(f"Error al listar claves CRM: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener las claves CRM")


@router.put("/google/{user_id}/asignar-clave")
async def asignar_clave_crm_google(
    user_id: str,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Asigna una clave CRM a un usuario de Google en el servicio auth-google.
    Este endpoint actúa como proxy y añade la autenticación necesaria.
    
    Args:
        user_id: ID del usuario en el servicio auth-google
        data: {"clave": "clave_crm_a_asignar"}
    """
    import os
    clave = data.get("clave")
    
    if not clave:
        raise HTTPException(status_code=400, detail="Clave requerida")
    
    # Obtener API key de variable de entorno
    service_api_key = os.getenv("AUTH_SERVICE_API_KEY", "change-this-to-a-secure-random-key-in-production")
    
    try:
        logger.info(f"Asignando clave '{clave}' al usuario Google ID: {user_id}")
        
        # Llamar al servicio de Google con la estructura correcta y autenticación
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{GOOGLE_AUTH_SERVICE_URL}/auth/users/{user_id}/key_crm",
                json={"key_crm": clave},
                headers={
                    "Content-Type": "application/json",
                    "X-Service-Key": service_api_key
                },
                timeout=10.0
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                error_detail = response.json().get("detail", "Error desconocido") if response.text else "Error al comunicarse con el servicio"
                logger.error(f"Error del servicio auth-google: {error_detail}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Error del servicio de autenticación: {error_detail}"
                )
            
            result = response.json()
            logger.info(f"Clave asignada exitosamente: {result}")
            
            return {
                "message": "Clave CRM asignada exitosamente",
                "user_id": user_id,
                "key_crm": clave,
                "user_data": result
            }
            
    except httpx.RequestError as e:
        logger.error(f"Error de conexión con el servicio de Google: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Servicio de autenticación de Google no disponible"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al asignar clave CRM: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")




