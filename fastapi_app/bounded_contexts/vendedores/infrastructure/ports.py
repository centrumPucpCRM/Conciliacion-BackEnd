"""
Ports (interfaces) for external services in the Vendedores bounded context.
Following Hexagonal Architecture pattern.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..domain.entities import Vendedor


class IVendedorRepository(ABC):
    """
    Port for vendor repository operations.
    This is the interface that adapters must implement.
    """
    
    @abstractmethod
    async def obtener_todos(self) -> List[Vendedor]:
        """
        Obtiene todos los vendedores desde la API externa.
        
        Returns:
            List[Vendedor]: Lista de vendedores
            
        Raises:
            Exception: Si hay un error al obtener los datos
        """
        pass


class IVacacionService(ABC):
    """
    Port for vacation management service.
    This is the interface that adapters must implement.
    """
    
    @abstractmethod
    async def actualizar_estado_vacaciones(
        self, 
        party_number: str, 
        en_vacaciones: bool
    ) -> Dict[str, Any]:
        """
        Actualiza el estado de vacaciones de un vendedor.
        
        Args:
            party_number: Número de party del vendedor
            en_vacaciones: True si está en vacaciones, False si no
            
        Returns:
            Dict[str, Any]: Respuesta de la API externa
            
        Raises:
            Exception: Si hay un error al actualizar el estado
        """
        pass


