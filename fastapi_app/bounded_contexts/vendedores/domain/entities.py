"""
Domain entities for Vendedores bounded context.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Vendedor:
    """
    Entity representing a vendor/seller.
    """
    nombre: str
    party_id: str
    party_number: str
    correo: str
    vacaciones: bool
    
    def __post_init__(self):
        """Validate entity invariants."""
        if not self.party_number:
            raise ValueError("party_number is required")
        if not self.nombre:
            raise ValueError("nombre is required")

