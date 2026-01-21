"""
Authentication schemas.
"""
from pydantic import BaseModel


class CurrentUserResponse(BaseModel):
    """Response schema for current authenticated user."""
    
    user_id: str
    email: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    
    detail: str


class TokenRequest(BaseModel):
    """Request schema for generating a test token."""
    
    user_id: str
    email: str | None = None
    expires_in: int = 3600


class TokenResponse(BaseModel):
    """Response schema for generated token."""
    
    access_token: str
    token_type: str = "bearer"
