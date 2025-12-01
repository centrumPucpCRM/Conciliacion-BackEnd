"""
Use cases for JWT Authentication bounded context.

Use cases contain the application logic and orchestrate domain entities
and infrastructure adapters. They are independent of frameworks.
"""
from typing import Optional
from ..domain.entities import AuthenticatedUser
from ..domain.value_objects import UserId, Email, TokenPayload
from ..domain.ports import IJWTValidator, IUserRepository


class ValidateTokenUseCase:
    """
    Use case: Validate JWT token.
    
    This use case validates a JWT token and returns the authenticated user.
    """
    
    def __init__(
        self,
        jwt_validator: IJWTValidator,
        user_repository: IUserRepository
    ):
        """
        Initialize use case with dependencies.
        
        Args:
            jwt_validator: JWT validator adapter
            user_repository: User repository adapter
        """
        self.jwt_validator = jwt_validator
        self.user_repository = user_repository
    
    def execute(self, token: str) -> AuthenticatedUser:
        """
        Execute the use case: validate token and get authenticated user.
        
        Args:
            token: JWT token string
            
        Returns:
            AuthenticatedUser: Authenticated user entity
            
        Raises:
            ValueError: If token is invalid, expired, or user not found
        """
        # Validate token and extract payload
        payload = self.jwt_validator.validate_token(token)
        
        # Find user by ID
        user = self.user_repository.find_by_id(payload.user_id)
        
        if not user:
            # If user not found by ID, try by email
            user = self.user_repository.find_by_email(payload.email)
            
            if not user:
                # Create user from token payload if not found
                user = AuthenticatedUser(
                    user_id=payload.user_id,
                    email=payload.email,
                    email_verified=True
                )
        
        return user


class GetCurrentUserUseCase:
    """
    Use case: Get current authenticated user from token.
    
    This use case extracts user information from a validated JWT token.
    """
    
    def __init__(self, jwt_validator: IJWTValidator):
        """
        Initialize use case with dependencies.
        
        Args:
            jwt_validator: JWT validator adapter
        """
        self.jwt_validator = jwt_validator
    
    def execute(self, token: str) -> AuthenticatedUser:
        """
        Execute the use case: get current user from token.
        
        Args:
            token: JWT token string
            
        Returns:
            AuthenticatedUser: Authenticated user entity
            
        Raises:
            ValueError: If token is invalid or expired
        """
        # Validate token
        payload = self.jwt_validator.validate_token(token)
        
        # Create user entity from token payload
        return AuthenticatedUser(
            user_id=payload.user_id,
            email=payload.email,
            email_verified=True
        )


class ExtractUserIdUseCase:
    """
    Use case: Extract user ID from JWT token.
    
    This use case extracts only the user ID from a validated token.
    """
    
    def __init__(self, jwt_validator: IJWTValidator):
        """
        Initialize use case with dependencies.
        
        Args:
            jwt_validator: JWT validator adapter
        """
        self.jwt_validator = jwt_validator
    
    def execute(self, token: str) -> UserId:
        """
        Execute the use case: extract user ID from token.
        
        Args:
            token: JWT token string
            
        Returns:
            UserId: User identifier
            
        Raises:
            ValueError: If token is invalid or doesn't contain user_id
        """
        return self.jwt_validator.extract_user_id(token)


class ExtractEmailUseCase:
    """
    Use case: Extract email from JWT token.
    
    This use case extracts only the email from a validated token.
    """
    
    def __init__(self, jwt_validator: IJWTValidator):
        """
        Initialize use case with dependencies.
        
        Args:
            jwt_validator: JWT validator adapter
        """
        self.jwt_validator = jwt_validator
    
    def execute(self, token: str) -> Email:
        """
        Execute the use case: extract email from token.
        
        Args:
            token: JWT token string
            
        Returns:
            Email: Email address
            
        Raises:
            ValueError: If token is invalid or doesn't contain email
        """
        return self.jwt_validator.extract_email(token)

