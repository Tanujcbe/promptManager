"""
Authentication router - provides endpoint to verify JWT and get current user.
"""
from fastapi import APIRouter

from app.core.security import CurrentUser, create_access_token
from app.schemas.auth import CurrentUserResponse, TokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
) -> CurrentUserResponse:
    """
    Get the current authenticated user's information.
    
    This endpoint validates the JWT token and returns user info.
    User sync to local DB happens automatically in the auth dependency.
    """
    return CurrentUserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
    )


#TODO: Remove this endpoint in production
@router.post("/token", response_model=TokenResponse)
async def generate_test_token(
    data: TokenRequest,
) -> TokenResponse:
    """
    Generate a JWT token for testing/development.
    
    This endpoint uses the SUPABASE_JWT_SECRET to sign a token with the
    given user_id. Use this to obtain tokens for Postman or testing.
    """
    token = create_access_token(
        user_id=data.user_id,
        email=data.email,
        expires_delta=data.expires_in,
    )
    return TokenResponse(access_token=token)
