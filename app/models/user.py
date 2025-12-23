"""
User model - synced with Supabase Auth.
The id field corresponds to the Supabase Auth user's UUID.
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, VersionMixin


class User(Base, TimestampMixin, SoftDeleteMixin, VersionMixin):
    """
    User model representing an authenticated user.
    
    The user ID is synced from Supabase Auth (not auto-generated).
    User records are created on first authenticated API request.
    """
    
    __tablename__ = "user"
    
    # ID is the Supabase Auth user_id (UUID as string)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Relationships
    personas: Mapped[list["Persona"]] = relationship(
        "Persona",
        back_populates="user",
        lazy="selectin",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="user",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"User(id={self.id})"


# Import at bottom to avoid circular imports
from app.models.persona import Persona
from app.models.message import Message
