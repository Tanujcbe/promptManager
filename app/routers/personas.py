"""
Personas router - CRUD endpoints for persona management.
"""
from fastapi import APIRouter, Query, status

from app.core.security import CurrentUser
from app.db.session import DBSession
from app.schemas.persona import (
    PersonaCreate,
    PersonaListResponse,
    PersonaResponse,
    PersonaUpdate,
)
from app.services import persona_service

router = APIRouter(tags=["Personas"])


@router.post("/personas", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
async def create_persona(
    data: PersonaCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> PersonaResponse:
    """
    Create a new persona.
    
    Personas are user-defined prompt templates that can be linked to messages.
    """
    persona = await persona_service.create_persona(db, current_user.user_id, data)
    return PersonaResponse.model_validate(persona)


@router.get("/personas", response_model=PersonaListResponse)
async def list_personas(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PersonaListResponse:
    """
    List all personas for the current user.
    
    Results are paginated and ordered by creation date (newest first).
    """
    personas, total = await persona_service.list_personas(
        db, current_user.user_id, page, page_size
    )
    
    return PersonaListResponse(
        items=[PersonaResponse.model_validate(p) for p in personas],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/persona/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> PersonaResponse:
    """
    Get a single persona by ID.
    
    Returns 404 if the persona doesn't exist or belongs to another user.
    """
    persona = await persona_service.get_persona_by_id(db, current_user.user_id, persona_id)
    return PersonaResponse.model_validate(persona)


@router.put("/persona/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    data: PersonaUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> PersonaResponse:
    """
    Update a persona.
    
    Only provided fields will be updated. Version is incremented.
    Returns 404 if the persona doesn't exist or belongs to another user.
    """
    persona = await persona_service.update_persona(
        db, current_user.user_id, persona_id, data
    )
    return PersonaResponse.model_validate(persona)


@router.delete("/persona/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(
    persona_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """
    Soft delete a persona.
    
    The persona is marked as deleted but not removed from the database.
    Returns 404 if the persona doesn't exist or belongs to another user.
    """
    await persona_service.delete_persona(db, current_user.user_id, persona_id)
