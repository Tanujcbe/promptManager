"""
Message model - saved prompts and responses.
"""
import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    ULIDMixin,
    VersionMixin,
)


class MessageType(str, enum.Enum):
    """Type of message - either a prompt or a response."""
    PROMPT = "prompt"
    RESPONSE = "response"


class Message(Base, ULIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    """
    Message model representing a saved prompt or AI response.
    
    Messages are independent records - no conversations, no threads,
    no ordering dependencies. A message exists only when explicitly
    saved by the user.
    """
    
    __tablename__ = "message"
    
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
        Enum(MessageType, name="message_type", create_constraint=True),
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
        return f"Message(id={self.id}, title={self.title}, type={self.message_type})"


# Import at bottom to avoid circular imports
from app.models.user import User
from app.models.persona import Persona