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
    
    def tiene_rol_daf(self, user_id: int) -> bool:
        """
        Verifica si un usuario tiene roles de DAF (Subdirector o Supervisor).
        
        Args:
            user_id: ID del usuario
            
        Returns:
            True si tiene rol de DAF, False en caso contrario
        """
        from ..models.rol_permiso import Rol
        
        usuario = self.obtener_usuario(user_id)
        if not usuario:
            print(f"DEBUG: Usuario {user_id} no encontrado")
            return False
        
        # Debug: imprimir todos los roles del usuario
        print(f"DEBUG: Usuario {user_id} ({usuario.nombre}) tiene roles:")
        for rol in usuario.roles:
            print(f"  - {rol.nombre}")
        
        # Verificar si el usuario tiene roles de DAF
        roles_daf = ["DAF - Supervisor", "DAF - Subdirector"]
        
        for rol in usuario.roles:
            if rol.nombre in roles_daf:
                print(f"DEBUG: Usuario tiene rol DAF: {rol.nombre}")
                return True
        
        print(f"DEBUG: Usuario NO tiene rol DAF")
        return False
    
    def tiene_rol_subdirector_comercial(self, user_id: int) -> bool:
        """
        Verifica si un usuario tiene el rol de Subdirector Comercial.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            True si tiene rol de Subdirector Comercial, False en caso contrario
        """
        usuario = self.obtener_usuario(user_id)
        if not usuario:
            return False
        
        for rol in usuario.roles:
            if rol.nombre == "Comercial - Subdirector":
                print(f"DEBUG: Usuario tiene rol Subdirector Comercial: {rol.nombre}")
                return True
        
        return False
    
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
    
    def obtener_todas_subdirecciones_propuesta(self, propuesta_id: int) -> List[str]:
        """
        Obtiene todas las subdirecciones únicas de los programas de una propuesta específica.
        
        Args:
            propuesta_id: ID de la propuesta
            
        Returns:
            Lista de todas las subdirecciones de la propuesta
        """
        print(f"DEBUG: Buscando todas las subdirecciones para propuesta {propuesta_id}")
        
        # Primero verificar cuántos programas hay en la propuesta
        total_programas = (
            self.db.query(Programa)
            .filter(Programa.idPropuesta == propuesta_id)
            .count()
        )
        print(f"DEBUG: Total de programas en propuesta {propuesta_id}: {total_programas}")
        
        subdirecciones = (
            self.db.query(distinct(Programa.subdireccion))
            .filter(Programa.idPropuesta == propuesta_id)
            .filter(Programa.subdireccion.isnot(None))
            .order_by(Programa.subdireccion)
            .all()
        )
        
        resultado = [subdir[0] for subdir in subdirecciones]
        print(f"DEBUG: Subdirecciones únicas encontradas: {resultado}")
        return resultado
    
    def obtener_subdirecciones_por_subdirector_asignado(self, user_id: int, propuesta_id: int) -> List[str]:
        """
        Obtiene las subdirecciones únicas de los programas donde el usuario es subdirector asignado
        en una propuesta específica.
        
        Args:
            user_id: ID del usuario
            propuesta_id: ID de la propuesta
            
        Returns:
            Lista de subdirecciones donde el usuario es subdirector asignado
        """
        print(f"DEBUG: Buscando subdirecciones donde usuario {user_id} es subdirector asignado en propuesta {propuesta_id}")
        
        subdirecciones = (
            self.db.query(distinct(Programa.subdireccion))
            .filter(Programa.idPropuesta == propuesta_id)
            .filter(Programa.idSubdirector == user_id)
            .filter(Programa.subdireccion.isnot(None))
            .order_by(Programa.subdireccion)
            .all()
        )
        
        resultado = [subdir[0] for subdir in subdirecciones]
        print(f"DEBUG: Subdirecciones donde es subdirector asignado: {resultado}")
        return resultado
    
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
    
    def obtener_subdirecciones_por_usuario_propuesta(self, user_id: int, propuesta_id: int) -> List[str]:
        """
        Obtiene las subdirecciones únicas de los programas donde el usuario tiene permisos
        en una propuesta específica.
        
        Lógica de negocio:
        1. Si el usuario tiene rol de DAF (Subdirector o Supervisor): retorna TODAS las subdirecciones de la propuesta
        2. Si el usuario tiene rol de Subdirector Comercial: retorna solo las subdirecciones donde es subdirector asignado
        3. Si no tiene ninguno de los anteriores: busca programas donde el usuario sea JP o Subdirector
        
        Args:
            user_id: ID del usuario
            propuesta_id: ID de la propuesta
            
        Returns:
            Lista de subdirecciones únicas según los permisos del usuario
        """
        print(f"DEBUG: Obteniendo subdirecciones para usuario {user_id} en propuesta {propuesta_id}")
        
        # Verificar si el usuario tiene rol de DAF
        if self.tiene_rol_daf(user_id):
            print(f"DEBUG: Usuario es DAF, obteniendo todas las subdirecciones de la propuesta")
            subdirecciones = self.obtener_todas_subdirecciones_propuesta(propuesta_id)
            print(f"DEBUG: Subdirecciones encontradas para DAF: {subdirecciones}")
            return subdirecciones
        
        # Verificar si el usuario tiene rol de Subdirector Comercial
        if self.tiene_rol_subdirector_comercial(user_id):
            print(f"DEBUG: Usuario es Subdirector Comercial, verificando si también es JP")
            
            # Verificar si también es Jefe de Producto
            usuario = self.obtener_usuario(user_id)
            es_tambien_jp = False
            if usuario:
                for rol in usuario.roles:
                    if rol.nombre == "Comercial - Jefe de producto":
                        es_tambien_jp = True
                        break
            
            if es_tambien_jp:
                print(f"DEBUG: Usuario es Subdirector Comercial Y Jefe de Producto, concatenando ambos")
                # Obtener subdirecciones como subdirector y como JP
                from sqlalchemy import or_
                
                subdirecciones = (
                    self.db.query(distinct(Programa.subdireccion))
                    .filter(Programa.idPropuesta == propuesta_id)
                    .filter(
                        or_(
                            Programa.idSubdirector == user_id,
                            Programa.idJefeProducto == user_id
                        )
                    )
                    .filter(Programa.subdireccion.isnot(None))
                    .order_by(Programa.subdireccion)
                    .all()
                )
                
                resultado = [subdir[0] for subdir in subdirecciones]
                print(f"DEBUG: Subdirecciones encontradas para Subdirector+JP: {resultado}")
                return resultado
            else:
                print(f"DEBUG: Usuario es solo Subdirector Comercial, filtrando por programas asignados")
                subdirecciones = self.obtener_subdirecciones_por_subdirector_asignado(user_id, propuesta_id)
                print(f"DEBUG: Subdirecciones encontradas para Subdirector Comercial: {subdirecciones}")
                return subdirecciones
        
        print(f"DEBUG: Usuario NO es DAF ni Subdirector Comercial, aplicando filtro por permisos específicos")
        
        # Si no es DAF ni Subdirector Comercial, aplicar filtro por usuario (JP o Subdirector)
        from sqlalchemy import or_
        
        subdirecciones = (
            self.db.query(distinct(Programa.subdireccion))
            .filter(Programa.idPropuesta == propuesta_id)
            .filter(
                or_(
                    Programa.idJefeProducto == user_id,
                    Programa.idSubdirector == user_id
                )
            )
            .filter(Programa.subdireccion.isnot(None))
            .order_by(Programa.subdireccion)
            .all()
        )
        
        resultado = [subdir[0] for subdir in subdirecciones]
        print(f"DEBUG: Subdirecciones encontradas por permisos: {resultado}")
        return resultado
    
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

