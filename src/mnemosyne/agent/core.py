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
    ) -> tuple[str, dict]:
        """Process a user message and return (response_text, pending_media).

        pending_media is a dict with keys 'image', 'audio', 'video' whose values
        are the prompts to generate. Callers should run generate_media_background()
        as a background task for each non-None entry.
        """
        # 1. Get character
        result = await session.execute(select(Character).where(Character.id == character_id))
        character = result.scalar_one_or_none()
        if not character:
            return "Error: character not found", {}

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

        # 7. Parse tool call markers — extract prompts for async media generation
        pending_media: dict = {}

        if "[IMAGE_GENERATION_REQUESTED]" in response:
            scene = response.split("[IMAGE_GENERATION_REQUESTED]")[1].strip()
            response = response.split("[IMAGE_GENERATION_REQUESTED]")[0].strip()
            if not response:
                response = "给你看一张我的照片~"
            pending_media["image"] = scene

        if "[AUDIO_GENERATION_REQUESTED]" in response:
            audio_prompt = response.split("[AUDIO_GENERATION_REQUESTED]")[1].strip()
            response = response.split("[AUDIO_GENERATION_REQUESTED]")[0].strip()
            if not response:
                response = "给你听听~"
            pending_media["audio"] = audio_prompt

        if "[VIDEO_GENERATION_REQUESTED]" in response:
            video_prompt = response.split("[VIDEO_GENERATION_REQUESTED]")[1].strip()
            response = response.split("[VIDEO_GENERATION_REQUESTED]")[0].strip()
            if not response:
                response = "给你看个视频~"
            pending_media["video"] = video_prompt

        if "[MEMORY_SAVED]" in response:
            response = response.split("[MEMORY_SAVED]")[0].strip()

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

        # 8. Update emotion (with memories for memory-triggered emotions)
        memories_for_emotion = await self.memory_retriever.retrieve(character_id, user_message, top_k=3)
        await self.emotion_manager.update_from_conversation(character_id, user_message, response, memories_for_emotion)

        return response, pending_media

    async def stream_message(
        self,
        character_id: str,
        user_message: str,
        session: AsyncSession,
    ):
        """Stream LLM response token by token.

        Yields dicts:
          {"type": "chunk", "content": "..."}   — each text fragment
          {"type": "done", "text": "...", "pending_media": {...}}  — final
        """
        logger = logging.getLogger(__name__)

        # 1-4: Same setup as process_message
        result = await session.execute(select(Character).where(Character.id == character_id))
        character = result.scalar_one_or_none()
        if not character:
            yield {"type": "done", "text": "Error: character not found", "pending_media": {}}
            return

        memories_text = await self._get_memories_text(character_id, user_message)
        mood = await self.emotion_manager.get_emotion(character_id, character.mood_default)

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

        history = await self._get_conversation_history(session, character_id, limit=20)
        messages = [{"role": "system", "content": system_prompt}] + history
        messages.append({"role": "user", "content": user_message})

        # 5. Stream LLM call
        full_content = ""
        tool_calls_data = []
        try:
            response = await litellm.acompletion(
                model=f"{settings.llm_provider}/{settings.llm_model}",
                messages=messages,
                api_key=settings.llm_api_key,
                api_base=settings.llm_base_url or None,
                tools=[self._format_tool_schema(t) for t in TOOLS],
                max_tokens=1024,
                temperature=0.8,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue
                # Handle tool calls in stream
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        # Accumulate tool call data
                        while len(tool_calls_data) <= (tc.index or 0):
                            tool_calls_data.append({"name": "", "arguments": ""})
                        idx = tc.index or 0
                        if tc.function and tc.function.name:
                            tool_calls_data[idx]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls_data[idx]["arguments"] += tc.function.arguments
                # Handle text content
                if delta.content:
                    full_content += delta.content
                    yield {"type": "chunk", "content": delta.content}

        except Exception as e:
            logger.error("LLM stream failed: %s - %s", type(e).__name__, e)
            error_text = f"抱歉，我现在有点不舒服，稍后再聊好吗？({type(e).__name__}: {e})"
            yield {"type": "done", "text": error_text, "pending_media": {}}
            return

        # 6. Process tool calls (same as non-streaming)
        if tool_calls_data:
            tool_results = []
            for tc in tool_calls_data:
                func_name = tc["name"]
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                logger.info("Tool call (stream): %s(%s)", func_name, args)
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
            if tool_results:
                full_content = " ".join(tool_results)

        # 7. Fallback: force image if user asked for photo
        photo_keywords = ["照片", "自拍", "拍照", "photo", "selfie", "picture", "pic"]
        if not tool_calls_data and any(kw in user_message.lower() for kw in photo_keywords):
            if "[IMAGE_GENERATION_REQUESTED]" not in full_content:
                logger.info("LLM didn't call image tool in stream, forcing IMAGE_GENERATION_REQUESTED.")
                full_content += " [IMAGE_GENERATION_REQUESTED] portrait, smiling gently, warm lighting"

        # 8. Parse tool markers from content
        pending_media: dict = {}
        response_text = full_content

        if "[IMAGE_GENERATION_REQUESTED]" in response_text:
            scene = response_text.split("[IMAGE_GENERATION_REQUESTED]")[1].strip()
            response_text = response_text.split("[IMAGE_GENERATION_REQUESTED]")[0].strip()
            if not response_text:
                response_text = "给你看一张我的照片~"
            pending_media["image"] = scene

        if "[AUDIO_GENERATION_REQUESTED]" in response_text:
            audio_prompt = response_text.split("[AUDIO_GENERATION_REQUESTED]")[1].strip()
            response_text = response_text.split("[AUDIO_GENERATION_REQUESTED]")[0].strip()
            if not response_text:
                response_text = "给你听听~"
            pending_media["audio"] = audio_prompt

        if "[VIDEO_GENERATION_REQUESTED]" in response_text:
            video_prompt = response_text.split("[VIDEO_GENERATION_REQUESTED]")[1].strip()
            response_text = response_text.split("[VIDEO_GENERATION_REQUESTED]")[0].strip()
            if not response_text:
                response_text = "给你看个视频~"
            pending_media["video"] = video_prompt

        if "[MEMORY_SAVED]" in response_text:
            response_text = response_text.split("[MEMORY_SAVED]")[0].strip()

        if "[SCHEDULE_MESSAGE]" in response_text:
            schedule_str = response_text.split("[SCHEDULE_MESSAGE]")[1].strip()
            response_text = response_text.split("[SCHEDULE_MESSAGE]")[0].strip()
            try:
                info = json.loads(schedule_str)
                from mnemosyne.trigger.scheduler import get_scheduler
                scheduler = get_scheduler()
                if scheduler:
                    scheduler.add_dynamic_job(character_id, info["message"], info["delay"])
                    confirm = f"好的，我会在{info['delay']}分钟后提醒你~"
                    response_text = f"{response_text} {confirm}" if response_text else confirm
                else:
                    response_text = response_text or "抱歉，定时功能暂时不可用~"
            except Exception as e:
                logger.error("Failed to schedule message: %s", e)

        # 9. Update emotion (with memories)
        memories_for_emotion = await self.memory_retriever.retrieve(character_id, user_message, top_k=3)
        await self.emotion_manager.update_from_conversation(character_id, user_message, response_text, memories_for_emotion)

        yield {"type": "done", "text": response_text, "pending_media": pending_media}

    async def generate_media_background(
        self,
        character_id: str,
        message_id: str,
        pending_media: dict,
        on_complete: Any = None,
    ):
        """Generate media in background and update the conversation record.

        Args:
            character_id: The character's ID.
            message_id: The Conversation record ID to update.
            pending_media: Dict with 'image'/'audio'/'video' prompts.
            on_complete: Optional async callback(message_id, media_type, url).
        """
        from mnemosyne.db.session import async_session

        logger = logging.getLogger(__name__)
        async with async_session() as session:
            result = await session.execute(select(Character).where(Character.id == character_id))
            character = result.scalar_one_or_none()
            if not character:
                return

            cid = str(character.id)
            image_url = None
            audio_url = None
            video_url = None

            if "image" in pending_media:
                image_url = await self._generate_image(character, pending_media["image"], session, character_id=cid)
            if "audio" in pending_media:
                audio_url = await self._generate_audio(pending_media["audio"], character_id=cid)
            if "video" in pending_media:
                video_url = await self._generate_video(pending_media["video"], character_id=cid)

            # Update the conversation record
            result = await session.execute(select(Conversation).where(Conversation.id == message_id))
            msg = result.scalar_one_or_none()
            if msg:
                if image_url:
                    msg.image_url = image_url
                if audio_url:
                    msg.audio_url = audio_url
                if video_url:
                    msg.video_url = video_url
                msg.media_status = "ready"
                await session.commit()
                logger.info("Media generated for message %s: img=%s audio=%s video=%s",
                            message_id, image_url, audio_url, video_url)

            if on_complete:
                await on_complete(message_id, image_url, audio_url, video_url)

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
        self, character: Character, scene: str, session: AsyncSession, character_id: str = ""
    ) -> str | None:
        """Generate an image using the image engine."""
        logger = logging.getLogger(__name__)

        if not character.base_image_url:
            logger.warning("Character '%s' has no base_image_url, skipping image generation", character.name)
            return None
        try:
            from mnemosyne.image.providers import get_image_provider
            provider = get_image_provider(settings.image_provider)

            # Build enriched prompt with visual style and physical attributes
            visual_style = character.visual_style or "Photorealistic, 8k, raw photo"
            physical_attrs = character.physical_attributes or ""
            enriched_prompt = f"{visual_style}, {physical_attrs}, {scene}, masterpiece, best quality"

            # Pass base_image_url directly — provider's _file_to_base64_uri handles both local and S3
            logger.info("Generating image: scene='%s', ref='%s'", enriched_prompt, character.base_image_url)
            image_url = await provider.generate(prompt=enriched_prompt, ref_image_path=character.base_image_url, character_id=character_id)
            logger.info("Image generated: %s", image_url)
            return image_url
        except Exception as e:
            logger.error("Image generation failed: %s - %s", type(e).__name__, e)
            return None

    async def _generate_audio(self, prompt: str, character_id: str = "") -> str | None:
        """Generate audio using the audio engine."""
        logger = logging.getLogger(__name__)
        try:
            from mnemosyne.audio.providers import get_audio_provider
            provider = get_audio_provider()
            logger.info("Generating audio: prompt='%s'", prompt)
            audio_url = await provider.generate(prompt=prompt, character_id=character_id)
            logger.info("Audio generated: %s", audio_url)
            return audio_url
        except Exception as e:
            logger.error("Audio generation failed: %s - %s", type(e).__name__, e)
            return None

    async def _generate_video(self, prompt: str, character_id: str = "") -> str | None:
        """Generate video using the video engine."""
        logger = logging.getLogger(__name__)
        try:
            from mnemosyne.video.providers import get_video_provider
            provider = get_video_provider()
            logger.info("Generating video: prompt='%s'", prompt)
            video_url = await provider.generate(prompt=prompt, character_id=character_id)
            logger.info("Video generated: %s", video_url)
            return video_url
        except Exception as e:
            logger.error("Video generation failed: %s - %s", type(e).__name__, e)
            return None
