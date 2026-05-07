"""Memory retrieval with semantic search + temporal filters."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from mnemosyne.config import settings
from mnemosyne.db.models import Memory
from mnemosyne.db.session import async_session


class MemoryRetriever:
    """Retrieves relevant memories for conversation context injection."""

    async def retrieve(self, character_id: str, query: str, top_k: int = 5) -> list[dict]:
        """Retrieve memories using semantic search + temporal filters.

        Returns combined results:
        1. Semantic search (top_k similar memories)
        2. Recent feelings (last 3 days)
        3. Upcoming events (next 7 days)
        """
        results = []

        async with async_session() as session:
            # 1. Semantic search via pgvector
            semantic = await self._semantic_search(session, character_id, query, top_k)
            results.extend(semantic)

            # 2. Recent feelings
            feelings = await self._recent_feelings(session, character_id, days=3)
            results.extend(feelings)

            # 3. Upcoming events
            events = await self._upcoming_events(session, character_id, days=7)
            results.extend(events)

            # Update last_accessed for retrieved memories
            for r in results:
                await session.execute(
                    text("UPDATE memories SET last_accessed = NOW() WHERE id = :id"),
                    {"id": r["id"]},
                )
            await session.commit()

        # Deduplicate by id
        seen = set()
        unique = []
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique.append(r)
        return unique

    async def _semantic_search(
        self, session: AsyncSession, character_id: str, query: str, top_k: int
    ) -> list[dict]:
        """Vector similarity search using pgvector."""
        try:
            from mnemosyne.memory.models import get_embedding
            embedding = await get_embedding(query)
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            result = await session.execute(
                text("""
                    SELECT id, type, content, metadata, importance,
                           1 - (embedding <=> :embedding::vector) as similarity
                    FROM memories
                    WHERE character_id = :char_id
                      AND embedding IS NOT NULL
                    ORDER BY embedding <=> :embedding::vector
                    LIMIT :top_k
                """),
                {"char_id": character_id, "embedding": embedding_str, "top_k": top_k},
            )
            rows = result.fetchall()
            return [
                {
                    "id": str(row[0]),
                    "type": row[1],
                    "content": row[2],
                    "metadata": row[3] or {},
                    "importance": row[4],
                    "similarity": row[5],
                }
                for row in rows
                if row[5] > 0.5  # similarity threshold
            ]
        except Exception:
            # Fallback: keyword search if pgvector/embedding fails
            result = await session.execute(
                select(Memory)
                .where(Memory.character_id == character_id)
                .order_by(Memory.created_at.desc())
                .limit(top_k)
            )
            return [
                {
                    "id": str(m.id),
                    "type": m.type,
                    "content": m.content,
                    "metadata": m.metadata_ or {},
                    "importance": m.importance,
                }
                for m in result.scalars().all()
            ]

    async def _recent_feelings(
        self, session: AsyncSession, character_id: str, days: int = 3
    ) -> list[dict]:
        """Get recent feeling-type memories."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await session.execute(
            select(Memory)
            .where(
                Memory.character_id == character_id,
                Memory.type == "feeling",
                Memory.created_at >= cutoff,
            )
            .order_by(Memory.created_at.desc())
        )
        return [
            {"id": str(m.id), "type": m.type, "content": m.content, "metadata": m.metadata_ or {}}
            for m in result.scalars().all()
        ]

    async def _upcoming_events(
        self, session: AsyncSession, character_id: str, days: int = 7
    ) -> list[dict]:
        """Get upcoming event-type memories."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days)
        result = await session.execute(
            select(Memory)
            .where(
                Memory.character_id == character_id,
                Memory.type == "event",
            )
            .order_by(Memory.created_at.desc())
        )
        # Filter events by metadata date if available
        events = []
        for m in result.scalars().all():
            meta = m.metadata_ or {}
            event_date = meta.get("event_date")
            if event_date:
                try:
                    from datetime import datetime as dt
                    ed = dt.fromisoformat(event_date)
                    if now <= ed <= future:
                        events.append({
                            "id": str(m.id), "type": m.type, "content": m.content,
                            "metadata": meta,
                        })
                except (ValueError, TypeError):
                    events.append({"id": str(m.id), "type": m.type, "content": m.content, "metadata": meta})
            else:
                events.append({"id": str(m.id), "type": m.type, "content": m.content, "metadata": meta})
        return events
