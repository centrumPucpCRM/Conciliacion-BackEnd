"""
Adapters for JWT Authentication bounded context.

Adapters implement the ports (interfaces) defined in the domain layer.
They handle the technical details of JWT validation and user retrieval.
"""
import os
import jwt
from datetime import datetime
from typing import Optional, Dict, Any
from ..domain.ports import IJWTValidator, IUserRepository
from ..domain.value_objects import UserId, Email, TokenPayload
from ..domain.entities import AuthenticatedUser


class JWTValidatorAdapter(IJWTValidator):
    """
    Adapter for JWT token validation using PyJWT library.
    
    This adapter implements the IJWTValidator port and handles
    the technical details of JWT validation.
    """
    
    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256"):
        """
        Initialize JWT validator adapter.
        
        Args:
            secret_key: JWT secret key (defaults to JWT_SECRET_KEY env var)
            algorithm: JWT algorithm (defaults to HS256)
        """
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-min-32-chars")
        self.algorithm = algorithm
        
        if not self.secret_key or len(self.secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
    
    def validate_token(self, token: str) -> TokenPayload:
        """
        Validate JWT token and return payload.
        
        Args:
            token: JWT token string
            
        Returns:
            TokenPayload: Validated token payload
            
        Raises:
            ValueError: If token is invalid, expired, or malformed
        """
        try:
            # Decode and verify token
            decoded = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Extract required fields
            user_id_str = decoded.get("sub")
            email_str = decoded.get("email")
            token_type = decoded.get("type")
            exp_timestamp = decoded.get("exp")
            iat_timestamp = decoded.get("iat")
            
            if not user_id_str:
                raise ValueError("Token does not contain 'sub' (user_id)")
            if not email_str:
                raise ValueError("Token does not contain 'email'")
            if token_type != "access":
                raise ValueError(f"Invalid token type: {token_type}. Expected 'access'")
            
            # Create value objects
            user_id = UserId(user_id_str)
            email = Email(email_str)
            
            # Convert timestamps to datetime
            expires_at = datetime.utcfromtimestamp(exp_timestamp) if exp_timestamp else datetime.utcnow()
            issued_at = datetime.utcfromtimestamp(iat_timestamp) if iat_timestamp else datetime.utcnow()
            
            # Extract additional claims (everything except standard claims)
            standard_claims = {"sub", "email", "type", "exp", "iat", "nbf", "jti"}
            additional_claims = {
                k: v for k, v in decoded.items() 
                if k not in standard_claims
            }
            
            # Create and return token payload
            return TokenPayload(
                user_id=user_id,
                email=email,
                token_type=token_type,
                expires_at=expires_at,
                issued_at=issued_at,
                additional_claims=additional_claims
            )
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error validating token: {str(e)}")
    
    def extract_user_id(self, token: str) -> UserId:
        """
        Extract user ID from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            UserId: User identifier
            
        Raises:
            ValueError: If token is invalid or doesn't contain user_id
        """
        payload = self.validate_token(token)
        return payload.user_id
    
    def extract_email(self, token: str) -> Email:
        """
        Extract email from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Email: Email address
            
        Raises:
            ValueError: If token is invalid or doesn't contain email
        """
        payload = self.validate_token(token)
        return payload.email


class UserRepositoryAdapter(IUserRepository):
    """
    Adapter for user repository.
    
    This adapter implements the IUserRepository port.
    Currently returns None (users are created from token payload),
    but can be extended to query a database or external service.
    """
    
    def find_by_id(self, user_id: UserId) -> Optional[AuthenticatedUser]:
        """
        Find user by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            Optional[AuthenticatedUser]: User if found, None otherwise
        """
        # TODO: Implement database lookup if needed
        # For now, return None to let use case create user from token
        return None
    
    def find_by_email(self, email: Email) -> Optional[AuthenticatedUser]:
        """
        Find user by email.
        
        Args:
            email: User email address
            
        Returns:
            Optional[AuthenticatedUser]: User if found, None otherwise
        """
        # TODO: Implement database lookup if needed
        # For now, return None to let use case create user from token
        return None

