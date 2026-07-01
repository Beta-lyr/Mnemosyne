"""Memory data models, schemas, and embedding utilities."""

import json

import litellm
from pydantic import BaseModel

from mnemosyne.config import settings


class MemoryCreate(BaseModel):
    character_id: str
    type: str  # fact / feeling / event
    content: str
    metadata: dict = {}
    importance: float = 0.5


class MemoryResponse(BaseModel):
    id: str
    character_id: str
    type: str
    content: str
    metadata: dict
    importance: float
    created_at: str


class ExtractionResult(BaseModel):
    facts: list[str] = []
    feelings: list[str] = []
    events: list[str] = []


async def get_embedding(text: str) -> list[float]:
    """Get embedding vector for text using configured provider."""
    if settings.embedding_provider == "openai":
        response = await litellm.aembedding(
            model=f"openai/{settings.embedding_model}",
            input=[text],
            api_key=settings.llm_api_key,
        )
        return response.data[0]["embedding"]
    else:
        # Local embedding via sentence-transformers
        return await _get_local_embedding(text)


_local_model = None


async def _get_local_embedding(text: str) -> list[float]:
    """Get embedding using local sentence-transformers model."""
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer(settings.embedding_model)
    embedding = _local_model.encode(text, normalize_embeddings=True)
    return embedding.tolist()
