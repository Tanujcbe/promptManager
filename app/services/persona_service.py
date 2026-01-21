"""
Persona service - business logic for persona CRUD operations.
All operations enforce user-scoped access control.
"""
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.models.persona import Persona
from app.schemas.persona import PersonaCreate, PersonaUpdate


async def create_persona(
    db: AsyncSession,
    user_id: str,
    data: PersonaCreate,
) -> Persona:
    """
    Create a new persona for the user.
    
    Args:
        db: Database session
        user_id: Authenticated user's ID
        data: Persona creation data
        
    Returns:
        Created persona
    """
    persona = Persona(
        id=data.id,
        user_id=user_id,
        name=data.name,
        description=data.description,
        persona_prompt=data.persona_prompt,
    )
    db.add(persona)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Persona with name '{data.name}' already exists",
        )
    await db.refresh(persona)
    return persona


async def get_persona_by_id(
    db: AsyncSession,
    user_id: str,
    persona_id: str,
) -> Persona:
    """
    Get a persona by ID, enforcing user ownership.
    
    Args:
        db: Database session
        user_id: Authenticated user's ID
        persona_id: Persona ID to retrieve
        
    Returns:
        Persona if found and owned by user
        
    Raises:
        HTTPException: 404 if not found or not owned by user
    """
    stmt = select(Persona).where(
        Persona.id == persona_id,
        Persona.user_id == user_id,
        Persona.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    persona = result.scalar_one_or_none()
    
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found",
        )
    
    return persona


async def list_personas(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Persona], int]:
    """
    List all personas for a user with pagination.
    
    Args:
        db: Database session
        user_id: Authenticated user's ID
        page: Page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Tuple of (personas list, total count)
    """
    # Count total
    count_stmt = select(func.count()).select_from(Persona).where(
        Persona.user_id == user_id,
        Persona.deleted_at.is_(None),
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    
    # Get paginated items
    offset = (page - 1) * page_size
    stmt = (
        select(Persona)
        .where(Persona.user_id == user_id, Persona.deleted_at.is_(None))
        .order_by(Persona.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    personas = list(result.scalars().all())
    
    return personas, total


async def update_persona(
    db: AsyncSession,
    user_id: str,
    persona_id: str,
    data: PersonaUpdate,
) -> Persona:
    """
    Update a persona, enforcing user ownership.
    
    Args:
        db: Database session
        user_id: Authenticated user's ID
        persona_id: Persona ID to update
        data: Update data (partial)
        
    Returns:
        Updated persona
        
    Raises:
        HTTPException: 404 if not found or not owned by user
    """
    persona = await get_persona_by_id(db, user_id, persona_id)
    
    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(persona, field, value)
    
    # Increment version
    persona.version += 1
    persona.updated_at = utc_now()
    
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Persona with name '{persona.name}' already exists",
        )
    await db.refresh(persona)
    return persona


async def delete_persona(
    db: AsyncSession,
    user_id: str,
    persona_id: str,
) -> None:
    """
    Soft delete a persona, enforcing user ownership.
    
    Args:
        db: Database session
        user_id: Authenticated user's ID
        persona_id: Persona ID to delete
        
    Raises:
        HTTPException: 404 if not found or not owned by user
    """
    persona = await get_persona_by_id(db, user_id, persona_id)
    
    persona.deleted_at = utc_now()
    persona.version += 1
    
    await db.flush()
