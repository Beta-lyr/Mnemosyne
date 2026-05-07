"""SQLAlchemy database models."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    characters: Mapped[list["Character"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    personality: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    base_image_url: Mapped[str | None] = mapped_column(Text)
    voice_style: Mapped[dict] = mapped_column(JSONB, default=dict)
    mood_default: Mapped[str] = mapped_column(String(20), default="sweet")
    telegram_token: Mapped[str | None] = mapped_column(String(255))
    card_export: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="characters")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="character", cascade="all, delete-orphan")
    memories: Mapped[list["Memory"]] = relationship(back_populates="character", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)  # user / assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    has_image: Mapped[bool] = mapped_column(Boolean, default=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    character: Mapped["Character"] = relationship(back_populates="conversations")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # fact / feeling / event
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(1024))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_accessed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    character: Mapped["Character"] = relationship(back_populates="memories")
