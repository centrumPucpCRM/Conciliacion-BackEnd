"""
Router (controller) for JWT Authentication bounded context.

This router provides endpoints for JWT authentication and demonstrates
how to use the dependencies in protected endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from .dependencies import (
    get_current_user,
    get_current_user_id_str,
    get_current_user_email_str
)
from ..domain.entities import AuthenticatedUser
from ..domain.value_objects import UserId, Email

router = APIRouter(
    prefix="/api/jwt-auth",
    tags=["JWT Authentication"]
)


@router.get("/me", summary="Get current authenticated user")
async def get_me(
    user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current authenticated user information.
    
    This endpoint demonstrates how to use the get_current_user dependency
    to get the full authenticated user entity.
    
    Returns:
        Dict[str, Any]: User information
    """
    return user.to_dict()


@router.get("/user-id", summary="Get current user ID")
async def get_user_id(
    user_id: str = Depends(get_current_user_id_str)
) -> Dict[str, str]:
    """
    Get current user ID.
    
    This endpoint demonstrates how to use the get_current_user_id_str dependency
    to get only the user ID as a string.
    
    Returns:
        Dict[str, str]: User ID
    """
    return {"user_id": user_id}


@router.get("/user-email", summary="Get current user email")
async def get_user_email(
    email: str = Depends(get_current_user_email_str)
) -> Dict[str, str]:
    """
    Get current user email.
    
    This endpoint demonstrates how to use the get_current_user_email_str dependency
    to get only the email as a string.
    
    Returns:
        Dict[str, str]: Email address
    """
    return {"email": email}


@router.get("/health", summary="Health check")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for JWT authentication service.
    
    Returns:
        Dict[str, str]: Health status
    """
    return {
        "status": "healthy",
        "service": "jwt-authentication",
        "architecture": "hexagonal-ddd"
    }

