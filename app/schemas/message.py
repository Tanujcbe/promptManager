"""
Message schemas for request/response validation.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Type of message."""
    PROMPT = "prompt"
    RESPONSE = "response"


class MessageBase(BaseModel):
    """Base schema for message fields."""
    
    message_type: MessageType
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    summary: str | None = Field(None, max_length=10000)
    starred: bool = False
    persona_id: str | None = None


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    pass


class MessageUpdate(BaseModel):
    """Schema for updating a message. All fields are optional."""
    
    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = Field(None, min_length=1)
    summary: str | None = Field(None, max_length=10000)
    starred: bool | None = None
    persona_id: str | None = None


class MessageResponse(BaseModel):
    """Schema for message response."""
    
    id: str
    user_id: str
    persona_id: str | None
    message_type: MessageType
    title: str
    content: str
    summary: str | None
    starred: bool
    created_at: datetime
    updated_at: datetime
    version: int
    
    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    """Schema for paginated list of messages."""
    
    items: list[MessageResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
