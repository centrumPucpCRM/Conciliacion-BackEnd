"""
Adapters for external services in the Vendedores bounded context.
These adapters implement the ports defined in ports.py.
"""
import requests
from typing import List, Dict, Any
from ..domain.entities import Vendedor
from ..infrastructure.ports import IVendedorRepository, IVacacionService


class VendedorRepositoryAdapter(IVendedorRepository):
    """
    Adapter for fetching vendors from external API.
    Implements IVendedorRepository port.
    """
    
    def __init__(self, api_url: str):
        """
        Initialize the adapter with the external API URL.
        
        Args:
            api_url: URL of the external API endpoint
        """
        self.api_url = api_url
    
    async def obtener_todos(self) -> List[Vendedor]:
        """
        Obtiene todos los vendedores desde la API externa.
        
        Returns:
            List[Vendedor]: Lista de vendedores
            
        Raises:
            Exception: Si hay un error al obtener los datos
        """
        try:
            response = requests.get(self.api_url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list):
                raise ValueError("Expected a list of vendors from API")
            
            vendedores = []
            for vendor_data in data:
                try:
                    vendedor = Vendedor(
                        nombre=vendor_data.get("PartyName", ""),
                        party_id=vendor_data.get("ResourcePartyId", ""),
                        party_number=vendor_data.get("ResourcePartyNumber", ""),
                        correo=vendor_data.get("ResourceEmail", ""),
                        vacaciones=vendor_data.get("CTREnVacaciones_c", False)
                    )
                    vendedores.append(vendedor)
                except ValueError as e:
                    # Skip invalid vendors but log the error
                    print(f"Warning: Skipping invalid vendor data: {e}")
                    continue
            
            return vendedores
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al obtener vendedores de la API externa: {str(e)}")
        except Exception as e:
            raise Exception(f"Error inesperado al procesar datos de vendedores: {str(e)}")


class VacacionServiceAdapter(IVacacionService):
    """
    Adapter for managing vacation status via external API.
    Implements IVacacionService port.
    """
    
    def __init__(self, api_url: str):
        """
        Initialize the adapter with the external API URL.
        
        Args:
            api_url: URL of the external API endpoint for vacation management
        """
        self.api_url = api_url
    
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
        if not party_number or not party_number.strip():
            raise ValueError("party_number is required")
        
        try:
            payload = {
                "resource_user_id": party_number,
                "CTREnVacaciones_c": en_vacaciones
            }
            
            # La API externa espera POST, aunque nuestro endpoint local es PATCH
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            response.raise_for_status()
            
            # Try to parse JSON response, if available
            try:
                return response.json()
            except ValueError:
                # If response is not JSON, return a success message
                return {
                    "success": True,
                    "message": f"Estado de vacaciones actualizado para party_number: {party_number}",
                    "en_vacaciones": en_vacaciones
                }
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al actualizar estado de vacaciones en la API externa: {str(e)}")
        except Exception as e:
            raise Exception(f"Error inesperado al procesar actualización de vacaciones: {str(e)}")

