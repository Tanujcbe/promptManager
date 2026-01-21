"""
Messages router - CRUD endpoints for message management.
"""
from fastapi import APIRouter, Query, status

from app.core.security import CurrentUser
from app.db.session import DBSession
from app.schemas.message import (
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    MessageType,
    MessageUpdate,
)
from app.services import message_service

router = APIRouter(tags=["Messages"])


@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    data: MessageCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> MessageResponse:
    """
    Save a new message (prompt or response).
    
    A message exists only when explicitly saved by the user.
    Optionally link to a persona for categorization.
    """
    message = await message_service.create_message(db, current_user.user_id, data)
    return MessageResponse.model_validate(message)


@router.get("/messages", response_model=MessageListResponse)
async def list_messages(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    message_type: MessageType | None = Query(None, description="Filter by message type"),
    starred: bool | None = Query(None, description="Filter by starred status"),
    persona_id: str | None = Query(None, description="Filter by persona ID"),
) -> MessageListResponse:
    """
    List all messages for the current user.
    
    Results are paginated and ordered by creation date (newest first).
    Optional filters: message_type, starred, persona_id.
    """
    messages, total = await message_service.list_messages(
        db,
        current_user.user_id,
        page,
        page_size,
        message_type,
        starred,
        persona_id,
    )
    
    return MessageListResponse(
        items=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/message/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: str,
    current_user: CurrentUser,
    db: DBSession,
    version: int | None = Query(None, description="Specific version to fetch (default: -1/Latest)"),
) -> MessageResponse:
    """
    Get a single message by ID.
    
    Returns 404 if the message doesn't exist or belongs to another user.
    """
    message = await message_service.get_message_by_id(
        db, 
        current_user.user_id, 
        message_id,
        version=version
    )
    return MessageResponse.model_validate(message)


@router.get("/message/{message_id}/history", response_model=MessageListResponse)
async def get_message_history(
    message_id: str,
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(5, ge=1, le=100, description="Items per page"),
) -> MessageListResponse:
    """
    Get version history for a message.
    
    Returns a paginated list of past versions (version >= 0).
    """
    messages, total = await message_service.get_message_history(
        db,
        current_user.user_id,
        message_id,
        page,
        page_size,
    )
    
    return MessageListResponse(
        items=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )



@router.put("/message/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: str,
    data: MessageUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> MessageResponse:
    """
    Update a message.
    
    Only provided fields will be updated. Version is always incremented.
    Use this endpoint to toggle starred status.
    Returns 404 if the message doesn't exist or belongs to another user.
    """
    message = await message_service.update_message(
        db, current_user.user_id, message_id, data
    )
    return MessageResponse.model_validate(message)


@router.delete("/message/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """
    Soft delete a message.
    
    The message is marked as deleted but not removed from the database.
    Returns 404 if the message doesn't exist or belongs to another user.
    """
    await message_service.delete_message(db, current_user.user_id, message_id)
