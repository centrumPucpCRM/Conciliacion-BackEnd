"""
Value objects for Vendedores bounded context.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PartyNumber:
    """
    Value object representing a party number.
    """
    value: str
    
    def __post_init__(self):
        """Validate party number."""
        if not self.value or not self.value.strip():
            raise ValueError("Party number cannot be empty")
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class VacationStatus:
    """
    Value object representing vacation status.
    """
    value: bool
    
    def __str__(self) -> str:
        return "En vacaciones" if self.value else "Trabajando"


