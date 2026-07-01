"""Memory retrieval with semantic search + temporal filters."""

import asyncio
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text, update
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

        # 1. Semantic search via pgvector (isolated session to avoid poisoning main tx)
        try:
            async with async_session() as vs_session:
                semantic = await self._semantic_search(vs_session, character_id, query, top_k)
                results.extend(semantic)
        except Exception:
            pass

        async with async_session() as session:
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

        # Trigger decay asynchronously (non-blocking)
        asyncio.create_task(self.apply_decay(character_id))

        return unique

    async def _semantic_search(
        self, session: AsyncSession, character_id: str, query: str, top_k: int
    ) -> list[dict]:
        """Vector similarity search using pgvector."""
        from mnemosyne.memory.models import get_embedding
        embedding = await get_embedding(query)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        result = await session.execute(
            text("""
                SELECT id, type, content, metadata, importance,
                       1 - (embedding <=> CAST(:embedding AS vector)) as similarity
                FROM memories
                WHERE character_id = :char_id
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:embedding AS vector)
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

    async def apply_decay(self, character_id: str):
        """Apply importance decay based on time since last access.

        Formula: new_importance = importance * (0.95 ^ days_since_access)
        Memories with importance < 0.1 are candidates for cleanup.
        """
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Memory).where(
                        Memory.character_id == character_id,
                        Memory.last_accessed.isnot(None),
                    )
                )
                memories = result.scalars().all()
                now = datetime.now(timezone.utc)

                for m in memories:
                    if m.last_accessed is None:
                        continue
                    days_since = (now - m.last_accessed.replace(tzinfo=timezone.utc)).days
                    if days_since < 1:
                        continue
                    decay_factor = math.pow(0.95, days_since)
                    new_importance = m.importance * decay_factor
                    if new_importance < 0.01:
                        new_importance = 0.01  # Don't go to absolute zero
                    if abs(new_importance - m.importance) > 0.01:
                        await session.execute(
                            update(Memory)
                            .where(Memory.id == m.id)
                            .values(importance=round(new_importance, 4))
                        )

                await session.commit()
        except Exception:
            pass  # Non-critical, don't break conversation flow

    async def get_graph_data(self, character_id: str, max_nodes: int = 50) -> dict:
        """Get memory graph data for visualization.

        Returns {nodes: [...], edges: [...]}.
        """
        async with async_session() as session:
            # Get top memories by importance
            result = await session.execute(
                select(Memory)
                .where(Memory.character_id == character_id)
                .where(Memory.embedding.isnot(None))
                .order_by(Memory.importance.desc())
                .limit(max_nodes)
            )
            memories = result.scalars().all()

            nodes = []
            for m in memories:
                nodes.append({
                    "id": str(m.id),
                    "type": m.type,
                    "content": m.content[:100],
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                })

            # Calculate edges via cosine similarity
            edges = []
            if len(memories) >= 2:
                import numpy as np
                embeddings = []
                valid_nodes = []
                for m in memories:
                    if m.embedding is not None:
                        try:
                            vec = list(m.embedding) if hasattr(m.embedding, '__iter__') else []
                            if vec:
                                embeddings.append(vec)
                                valid_nodes.append(m)
                        except Exception:
                            continue

                if len(embeddings) >= 2:
                    embs = np.array(embeddings)
                    # Normalize
                    norms = np.linalg.norm(embs, axis=1, keepdims=True)
                    norms = np.where(norms == 0, 1, norms)
                    normalized = embs / norms
                    # Cosine similarity matrix
                    sim_matrix = normalized @ normalized.T

                    for i in range(len(valid_nodes)):
                        for j in range(i + 1, len(valid_nodes)):
                            sim = float(sim_matrix[i, j])
                            if sim > 0.5:
                                edges.append({
                                    "source": str(valid_nodes[i].id),
                                    "target": str(valid_nodes[j].id),
                                    "similarity": round(sim, 3),
                                })

            return {"nodes": nodes, "edges": edges}
