"""
Message service - business logic for message CRUD operations.
All operations enforce user-scoped access control.
"""
from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.models.message import Message, MessageType as ModelMessageType
from app.models.persona import Persona
from app.schemas.message import MessageCreate, MessageType, MessageUpdate
from app.schemas.persona import PersonaCreate
from app.services.persona_service import create_persona


async def create_message(
    db: AsyncSession,
    user_id: str,
    data: MessageCreate,
) -> Message:
    """
    Create a new message for the user.
    New messages are always version -1 (Latest).
    """
    # Validate persona if provided
    persona_id = data.persona_id or user_id
    print(persona_id)
    if persona_id is not None:
        stmt = select(Persona).where(
            Persona.id == persona_id,
            Persona.user_id == user_id,
            Persona.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        persona = result.scalar_one_or_none()
        
        if persona is None:
            new_persona_data = PersonaCreate(name="Default Persona", description="Default Persona", persona_prompt=None)
            new_persona = await create_persona(db, user_id, new_persona_data)
            persona_id = new_persona.id
    
    # Convert schema enum to model enum
    model_message_type = ModelMessageType(data.message_type.value)
    message = Message(
        user_id=user_id,
        persona_id=persona_id,
        message_type=model_message_type,
        title=data.title,
        content=data.content,
        summary=data.summary,
        starred=data.starred,
        version=-1,  # Explicitly set as Latest
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def get_message_by_id(
    db: AsyncSession,
    user_id: str,
    message_id: str,
    version: int | None = None,
) -> Message:
    """
    Get a message by ID.
    Defaults to version -1 (Latest) if version is not specified.
    """
    target_version = version if version is not None else -1
    
    stmt = select(Message).where(
        Message.id == message_id,
        Message.version == target_version,
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
    List all messages for a user.
    Only returns Latest versions (version = -1).
    """
    persona_id = persona_id or user_id
    # Base conditions
    conditions = [
        Message.user_id == user_id,
        Message.deleted_at.is_(None),
        Message.version == -1,  # Only show latest
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
    Update a message.
    1. Archives current state as a history row (version > 0).
    2. Updates the Latest row (version = -1) with new data.
    """
    # 1. Fetch current latest message
    message = await get_message_by_id(db, user_id, message_id, version=-1)
    
    # 2. Determine next history version
    stmt = select(func.max(Message.version)).where(
        Message.id == message_id,
        Message.version > 0,
    )
    result = await db.execute(stmt)
    max_ver = result.scalar_one_or_none() or 0
    next_ver = max_ver + 1
    
    # 3. Archive current state as history
    history_msg = Message(
        id=message.id,
        version=next_ver,
        user_id=message.user_id,
        persona_id=message.persona_id,
        message_type=message.message_type,
        title=message.title,
        content=message.content,
        summary=message.summary,
        starred=message.starred,
        # Preserve original timestamps for history
        created_at=message.created_at,
        updated_at=message.updated_at,
    )
    db.add(history_msg)
    
    # 4. Update latest message
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
    
    for field, value in update_data.items():
        setattr(message, field, value)
    
    message.updated_at = utc_now()
    # version remains -1
    
    await db.flush()
    await db.refresh(message)
    return message


async def delete_message(
    db: AsyncSession,
    user_id: str,
    message_id: str,
) -> None:
    """
    Soft delete a message.
    Marks ALL versions (Latest and History) as deleted.
    """
    # Verify ownership (at least one version exists)
    stmt = select(Message).where(
        Message.id == message_id,
        Message.user_id == user_id,
        Message.deleted_at.is_(None)
    ).limit(1)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    # Soft delete all versions
    await db.execute(
        update(Message)
        .where(
            Message.id == message_id,
            Message.user_id == user_id
        )
        .values(deleted_at=utc_now())
    )
    
    await db.flush()


async def get_message_history(
    db: AsyncSession,
    user_id: str,
    message_id: str,
    page: int = 1,
    page_size: int = 5,
) -> tuple[list[Message], int]:
    """
    Get version history for a message.
    Returns versions >= 0, paginated.
    """
    # Verify the message exists and belongs to the user (check any version)
    # We check version -1 (latest) to ensure the message isn't fully hard-deleted 
    # (though we use soft deletes) and to confirm ownership.
    latest_stmt = select(Message).where(
        Message.id == message_id,
        Message.version == -1,
        Message.user_id == user_id,
        Message.deleted_at.is_(None),
    )
    result = await db.execute(latest_stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    # Base conditions for history: correct ID, user, version >= 0, not deleted
    conditions = [
        Message.id == message_id,
        Message.user_id == user_id,
        Message.version >= 0,
        Message.deleted_at.is_(None),
    ]

    # Count total history versions
    count_stmt = select(func.count()).select_from(Message).where(*conditions)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Get paginated items, ordered by version descending (newest history first)
    offset = (page - 1) * page_size
    stmt = (
        select(Message)
        .where(*conditions)
        .order_by(Message.version.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    messages = list(result.scalars().all())

    return messages, total