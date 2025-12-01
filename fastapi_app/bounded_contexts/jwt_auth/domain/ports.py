"""
Ports (interfaces) for JWT Authentication domain.

Ports define the contracts that adapters must implement.
Following Hexagonal Architecture, ports are in the domain layer
but implemented in the infrastructure layer.
"""
from abc import ABC, abstractmethod
from typing import Optional
from .value_objects import TokenPayload, UserId, Email
from .entities import AuthenticatedUser


class IJWTValidator(ABC):
    """
    Port for JWT token validation.
    
    This port defines the contract for validating JWT tokens.
    Implementations can use different libraries or services.
    """
    
    @abstractmethod
    def validate_token(self, token: str) -> TokenPayload:
        """
        Validate a JWT token and return its payload.
        
        Args:
            token: JWT token string
            
        Returns:
            TokenPayload: Validated token payload
            
        Raises:
            ValueError: If token is invalid or expired
        """
        pass
    
    @abstractmethod
    def extract_user_id(self, token: str) -> UserId:
        """
        Extract user ID from a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            UserId: User identifier from token
            
        Raises:
            ValueError: If token is invalid or doesn't contain user_id
        """
        pass
    
    @abstractmethod
    def extract_email(self, token: str) -> Email:
        """
        Extract email from a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Email: Email address from token
            
        Raises:
            ValueError: If token is invalid or doesn't contain email
        """
        pass


class IUserRepository(ABC):
    """
    Port for user repository operations.
    
    This port defines the contract for retrieving user information.
    Implementations can use database, external API, or other sources.
    """
    
    @abstractmethod
    def find_by_id(self, user_id: UserId) -> Optional[AuthenticatedUser]:
        """
        Find a user by their ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            Optional[AuthenticatedUser]: User if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find_by_email(self, email: Email) -> Optional[AuthenticatedUser]:
        """
        Find a user by their email.
        
        Args:
            email: User email address
            
        Returns:
            Optional[AuthenticatedUser]: User if found, None otherwise
        """
        pass

