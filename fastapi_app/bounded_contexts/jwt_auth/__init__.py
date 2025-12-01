"""
JWT Authentication Bounded Context.

This bounded context handles JWT token validation and user authentication
using Hexagonal Architecture and Domain-Driven Design principles.

Structure:
- domain/: Domain entities, value objects, and repository interfaces
- application/: Use cases and application services
- infrastructure/: Adapters implementing ports (JWT validation, user repository)
- interface/: Controllers, routers, and FastAPI dependencies
"""

