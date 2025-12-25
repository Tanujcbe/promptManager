"""
JWT Security module for Supabase token validation.
Provides FastAPI dependency for extracting authenticated user from JWT.
"""
import logging
from datetime import datetime, timezone
from typing import Annotated

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db

# Setup logger
logger = logging.getLogger(__name__)

# HTTP Bearer scheme for JWT tokens
security = HTTPBearer()

import ssl
import certifi

# Cache for JWKS client
_jwks_client = None


def get_jwks_client() -> PyJWKClient:
    """
    Get or create the PyJWKClient instance.
    """
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        
        # Create SSL context with certifi's CA bundle
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600, ssl_context=ssl_context)
    return _jwks_client


class AuthenticatedUser:
    """Represents the authenticated user extracted from JWT."""
    
    def __init__(self, user_id: str, email: str | None = None):
        self.user_id = user_id
        self.email = email
    
    def __repr__(self) -> str:
        return f"AuthenticatedUser(user_id={self.user_id}, email={self.email})"


def decode_supabase_jwt(token: str) -> dict:
    """
    Decode and validate a Supabase-issued JWT.
    Supports both HS256 (Secret) and ES256 (JWKS/Public Key).
    """
    settings = get_settings()
    
    try:
        # Get header to check algorithm
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
        
        if alg == "HS256":
            key = settings.supabase_jwt_secret
            algorithms = ["HS256"]
        elif alg == "ES256":
             # Use PyJWKClient to fetch signing key
            jwks_client = get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            key = signing_key.key
            algorithms = ["ES256"]
        else:
             raise jwt.PyJWTError(f"Unsupported algorithm: {alg}")

        payload = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience="authenticated",
            leeway=60 # Add 60s leeway for clock skew
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"JWT decoding failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
         logger.error(f"Unexpected JWT error: {e}")
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthenticatedUser:
    """
    FastAPI dependency to extract, validate JWT, and ensure user exists in DB.
    
    This is the ONLY place where user sync happens - not in individual endpoints.
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        AuthenticatedUser with user_id extracted from JWT 'sub' claim
        
    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    # Note: decode_supabase_jwt is synchronous now (PyJWKClient is sync by default used here)
    # If async is strictly needed, we'd need a different approach, but PyJWKClient is efficient with caching.
    payload = decode_supabase_jwt(credentials.credentials)
    
    user_id = payload.get("sub")
    if not user_id:
        logger.error("Token missing 'sub' claim (user_id)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email = payload.get("email")
    
    # Ensure user exists in local DB (sync from Supabase Auth)
    # Import here to avoid circular import
    from app.models.user import User
    
    stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        # Create new user record on first request
        user = User(id=user_id)
        db.add(user)
        await db.flush()
    
    return AuthenticatedUser(user_id=user_id, email=email)


# Type alias for dependency injection
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]



def create_access_token(user_id: str, email: str | None = None, expires_delta: int = 3600) -> str:
    """
    Generate a JWT token signed with Supabase JWT secret.
    ONLY for development/testing purposes.
    
    Args:
        user_id: The 'sub' claim for the JWT
        email: Optional email claim
        expires_delta: Seconds until token expires (default 1 hour)
        
    Returns:
        Encoded JWT string
    """
    settings = get_settings()
    
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_delta)).timestamp()),
    }
    
    return jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")
