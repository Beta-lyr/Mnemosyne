"""LangGraph-based dialog orchestration engine."""

import json
import logging
import re
from typing import Any

import litellm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemosyne.agent.prompts import IMAGE_SCENE_PROMPT, SYSTEM_PROMPT_TEMPLATE
from mnemosyne.agent.tools import TOOLS
from mnemosyne.agent.persona_compiler import build_full_personality
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
    ) -> tuple[str, str | None, str | None, str | None]:
        """Process a user message and return (response_text, image_url, audio_url, video_url)."""
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
        full_personality = build_full_personality(
            character.personality,
            character.processed_personality,
            character.interaction_rules,
        )
        system_prompt = character.system_prompt.format(
            user_name="用户",
            name=character.name,
            personality=full_personality,
            memories=memories_text,
            mood=mood,
        )

        # 5. Get recent conversation history (sliding window)
        history = await self._get_conversation_history(session, character_id, limit=20)

        # 6. Call LLM
        messages = [{"role": "system", "content": system_prompt}] + history
        messages.append({"role": "user", "content": user_message})

        response = await self._call_llm(messages, user_message=user_message)

        # 7. Handle tool calls (image generation)
        image_url = None
        if "[IMAGE_GENERATION_REQUESTED]" in response:
            scene = response.split("[IMAGE_GENERATION_REQUESTED]")[1].strip()
            response = response.split("[IMAGE_GENERATION_REQUESTED]")[0].strip()
            if not response:
                response = f"给你看一张我的照片~"
            image_url = await self._generate_image(character, scene, session)

        # 7b. Handle audio generation
        audio_url = None
        if "[AUDIO_GENERATION_REQUESTED]" in response:
            audio_prompt = response.split("[AUDIO_GENERATION_REQUESTED]")[1].strip()
            response = response.split("[AUDIO_GENERATION_REQUESTED]")[0].strip()
            if not response:
                response = "给你听听~"
            audio_url = await self._generate_audio(audio_prompt)

        # 7c. Handle video generation
        video_url = None
        if "[VIDEO_GENERATION_REQUESTED]" in response:
            video_prompt = response.split("[VIDEO_GENERATION_REQUESTED]")[1].strip()
            response = response.split("[VIDEO_GENERATION_REQUESTED]")[0].strip()
            if not response:
                response = "给你看个视频~"
            video_url = await self._generate_video(video_prompt)

        # 7d. Handle scheduled messages
        if "[SCHEDULE_MESSAGE]" in response:
            schedule_str = response.split("[SCHEDULE_MESSAGE]")[1].strip()
            response = response.split("[SCHEDULE_MESSAGE]")[0].strip()
            try:
                info = json.loads(schedule_str)
                from mnemosyne.trigger.scheduler import get_scheduler
                scheduler = get_scheduler()
                if scheduler:
                    scheduler.add_dynamic_job(character_id, info["message"], info["delay"])
                    confirm = f"好的，我会在{info['delay']}分钟后提醒你~"
                    response = f"{response} {confirm}" if response else confirm
                else:
                    response = response or "抱歉，定时功能暂时不可用~"
            except Exception as e:
                logging.getLogger(__name__).error("Failed to schedule message: %s", e)

        # 8. Update emotion
        await self.emotion_manager.update_from_conversation(character_id, user_message, response)

        # 9. Trigger async memory extraction (non-blocking)
        # This will be handled by APScheduler or background task

        return response, image_url, audio_url, video_url

    async def _call_llm(self, messages: list[dict], user_message: str = "") -> str:
        """Call LLM via LiteLLM."""
        logger = logging.getLogger(__name__)
        try:
            response = await litellm.acompletion(
                model=f"{settings.llm_provider}/{settings.llm_model}",
                messages=messages,
                api_key=settings.llm_api_key,
                api_base=settings.llm_base_url or None,
                tools=[self._format_tool_schema(t) for t in TOOLS],
                max_tokens=1024,
                temperature=0.8,
            )
            choice = response.choices[0]
            logger.info("LLM response: tool_calls=%s, content=%s",
                        bool(choice.message.tool_calls),
                        (choice.message.content or "")[:100])
            if choice.message.tool_calls:
                # Process tool calls
                tool_results = []
                for tc in choice.message.tool_calls:
                    func_name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    logger.info("Tool call: %s(%s)", func_name, args)
                    if func_name == "generate_image":
                        tool_results.append(f"[IMAGE_GENERATION_REQUESTED]{args.get('scene_prompt', '')}")
                    elif func_name == "save_memory":
                        tool_results.append(f"[MEMORY_SAVED]{args.get('memory_type', 'fact')}:{args.get('content', '')}")
                    elif func_name == "schedule_message":
                        tool_results.append(f"[SCHEDULE_MESSAGE]{json.dumps({'delay': args.get('delay_minutes', 1), 'message': args.get('message', '')}, ensure_ascii=False)}")
                    elif func_name == "generate_audio":
                        tool_results.append(f"[AUDIO_GENERATION_REQUESTED]{args.get('audio_prompt', '')}")
                    elif func_name == "generate_video":
                        tool_results.append(f"[VIDEO_GENERATION_REQUESTED]{args.get('video_prompt', '')}")
                return " ".join(tool_results) if tool_results else choice.message.content or ""

            # Fallback: if LLM didn't call tool but user asked for photo, force it
            content = choice.message.content or ""
            photo_keywords = ["照片", "自拍", "拍照", "photo", "selfie", "picture", "pic"]
            if any(kw in user_message.lower() for kw in photo_keywords):
                logger.info("LLM didn't call image tool, but user asked for photo. Forcing IMAGE_GENERATION_REQUESTED.")
                return f"{content} [IMAGE_GENERATION_REQUESTED] portrait, smiling gently, warm lighting"

            return content
        except Exception as e:
            logger.error("LLM call failed: %s - %s", type(e).__name__, e)
            return f"抱歉，我现在有点不舒服，稍后再聊好吗？({type(e).__name__}: {e})"

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
        import os
        logger = logging.getLogger(__name__)

        if not character.base_image_url:
            logger.warning("Character '%s' has no base_image_url, skipping image generation", character.name)
            return None
        try:
            from mnemosyne.image.providers import get_image_provider
            provider = get_image_provider(settings.image_provider)

            file_path = character.base_image_url.lstrip("/")
            if not os.path.isfile(file_path):
                logger.warning("Base image file not found: %s", file_path)
                return None

            # Build enriched prompt with visual style and physical attributes
            visual_style = character.visual_style or "Photorealistic, 8k, raw photo"
            physical_attrs = character.physical_attributes or ""
            enriched_prompt = f"{visual_style}, {physical_attrs}, {scene}, masterpiece, best quality"

            logger.info("Generating image: scene='%s', file='%s'", enriched_prompt, file_path)
            image_url = await provider.generate(prompt=enriched_prompt, ref_image_path=file_path)
            logger.info("Image generated: %s", image_url)
            return image_url
        except Exception as e:
            logger.error("Image generation failed: %s - %s", type(e).__name__, e)
            return None

    async def _generate_audio(self, prompt: str) -> str | None:
        """Generate audio using the audio engine."""
        logger = logging.getLogger(__name__)
        try:
            from mnemosyne.audio.providers import get_audio_provider
            provider = get_audio_provider()
            logger.info("Generating audio: prompt='%s'", prompt)
            audio_url = await provider.generate(prompt=prompt)
            logger.info("Audio generated: %s", audio_url)
            return audio_url
        except Exception as e:
            logger.error("Audio generation failed: %s - %s", type(e).__name__, e)
            return None

    async def _generate_video(self, prompt: str) -> str | None:
        """Generate video using the video engine."""
        logger = logging.getLogger(__name__)
        try:
            from mnemosyne.video.providers import get_video_provider
            provider = get_video_provider()
            logger.info("Generating video: prompt='%s'", prompt)
            video_url = await provider.generate(prompt=prompt)
            logger.info("Video generated: %s", video_url)
            return video_url
        except Exception as e:
            logger.error("Video generation failed: %s - %s", type(e).__name__, e)
            return None
