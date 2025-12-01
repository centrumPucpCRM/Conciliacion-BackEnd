"""
Application services (use cases) for Vendedores bounded context.
This layer contains the business logic and orchestrates domain entities and infrastructure adapters.
"""
from typing import List, Dict, Any
from ..domain.entities import Vendedor
from ..infrastructure.ports import IVendedorRepository, IVacacionService


class VendedorService:
    """
    Application service for vendor operations.
    Orchestrates the use cases for vendor management.
    """
    
    def __init__(
        self, 
        vendedor_repository: IVendedorRepository,
        vacacion_service: IVacacionService
    ):
        """
        Initialize the service with required dependencies.
        
        Args:
            vendedor_repository: Repository for fetching vendors
            vacacion_service: Service for managing vacation status
        """
        self.vendedor_repository = vendedor_repository
        self.vacacion_service = vacacion_service
    
    async def listar_vendedores(self) -> List[Dict[str, Any]]:
        """
        Use case: List all vendors.
        
        Returns:
            List[Dict[str, Any]]: List of vendors in dictionary format
            
        Raises:
            Exception: If there's an error fetching vendors
        """
        vendedores = await self.vendedor_repository.obtener_todos()
        
        # Convert entities to dictionaries for API response
        return [
            {
                "nombre": v.nombre,
                "party_id": v.party_id,
                "party_number": v.party_number,
                "correo": v.correo,
                "vacaciones": v.vacaciones
            }
            for v in vendedores
        ]
    
    async def actualizar_vacaciones(
        self, 
        party_number: str, 
        en_vacaciones: bool
    ) -> Dict[str, Any]:
        """
        Use case: Update vacation status for a vendor.
        
        Args:
            party_number: Party number of the vendor
            en_vacaciones: True if on vacation, False otherwise
            
        Returns:
            Dict[str, Any]: Response from the external API
            
        Raises:
            ValueError: If party_number is invalid
            Exception: If there's an error updating the status
        """
        if not party_number or not party_number.strip():
            raise ValueError("party_number is required")
        
        result = await self.vacacion_service.actualizar_estado_vacaciones(
            party_number=party_number,
            en_vacaciones=en_vacaciones
        )
        
        return result


