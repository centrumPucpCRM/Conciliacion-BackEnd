"""
FastAPI dependencies for JWT Authentication.

These dependencies integrate the use cases with FastAPI's dependency injection system.
They can be used in route handlers to get authenticated user information.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from ..application.use_cases import (
    ValidateTokenUseCase,
    GetCurrentUserUseCase,
    ExtractUserIdUseCase,
    ExtractEmailUseCase
)
from ..domain.entities import AuthenticatedUser
from ..domain.value_objects import UserId, Email
from ..infrastructure.adapters import JWTValidatorAdapter, UserRepositoryAdapter

# Initialize adapters (singleton pattern)
_jwt_validator = JWTValidatorAdapter()
_user_repository = UserRepositoryAdapter()

# Initialize use cases
_validate_token_use_case = ValidateTokenUseCase(_jwt_validator, _user_repository)
_get_current_user_use_case = GetCurrentUserUseCase(_jwt_validator)
_extract_user_id_use_case = ExtractUserIdUseCase(_jwt_validator)
_extract_email_use_case = ExtractEmailUseCase(_jwt_validator)

# HTTP Bearer security scheme
security = HTTPBearer()


def get_token_from_header(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Extract JWT token from Authorization header.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        str: JWT token string
        
    Raises:
        HTTPException: If token is not provided
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_current_user(
    token: str = Depends(get_token_from_header)
) -> AuthenticatedUser:
    """
    FastAPI dependency to get current authenticated user.
    
    Usage:
        @router.get("/endpoint")
        async def my_endpoint(user: AuthenticatedUser = Depends(get_current_user)):
            user_id = str(user.user_id)
            # Your logic here
    
    Args:
        token: JWT token from header
        
    Returns:
        AuthenticatedUser: Authenticated user entity
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        return _get_current_user_use_case.execute(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(
    token: str = Depends(get_token_from_header)
) -> UserId:
    """
    FastAPI dependency to get current user ID.
    
    Usage:
        @router.get("/endpoint")
        async def my_endpoint(user_id: UserId = Depends(get_current_user_id)):
            user_id_str = str(user_id)
            # Your logic here
    
    Args:
        token: JWT token from header
        
    Returns:
        UserId: User identifier value object
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        return _extract_user_id_use_case.execute(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_email(
    token: str = Depends(get_token_from_header)
) -> Email:
    """
    FastAPI dependency to get current user email.
    
    Usage:
        @router.get("/endpoint")
        async def my_endpoint(email: Email = Depends(get_current_user_email)):
            email_str = str(email)
            # Your logic here
    
    Args:
        token: JWT token from header
        
    Returns:
        Email: Email address value object
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        return _extract_email_use_case.execute(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id_str(
    token: str = Depends(get_token_from_header)
) -> str:
    """
    FastAPI dependency to get current user ID as string.
    
    Convenience dependency that returns user ID as string instead of UserId value object.
    
    Usage:
        @router.get("/endpoint")
        async def my_endpoint(user_id: str = Depends(get_current_user_id_str)):
            # Your logic here
    
    Args:
        token: JWT token from header
        
    Returns:
        str: User identifier as string
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        user_id = _extract_user_id_use_case.execute(token)
        return str(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_email_str(
    token: str = Depends(get_token_from_header)
) -> str:
    """
    FastAPI dependency to get current user email as string.
    
    Convenience dependency that returns email as string instead of Email value object.
    
    Usage:
        @router.get("/endpoint")
        async def my_endpoint(email: str = Depends(get_current_user_email_str)):
            # Your logic here
    
    Args:
        token: JWT token from header
        
    Returns:
        str: Email address as string
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        email = _extract_email_use_case.execute(token)
        return str(email)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

