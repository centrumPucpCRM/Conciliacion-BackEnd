"""
Value Objects for JWT Authentication domain.

Value objects are immutable and represent concepts that are defined
by their attributes rather than their identity.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass(frozen=True)
class UserId:
    """
    Value object representing a user identifier.
    Immutable and validated.
    """
    value: str
    
    def __post_init__(self):
        """Validate user ID."""
        if not self.value or not isinstance(self.value, str):
            raise ValueError("User ID must be a non-empty string")
        if not self.value.strip():
            raise ValueError("User ID cannot be empty or whitespace")
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Email:
    """
    Value object representing an email address.
    Immutable and validated.
    """
    value: str
    
    def __post_init__(self):
        """Validate email format."""
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Email must be a non-empty string")
        if "@" not in self.value:
            raise ValueError("Email must contain @ symbol")
        if not self.value.strip():
            raise ValueError("Email cannot be empty or whitespace")
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TokenPayload:
    """
    Value object representing a JWT token payload.
    Immutable and validated.
    """
    user_id: UserId
    email: Email
    token_type: str
    expires_at: datetime
    issued_at: datetime
    additional_claims: Dict[str, Any]
    
    def __post_init__(self):
        """Validate token payload."""
        if self.token_type != "access":
            raise ValueError(f"Invalid token type: {self.token_type}. Expected 'access'")
        
        if self.expires_at <= self.issued_at:
            raise ValueError("Token expiration must be after issue time")
        
        # Note: Expiration check is done in the adapter, not here
        # to allow for more flexible error handling
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert payload to dictionary."""
        return {
            "sub": str(self.user_id),
            "email": str(self.email),
            "type": self.token_type,
            "exp": int(self.expires_at.timestamp()),
            "iat": int(self.issued_at.timestamp()),
            **self.additional_claims
        }

