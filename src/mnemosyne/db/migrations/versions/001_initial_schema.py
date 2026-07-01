"""Initial schema with pgvector.

Revision ID: 001
Revises:
Create Date: 2026-05-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Users table
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Characters table
    op.create_table(
        "characters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("personality", sa.Text, nullable=False),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("base_image_url", sa.Text),
        sa.Column("voice_style", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("mood_default", sa.String(20), server_default=sa.text("'sweet'")),
        sa.Column("telegram_token", sa.String(255)),
        sa.Column("card_export", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Conversations table
    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("character_id", UUID(as_uuid=True), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("has_image", sa.Boolean, server_default=sa.text("false")),
        sa.Column("image_url", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_character_id", "conversations", ["character_id"])
    op.create_index("ix_conversations_created_at", "conversations", ["created_at"])

    # Memories table with pgvector
    op.create_table(
        "memories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("character_id", UUID(as_uuid=True), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(1024)),
        sa.Column("metadata", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("importance", sa.Float, server_default=sa.text("0.5")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_accessed", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_memories_character_id", "memories", ["character_id"])
    op.create_index("ix_memories_type", "memories", ["type"])
    # IVFFlat index for vector similarity search
    op.execute("CREATE INDEX IF NOT EXISTS ix_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")


def downgrade() -> None:
    op.drop_table("memories")
    op.drop_table("conversations")
    op.drop_table("characters")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
