"""
Propuesta Filter Service

This service handles the filtering logic for propuesta states according to business rules:
- By default, exclude states CONCILIADA and CANCELADA
- When explicitly requesting CONCILIADA or CANCELADA, show only those states
- Maintain clean separation of concerns and reusability
"""

from typing import List, Optional
from sqlalchemy.orm import Query
from sqlalchemy import and_, or_
from ..models.propuesta import Propuesta, EstadoPropuesta


class PropuestaFilterService:
    """Service for handling propuesta state filtering logic"""
    
    # Constants for excluded states by default (using names instead of IDs)
    EXCLUDED_STATES_BY_DEFAULT = ["CONCILIADA", "CANCELADA"]
    
    # LOV (List of Values) for all available states
    ESTADO_LOV = {
        "PROGRAMADA": 1,
        "GENERADA": 2,
        "PRECONCILIADA": 3,
        "APROBADA": 4,
        "CONCILIADA": 5,
        "CANCELADA": 6
    }
    
    @classmethod
    def apply_state_filter(
        cls, 
        query: Query, 
        estado_names: Optional[List[str]] = None
    ) -> Query:
        """
        Apply state filtering logic to a propuesta query.
        
        Args:
            query: The base SQLAlchemy query for Propuesta
            estado_names: Optional list of state names to filter by
            
        Returns:
            Modified query with state filtering applied
            
        Business Rules:
        - If no estado_names provided: exclude CONCILIADA and CANCELADA by default
        - If estado_names contains CONCILIADA or CANCELADA: show only those specific states
        - If estado_names contains other states: show only those states
        """
        if estado_names is None or len(estado_names) == 0:
            # Default behavior: exclude CONCILIADA and CANCELADA
            return cls._exclude_states_by_default(query)
        
        # Explicit state filtering: show only requested states
        return cls._filter_by_explicit_states(query, estado_names)
    
    @classmethod
    def _exclude_states_by_default(cls, query: Query) -> Query:
        """
        Exclude states CONCILIADA and CANCELADA from the query.
        
        Args:
            query: The base SQLAlchemy query for Propuesta
            
        Returns:
            Query with excluded states filtered out
        """
        return query.join(EstadoPropuesta).filter(
            ~EstadoPropuesta.nombre.in_(cls.EXCLUDED_STATES_BY_DEFAULT)
        )
    
    @classmethod
    def _filter_by_explicit_states(cls, query: Query, estado_names: List[str]) -> Query:
        """
        Filter query to show only the explicitly requested states.
        
        Args:
            query: The base SQLAlchemy query for Propuesta
            estado_names: List of state names to include
            
        Returns:
            Query filtered to only include requested states
        """
        return query.join(EstadoPropuesta).filter(EstadoPropuesta.nombre.in_(estado_names))
    
    @classmethod
    def get_available_states(cls, db_session) -> List[dict]:
        """
        Get all available estado propuesta states with their IDs and names.
        
        Args:
            db_session: SQLAlchemy database session
            
        Returns:
            List of dictionaries with id and nombre for each state
        """
        estados = db_session.query(EstadoPropuesta).order_by(EstadoPropuesta.id).all()
        return [
            {"id": estado.id, "nombre": estado.nombre} 
            for estado in estados
        ]
    
    @classmethod
    def get_estado_lov(cls) -> dict:
        """
        Get the LOV (List of Values) mapping for estado names to IDs.
        
        Returns:
            Dictionary mapping estado names to their IDs
        """
        return cls.ESTADO_LOV.copy()
    
    @classmethod
    def validate_state_names(cls, estado_names: List[str]) -> tuple[List[str], List[str]]:
        """
        Validate that the provided state names exist in the LOV.
        
        Args:
            estado_names: List of state names to validate
            
        Returns:
            Tuple of (valid_names, error_messages)
        """
        if not estado_names:
            return [], []
        
        valid_names = []
        errors = []
        
        for estado_name in estado_names:
            if estado_name in cls.ESTADO_LOV:
                valid_names.append(estado_name)
            else:
                errors.append(f"Estado '{estado_name}' no existe. Estados válidos: {', '.join(cls.ESTADO_LOV.keys())}")
        
        return valid_names, errors
