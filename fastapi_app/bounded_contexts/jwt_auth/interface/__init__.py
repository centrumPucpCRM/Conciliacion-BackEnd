"""
Interface layer for JWT Authentication bounded context.
Contains controllers, routers, and FastAPI dependencies.
"""
from .router import router

__all__ = ["router"]

