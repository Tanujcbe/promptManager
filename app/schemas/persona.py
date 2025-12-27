"""
Persona schemas for request/response validation.
"""
from datetime import datetime

from pydantic import BaseModel, Field


class PersonaBase(BaseModel):
    """Base schema for persona fields."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    persona_prompt: str | None = Field(None, min_length=1)


class PersonaCreate(PersonaBase):
    """Schema for creating a new persona."""
    pass


class PersonaUpdate(BaseModel):
    """Schema for updating a persona. All fields are optional."""
    
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    persona_prompt: str | None = Field(None, min_length=1)


class PersonaResponse(PersonaBase):
    """Schema for persona response."""
    
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    version: int
    
    model_config = {"from_attributes": True}


class PersonaListResponse(BaseModel):
    """Schema for paginated list of personas."""
    
    items: list[PersonaResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
