"""
Router para autenticación con Google.
Consume el servicio de autenticación de Google existente en http://localhost:8000
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response
from sqlalchemy.orm import Session
from fastapi_app.database import get_db
from fastapi_app.models.usuario import Usuario
from typing import Optional
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usuario", tags=["Google Authentication"])

# URL del servicio de autenticación de Google
GOOGLE_AUTH_SERVICE_URL = "http://localhost:8000"


@router.get("/login-google/init")
async def init_google_login(
    redirect_uri: Optional[str] = Query(None, description="URL de retorno después del login"),
    response: Response = None
):
    """
    Inicia el flujo de autenticación con Google.
    Redirige al servicio de autenticación de Google.
    
    Args:
        redirect_uri: URL a la que redirigir después del login exitoso
        
    Returns:
        Redirección a la URL de autenticación de Google
    """
    try:
        # Construir la URL de inicio de OAuth de Google
        auth_url = f"{GOOGLE_AUTH_SERVICE_URL}/auth/google"
        if redirect_uri:
            auth_url += f"?redirect_uri={redirect_uri}"
        
        # Redirigir al servicio de autenticación
        return {
            "auth_url": auth_url,
            "message": "Redirigir al usuario a auth_url para iniciar autenticación con Google"
        }
    except Exception as e:
        logger.error(f"Error al iniciar login con Google: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al iniciar autenticación con Google")


@router.post("/login-google")
async def login_google(
    session_token: Optional[str] = Query(None, description="Token de sesión de Google"),
    db: Session = Depends(get_db)
):
    """
    Endpoint de login con Google.
    Verifica la sesión de Google y retorna o crea el usuario en el sistema local.
    
    Este endpoint:
    1. Verifica la sesión de Google llamando al servicio de autenticación
    2. Busca o crea el usuario en la base de datos local
    3. Si el usuario es nuevo, lo crea con activo=False (pendiente de aprobación)
    4. Si el usuario existe pero activo=False, retorna error de pendiente aprobación
    5. Si el usuario existe y activo=True, retorna los datos del usuario con permisos
    
    Args:
        session_token: Token de sesión obtenido del servicio de Google
        db: Sesión de base de datos
        
    Returns:
        Información del usuario y estado de aprobación
    """
    if not session_token:
        raise HTTPException(status_code=400, detail="Token de sesión requerido")
    
    try:
        # Verificar la sesión con el servicio de autenticación de Google
        async with httpx.AsyncClient() as client:
            # Llamar al endpoint /auth/me del servicio de Google con el token de sesión
            headers = {
                "Cookie": f"auth_session={session_token}"
            }
            google_response = await client.get(
                f"{GOOGLE_AUTH_SERVICE_URL}/auth/me",
                headers=headers,
                timeout=10.0
            )
            
            if google_response.status_code != 200:
                raise HTTPException(
                    status_code=401,
                    detail="Sesión de Google inválida o expirada"
                )
            
            google_user = google_response.json()
        
        # Extraer información del usuario de Google
        email = google_user.get("email")
        name = google_user.get("name")
        google_id = google_user.get("id")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email no proporcionado por Google")
        
        # Buscar usuario en la base de datos local por correo
        user = db.query(Usuario).filter(Usuario.correo == email).first()
        
        if not user:
            # Usuario nuevo - crear con activo=False (pendiente de aprobación)
            # Usar el email como nombre de usuario y documentoIdentidad = google_id
            user = Usuario(
                nombre=email.split('@')[0],  # Usar parte del email como nombre
                correo=email,
                documentoIdentidad=f"GOOGLE_{google_id}" if google_id else f"GOOGLE_{email}",
                activo=False,  # Pendiente de aprobación del administrador
                clave=None  # Los usuarios de Google no tienen clave local
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"Nuevo usuario de Google creado: {email} (pendiente de aprobación)")
            
            return {
                "status": "pending_approval",
                "message": "Usuario registrado. Solicitud de acceso enviada al administrador.",
                "usuario": {
                    "idUsuario": user.id,
                    "nombre": user.nombre,
                    "correo": user.correo,
                    "activo": user.activo,
                    "tipo": "google"
                }
            }
        
        # Usuario existe - verificar si está activo
        if not user.activo:
            return {
                "status": "pending_approval",
                "message": "Tu solicitud de acceso está pendiente de aprobación por el administrador.",
                "usuario": {
                    "idUsuario": user.id,
                    "nombre": user.nombre,
                    "correo": user.correo,
                    "activo": user.activo,
                    "tipo": "google"
                }
            }
        
        # Usuario activo - obtener permisos
        # Get direct permissions
        direct_perms = set(p.descripcion for p in getattr(user, "permisos", []) if hasattr(p, "descripcion"))
        # Get permissions from roles
        role_perms = set()
        for rol in getattr(user, "roles", []):
            for p in getattr(rol, "permisos", []):
                if hasattr(p, "descripcion"):
                    role_perms.add(p.descripcion)
        permisos = list(direct_perms | role_perms)
        
        logger.info(f"Login exitoso con Google para usuario: {email}")
        
        return {
            "status": "success",
            "message": "Login exitoso",
            "usuario": {
                "idUsuario": user.id,
                "nombre": user.nombre,
                "correo": user.correo,
                "activo": user.activo,
                "tipo": "google",
                "permisos": permisos
            },
            "google_session_token": session_token
        }
        
    except httpx.RequestError as e:
        logger.error(f"Error al comunicarse con el servicio de Google: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Servicio de autenticación de Google no disponible"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login con Google: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/google/session")
async def verify_google_session(
    session_token: Optional[str] = Query(None, description="Token de sesión de Google"),
    db: Session = Depends(get_db)
):
    """
    Verifica una sesión activa de Google y retorna información del usuario.
    
    Args:
        session_token: Token de sesión de Google
        db: Sesión de base de datos
        
    Returns:
        Información del usuario si la sesión es válida
    """
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sesión requerido")
    
    try:
        # Verificar la sesión con el servicio de autenticación de Google
        async with httpx.AsyncClient() as client:
            headers = {
                "Cookie": f"auth_session={session_token}"
            }
            google_response = await client.get(
                f"{GOOGLE_AUTH_SERVICE_URL}/auth/me",
                headers=headers,
                timeout=10.0
            )
            
            if google_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
            
            google_user = google_response.json()
        
        # Buscar usuario en la base de datos local
        email = google_user.get("email")
        user = db.query(Usuario).filter(Usuario.correo == email).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado en el sistema")
        
        if not user.activo:
            return {
                "status": "pending_approval",
                "message": "Usuario pendiente de aprobación",
                "usuario": {
                    "idUsuario": user.id,
                    "correo": user.correo,
                    "activo": False
                }
            }
        
        # Get permissions
        direct_perms = set(p.descripcion for p in getattr(user, "permisos", []) if hasattr(p, "descripcion"))
        role_perms = set()
        for rol in getattr(user, "roles", []):
            for p in getattr(rol, "permisos", []):
                if hasattr(p, "descripcion"):
                    role_perms.add(p.descripcion)
        permisos = list(direct_perms | role_perms)
        
        return {
            "status": "active",
            "usuario": {
                "idUsuario": user.id,
                "nombre": user.nombre,
                "correo": user.correo,
                "activo": user.activo,
                "tipo": "google",
                "permisos": permisos
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al verificar sesión de Google: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al verificar sesión")
