"""
Persona model - user-defined prompt templates.
"""
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    ULIDMixin,
    VersionMixin,
)


class Persona(Base, ULIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    """
    Persona model representing a user-defined prompt template.
    
    Examples: Official, Side Project, Fun
    
    Each persona belongs to exactly one user and can be optionally
    linked to messages for categorization.
    """
    
    __tablename__ = "persona"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_persona_user_name"),
    )
    
    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Persona fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="personas")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="persona",
        lazy="selectin",    
    )
    
    def __repr__(self) -> str:
        return f"Persona(id={self.id}, name={self.name}, user_id={self.user_id})"


# Import at bottom to avoid circular imports
from app.models.user import User
from app.models.message import Message
