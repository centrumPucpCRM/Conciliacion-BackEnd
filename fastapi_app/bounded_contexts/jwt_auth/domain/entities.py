"""
Domain entities for JWT Authentication.

Entities are objects that have a unique identity and lifecycle.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from .value_objects import UserId, Email, TokenPayload


@dataclass
class AuthenticatedUser:
    """
    Entity representing an authenticated user.
    
    This entity has identity (user_id) and can have its state changed
    throughout its lifecycle.
    """
    user_id: UserId
    email: Email
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: bool = False
    authenticated_at: datetime = None
    
    def __post_init__(self):
        """Initialize entity."""
        if self.authenticated_at is None:
            self.authenticated_at = datetime.utcnow()
    
    def update_email(self, new_email: Email) -> None:
        """Update user email."""
        self.email = new_email
    
    def verify_email(self) -> None:
        """Mark email as verified."""
        self.email_verified = True
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.user_id is not None and self.email is not None
    
    def to_dict(self) -> dict:
        """Convert entity to dictionary."""
        return {
            "user_id": str(self.user_id),
            "email": str(self.email),
            "name": self.name,
            "picture": self.picture,
            "email_verified": self.email_verified,
            "authenticated_at": self.authenticated_at.isoformat() if self.authenticated_at else None
        }

