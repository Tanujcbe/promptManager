"""
Message service - business logic for message CRUD operations.
All operations enforce user-scoped access control.
"""
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.models.message import Message, MessageType as ModelMessageType
from app.models.persona import Persona
from app.schemas.message import MessageCreate, MessageType, MessageUpdate


async def create_message(
    db: AsyncSession,
    user_id: str,
    data: MessageCreate,
) -> Message:
    """
    Create a new message for the user.
    
    Args:
        db: Database session
        user_id: Authenticated user's ID
        data: Message creation data
        
    Returns:
        Created message
        
    Raises:
        HTTPException: 400 if persona_id is invalid or not owned by user
    """
    # Validate persona if provided
    if data.persona_id is not None:
        stmt = select(Persona).where(
            Persona.id == data.persona_id,
            Persona.user_id == user_id,
            Persona.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        persona = result.scalar_one_or_none()
        
        if persona is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid persona_id: persona not found or not owned by user",
            )
    
    # Convert schema enum to model enum
    model_message_type = ModelMessageType(data.message_type.value)
    
    message = Message(
        user_id=user_id,
        persona_id=data.persona_id,
        message_type=model_message_type,
        title=data.title,
        content=data.content,
        summary=data.summary,
        starred=data.starred,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def get_message_by_id(
    db: AsyncSession,
    user_id: str,
    message_id: str,
) -> Message:
    """
    Get a message by ID, enforcing user ownership.
    
    Args:
        db: Database session
        user_id: Authenticated user's ID
        message_id: Message ID to retrieve
        
    Returns:
        Message if found and owned by user
        
    Raises:
        HTTPException: 404 if not found or not owned by user
    """
    stmt = select(Message).where(
        Message.id == message_id,
        Message.user_id == user_id,
        Message.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()
    
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )
    
    return message


async def list_messages(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    message_type: MessageType | None = None,
    starred: bool | None = None,
    persona_id: str | None = None,
) -> tuple[list[Message], int]:
    """
    List all messages for a user with pagination and optional filters.
    
    Args:
        db: Database session
        user_id: Authenticated user's ID
        page: Page number (1-indexed)
        page_size: Number of items per page
        message_type: Optional filter by message type
        starred: Optional filter by starred status
        persona_id: Optional filter by persona ID
        
    Returns:
        Tuple of (messages list, total count)
    """
    # Base conditions
    conditions = [
        Message.user_id == user_id,
        Message.deleted_at.is_(None),
    ]
    
    # Apply optional filters
    if message_type is not None:
        conditions.append(Message.message_type == ModelMessageType(message_type.value))
    
    if starred is not None:
        conditions.append(Message.starred == starred)
    
    if persona_id is not None:
        conditions.append(Message.persona_id == persona_id)
    
    # Count total
    count_stmt = select(func.count()).select_from(Message).where(*conditions)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    
    # Get paginated items
    offset = (page - 1) * page_size
    stmt = (
        select(Message)
        .where(*conditions)
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    messages = list(result.scalars().all())
    
    return messages, total


async def update_message(
    db: AsyncSession,
    user_id: str,
    message_id: str,
    data: MessageUpdate,
) -> Message:
    """
    Update a message, enforcing user ownership.
    Increments version on every update.
    
    Args:
        db: Database session
        user_id: Authenticated user's ID
        message_id: Message ID to update
        data: Update data (partial)
        
    Returns:
        Updated message
        
    Raises:
        HTTPException: 404 if not found or not owned by user
        HTTPException: 400 if persona_id is invalid
    """
    message = await get_message_by_id(db, user_id, message_id)
    
    update_data = data.model_dump(exclude_unset=True)
    
    # Validate persona_id if being updated
    if "persona_id" in update_data and update_data["persona_id"] is not None:
        stmt = select(Persona).where(
            Persona.id == update_data["persona_id"],
            Persona.user_id == user_id,
            Persona.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        persona = result.scalar_one_or_none()
        
        if persona is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid persona_id: persona not found or not owned by user",
            )
    
    # Update fields
    for field, value in update_data.items():
        setattr(message, field, value)
    
    # Always increment version on update
    message.version += 1
    message.updated_at = utc_now()
    
    await db.flush()
    await db.refresh(message)
    return message


async def delete_message(
    db: AsyncSession,
    user_id: str,
    message_id: str,
) -> None:
    """
    Soft delete a message, enforcing user ownership.
    
    Args:
        db: Database session
        user_id: Authenticated user's ID
        message_id: Message ID to delete
        
    Raises:
        HTTPException: 404 if not found or not owned by user
    """
    message = await get_message_by_id(db, user_id, message_id)
    
    message.deleted_at = utc_now()
    message.version += 1
    
    await db.flush()