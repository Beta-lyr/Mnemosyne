"""LangGraph-based dialog orchestration engine."""

import json
import re
from typing import Any

import litellm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemosyne.agent.prompts import IMAGE_SCENE_PROMPT, SYSTEM_PROMPT_TEMPLATE
from mnemosyne.agent.tools import TOOLS
from mnemosyne.config import settings
from mnemosyne.db.models import Character, Conversation
from mnemosyne.memory.retriever import MemoryRetriever
from mnemosyne.emotion.state import EmotionManager


class DialogEngine:
    """Core dialog engine for processing user messages and generating responses."""

    def __init__(self):
        self.memory_retriever = MemoryRetriever()
        self.emotion_manager = EmotionManager()

    async def process_message(
        self,
        character_id: str,
        user_message: str,
        session: AsyncSession,
    ) -> tuple[str, str | None]:
        """Process a user message and return (response_text, image_url_or_none)."""
        # 1. Get character
        result = await session.execute(select(Character).where(Character.id == character_id))
        character = result.scalar_one_or_none()
        if not character:
            return "Error: character not found", None

        # 2. Retrieve memories
        memories_text = await self._get_memories_text(character_id, user_message)

        # 3. Get emotion state
        mood = await self.emotion_manager.get_emotion(character_id, character.mood_default)

        # 4. Build system prompt
        system_prompt = character.system_prompt.format(
            user_name="用户",
            name=character.name,
            personality=character.personality,
            memories=memories_text,
            mood=mood,
        )

        # 5. Get recent conversation history (sliding window)
        history = await self._get_conversation_history(session, character_id, limit=20)

        # 6. Call LLM
        messages = [{"role": "system", "content": system_prompt}] + history
        messages.append({"role": "user", "content": user_message})

        response = await self._call_llm(messages)

        # 7. Handle tool calls (image generation)
        image_url = None
        if "[IMAGE_GENERATION_REQUESTED]" in response:
            scene = response.split("[IMAGE_GENERATION_REQUESTED]")[1].strip()
            response = response.split("[IMAGE_GENERATION_REQUESTED]")[0].strip()
            if not response:
                response = f"给你看一张我的照片~"
            # Queue image generation (async, don't block)
            image_url = await self._generate_image(character, scene, session)

        # 8. Update emotion
        await self.emotion_manager.update_from_conversation(character_id, user_message, response)

        # 9. Trigger async memory extraction (non-blocking)
        # This will be handled by APScheduler or background task

        return response, image_url

    async def _call_llm(self, messages: list[dict]) -> str:
        """Call LLM via LiteLLM."""
        try:
            response = await litellm.acompletion(
                model=f"{settings.llm_provider}/{settings.llm_model}" if settings.llm_provider != "openai" else settings.llm_model,
                messages=messages,
                api_key=settings.llm_api_key,
                api_base=settings.llm_base_url or None,
                tools=[self._format_tool_schema(t) for t in TOOLS],
                max_tokens=1024,
                temperature=0.8,
            )
            choice = response.choices[0]
            if choice.message.tool_calls:
                # Process tool calls
                tool_results = []
                for tc in choice.message.tool_calls:
                    func_name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    if func_name == "generate_image":
                        tool_results.append(f"[IMAGE_GENERATION_REQUESTED]{args.get('scene_prompt', '')}")
                    elif func_name == "save_memory":
                        tool_results.append(f"[MEMORY_SAVED]{args.get('memory_type', 'fact')}:{args.get('content', '')}")
                return " ".join(tool_results) if tool_results else choice.message.content or ""
            return choice.message.content or ""
        except Exception as e:
            return f"抱歉，我现在有点不舒服，稍后再聊好吗？({type(e).__name__})"

    def _format_tool_schema(self, tool) -> dict:
        """Convert langchain tool to OpenAI function schema."""
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.args_schema.model_json_schema() if hasattr(tool, 'args_schema') and tool.args_schema else {
                    "type": "object",
                    "properties": {},
                },
            },
        }

    async def _get_memories_text(self, character_id: str, query: str) -> str:
        """Retrieve and format memories for prompt injection."""
        memories = await self.memory_retriever.retrieve(character_id, query, top_k=5)
        if not memories:
            return "（暂无记忆）"
        return "\n".join(f"- {m['content']}" for m in memories)

    async def _get_conversation_history(
        self, session: AsyncSession, character_id: str, limit: int = 20
    ) -> list[dict]:
        """Get recent conversation history as message list."""
        result = await session.execute(
            select(Conversation)
            .where(Conversation.character_id == character_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )
        messages = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in messages]

    async def _generate_image(
        self, character: Character, scene: str, session: AsyncSession
    ) -> str | None:
        """Generate an image using the image engine."""
        if not character.base_image_url:
            return None
        try:
            from mnemosyne.image.providers import get_image_provider
            provider = get_image_provider(settings.image_provider)
            # Build full URL for local uploads
            base_url = f"http://localhost:{settings.web_port}{character.base_image_url}"
            image_url = await provider.generate(prompt=scene, reference_image_url=base_url)
            return image_url
        except Exception:
            return None
