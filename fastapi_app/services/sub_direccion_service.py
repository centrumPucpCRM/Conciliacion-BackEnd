"""
Servicio de negocio para gestión de subdirecciones.
Contiene la lógica de negocio separada de la capa de presentación.
"""

from sqlalchemy.orm import Session
from sqlalchemy import distinct
from typing import List, Dict, Optional

from ..models.programa import Programa
from ..models.usuario import Usuario
from ..config.sub_direccion_config import (
    USUARIOS_ACCESO_TOTAL,
    MAPEO_USUARIOS_SUBDIRECCIONES
)


class SubDireccionService:
    """Servicio para gestionar subdirecciones y permisos de usuarios."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def obtener_usuario(self, user_id: int) -> Optional[Usuario]:
        """
        Obtiene un usuario por su ID.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Usuario si existe, None en caso contrario
        """
        return self.db.query(Usuario).filter(Usuario.id == user_id).first()
    
    def tiene_acceso_total(self, nombre_usuario: str) -> bool:
        """
        Verifica si un usuario tiene acceso total a todas las subdirecciones.
        
        Args:
            nombre_usuario: Nombre del usuario
            
        Returns:
            True si tiene acceso total, False en caso contrario
        """
        return nombre_usuario in USUARIOS_ACCESO_TOTAL
    
    def tiene_acceso_especifico(self, nombre_usuario: str) -> bool:
        """
        Verifica si un usuario tiene acceso a subdirecciones específicas.
        
        Args:
            nombre_usuario: Nombre del usuario
            
        Returns:
            True si tiene acceso específico, False en caso contrario
        """
        return nombre_usuario in MAPEO_USUARIOS_SUBDIRECCIONES
    
    def obtener_subdirecciones_asignadas(self, nombre_usuario: str) -> List[str]:
        """
        Obtiene las subdirecciones asignadas a un usuario específico.
        
        Args:
            nombre_usuario: Nombre del usuario
            
        Returns:
            Lista de subdirecciones asignadas
        """
        return MAPEO_USUARIOS_SUBDIRECCIONES.get(nombre_usuario, [])
    
    def obtener_todas_subdirecciones(self) -> List[str]:
        """
        Obtiene todas las subdirecciones únicas del sistema.
        
        Returns:
            Lista de todas las subdirecciones
        """
        subdirecciones = (
            self.db.query(distinct(Programa.subdireccion))
            .filter(Programa.subdireccion.isnot(None))
            .order_by(Programa.subdireccion)
            .all()
        )
        return [subdir[0] for subdir in subdirecciones]
    
    def obtener_subdirecciones_por_mapeo(self, subdirecciones_asignadas: List[str]) -> List[str]:
        """
        Obtiene subdirecciones filtradas por una lista de nombres asignados.
        
        Args:
            subdirecciones_asignadas: Lista de nombres de subdirecciones asignadas
            
        Returns:
            Lista de subdirecciones que existen en el sistema
        """
        subdirecciones = (
            self.db.query(distinct(Programa.subdireccion))
            .filter(Programa.subdireccion.in_(subdirecciones_asignadas))
            .filter(Programa.subdireccion.isnot(None))
            .order_by(Programa.subdireccion)
            .all()
        )
        return [subdir[0] for subdir in subdirecciones]
    
    def obtener_subdirecciones_por_jefatura(self, user_id: int) -> List[str]:
        """
        Obtiene subdirecciones donde el usuario es jefe de producto.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de subdirecciones donde es jefe de producto
        """
        subdirecciones = (
            self.db.query(distinct(Programa.subdireccion))
            .filter(Programa.idJefeProducto == user_id)
            .filter(Programa.subdireccion.isnot(None))
            .order_by(Programa.subdireccion)
            .all()
        )
        return [subdir[0] for subdir in subdirecciones]
    
    def obtener_subdirecciones_por_usuario(self, user_id: int) -> List[str]:
        """
        Obtiene las subdirecciones a las que un usuario tiene acceso.
        Aplica la lógica de negocio según el tipo de usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de subdirecciones accesibles para el usuario
        """
        # Obtener usuario
        usuario = self.obtener_usuario(user_id)
        
        if not usuario:
            return []
        
        # Caso 1: Usuario con acceso total
        if self.tiene_acceso_total(usuario.nombre):
            return self.obtener_todas_subdirecciones()
        
        # Caso 2: Usuario con subdirecciones específicas asignadas
        if self.tiene_acceso_especifico(usuario.nombre):
            subdirecciones_asignadas = self.obtener_subdirecciones_asignadas(usuario.nombre)
            return self.obtener_subdirecciones_por_mapeo(subdirecciones_asignadas)
        
        # Caso 3: Usuario con acceso por jefatura de producto
        return self.obtener_subdirecciones_por_jefatura(user_id)
    
    def formatear_respuesta(self, subdirecciones: List[str]) -> Dict:
        """
        Formatea la lista de subdirecciones al formato de respuesta esperado.
        
        Args:
            subdirecciones: Lista de nombres de subdirecciones
            
        Returns:
            Diccionario con formato de respuesta
        """
        items = [
            {"sub-direccion": subdir}
            for subdir in subdirecciones
        ]
        return {"items": items}

