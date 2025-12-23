"""
JWT Security module for Supabase token validation.
Provides FastAPI dependency for extracting authenticated user from JWT.
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db

# HTTP Bearer scheme for JWT tokens
security = HTTPBearer()


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
    
    Args:
        token: The JWT access token from Authorization header
        
    Returns:
        The decoded token payload
        
    Raises:
        HTTPException: If token is invalid, expired, or malformed
    """
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check expiration
    exp = payload.get("exp")
    if exp is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has no expiration",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
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
    payload = decode_supabase_jwt(credentials.credentials)
    
    user_id = payload.get("sub")
    if not user_id:
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
