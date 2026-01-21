"""
Message model - saved prompts and responses.
"""
import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    generate_ulid,
)


class MessageType(str, enum.Enum):
    """Type of message - either a prompt or a response."""
    PROMPT = "prompt"
    RESPONSE = "response"


class Message(Base, TimestampMixin, SoftDeleteMixin):
    """
    Message model representing a saved prompt or AI response.
    
    Uses Composite Primary Key (id, version).
    - id: ULID, shared across versions of the same message.
    - version: -1 for Latest, >0 for History.
    """
    
    __tablename__ = "message"
    
    # Composite Primary Key
    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        default=generate_ulid,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=-1,  # Default to Latest
        nullable=False,
    )
    
    # Foreign key to user (required)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Foreign key to persona (optional)
    persona_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("persona.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Message fields
    message_type: Mapped[MessageType] = mapped_column(
        Enum(
            MessageType,
            name="message_type",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(String(10000), nullable=True)
    starred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="messages")
    persona: Mapped["Persona | None"] = relationship(
        "Persona",
        back_populates="messages",
    )
    
    def __repr__(self) -> str:
        return f"Message(id={self.id}, ver={self.version}, title={self.title})"


# Import at bottom to avoid circular imports
from app.models.user import User
from app.models.persona import Persona