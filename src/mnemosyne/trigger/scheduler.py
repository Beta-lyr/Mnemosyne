"""APScheduler-based proactive trigger engine.

Uses LLM-driven decisions instead of fixed cron rules.
The scheduler periodically checks if the character should reach out,
and the LLM decides when/what to send based on full context.
"""

import logging
import random
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, func

from mnemosyne.agent.core import DialogEngine
from mnemosyne.config import settings
from mnemosyne.db.models import Character, Conversation, Memory, User
from mnemosyne.db.session import async_session, redis_client
from mnemosyne.emotion.state import EmotionManager
from mnemosyne.trigger.rules import TriggerContext, format_time_since, should_attempt_proactive

logger = logging.getLogger(__name__)

DAILY_COUNT_KEY = "mnemosyne:daily_count:{character_id}"

# Base interval between proactive checks (minutes)
CHECK_INTERVAL_MINUTES = 45


class TriggerScheduler:
    """Manages proactive messages via LLM-driven decisions."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.dialog_engine = DialogEngine()
        self.emotion_manager = EmotionManager()

    def start(self):
        """Start the scheduler with a single periodic proactive check."""
        # Main proactive check — every 45 minutes with jitter
        # The jitter prevents all characters from being checked at the same instant
        self.scheduler.add_job(
            self._proactive_check_loop,
            IntervalTrigger(minutes=CHECK_INTERVAL_MINUTES, jitter=600),
            id="proactive_check",
            replace_existing=True,
        )

        # Daily reset at midnight
        self.scheduler.add_job(
            self._reset_daily_counts,
            CronTrigger(hour=0, minute=0),
            id="daily_reset",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Proactive scheduler started (check interval: %d min)", CHECK_INTERVAL_MINUTES)

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown(wait=False)
        logger.info("Proactive scheduler stopped")

    def add_dynamic_job(self, character_id: str, message: str, delay_minutes: int):
        """Schedule a one-time dynamic message after a delay (from LLM schedule_message tool)."""
        import uuid
        run_date = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        job_id = f"dynamic_{character_id}_{uuid.uuid4().hex[:8]}"
        self.scheduler.add_job(
            self._send_dynamic_message,
            trigger=DateTrigger(run_date=run_date),
            args=[character_id, message],
            id=job_id,
            replace_existing=False,
        )
        logger.info("Scheduled dynamic message for character %s in %d min (job=%s)",
                     character_id, delay_minutes, job_id)

    # ------------------------------------------------------------------
    # Core proactive check loop
    # ------------------------------------------------------------------

    async def _proactive_check_loop(self):
        """Periodic check: for each character, ask LLM if we should reach out."""
        try:
            async with async_session() as session:
                result = await session.execute(select(Character))
                characters = result.scalars().all()

            for char in characters:
                try:
                    await self._check_character(char)
                except Exception as e:
                    logger.error("Proactive check failed for %s: %s", char.name, e)
        except Exception as e:
            logger.error("Proactive check loop error: %s", e)

    async def _check_character(self, char: Character):
        """Run a proactive care decision for a single character."""
        ctx = await self._build_context(char)

        # Guard checks (quiet hours, cooldown, daily limit)
        if not should_attempt_proactive(ctx):
            return

        # Ask LLM to decide
        message = await self._llm_decide(char, ctx)
        if not message:
            return

        # Send the message
        await self._send_message(char, message)
        await self._increment_daily_count(char.id)
        logger.info("Proactive message sent for %s: %s", char.name, message[:60])

    async def _llm_decide(self, char: Character, ctx: TriggerContext) -> str | None:
        """Ask the LLM whether to send a proactive message and what to say."""
        import litellm
        from mnemosyne.agent.prompts import PROACTIVE_DECISION_PROMPT

        memories_text = "\n".join(f"- {m}" for m in ctx.memories[:10]) if ctx.memories else "暂无记忆"

        prompt = PROACTIVE_DECISION_PROMPT.format(
            name=char.name,
            user_name="用户",
            personality=char.personality[:500],
            mood=ctx.last_mood,
            memories=memories_text,
            current_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            time_since_last=format_time_since(ctx.last_interaction_time),
            daily_count=ctx.daily_messages_sent,
            recent_summary=ctx.recent_summary or "暂无",
        )

        try:
            response = await litellm.acompletion(
                model=f"{settings.llm_provider}/{settings.llm_model}",
                messages=[{"role": "user", "content": prompt}],
                api_key=settings.llm_api_key,
                api_base=settings.llm_base_url or None,
                max_tokens=200,
                temperature=0.85,
            )
            content = response.choices[0].message.content.strip()

            # Empty response or just whitespace = LLM decided not to send
            if not content or content.isspace():
                return None

            return content
        except Exception as e:
            logger.error("LLM proactive decision failed for %s: %s", char.name, e)
            return None

    # ------------------------------------------------------------------
    # Context building
    # ------------------------------------------------------------------

    async def _build_context(self, char: Character) -> TriggerContext:
        """Build trigger context for a character."""
        async with async_session() as session:
            # Last interaction time
            result = await session.execute(
                select(Conversation)
                .where(Conversation.character_id == char.id)
                .order_by(Conversation.created_at.desc())
                .limit(1)
            )
            last_msg = result.scalar_one_or_none()
            last_time = last_msg.created_at if last_msg else None

            # Recent conversation summary (last 5 messages)
            result = await session.execute(
                select(Conversation)
                .where(Conversation.character_id == char.id)
                .order_by(Conversation.created_at.desc())
                .limit(5)
            )
            recent_msgs = list(result.scalars().all())
            recent_summary = ""
            if recent_msgs:
                recent_msgs.reverse()
                lines = []
                for m in recent_msgs:
                    role = "用户" if m.role == "user" else char.name
                    lines.append(f"{role}: {m.content[:80]}")
                recent_summary = "\n".join(lines)

            # Memories
            result = await session.execute(
                select(Memory)
                .where(Memory.character_id == char.id)
                .order_by(Memory.importance.desc())
                .limit(10)
            )
            memories = [m.content for m in result.scalars().all()]

        # Daily message count
        count = await redis_client.get(DAILY_COUNT_KEY.format(character_id=char.id))
        daily_count = int(count) if count else 0

        # Current mood
        mood = await self.emotion_manager.get_emotion(char.id, char.mood_default)

        return TriggerContext(
            character_id=str(char.id),
            character_name=char.name,
            character_personality=char.personality,
            mood_default=char.mood_default,
            last_interaction_time=last_time,
            last_mood=mood,
            daily_messages_sent=daily_count,
            max_daily_messages=settings.max_daily_messages,
            quiet_hours_start=settings.quiet_hours_start,
            quiet_hours_end=settings.quiet_hours_end,
            cooldown_minutes=settings.cooldown_minutes,
            memories=memories,
            recent_summary=recent_summary,
        )

    # ------------------------------------------------------------------
    # Message delivery
    # ------------------------------------------------------------------

    async def _send_message(self, char: Character, message: str):
        """Send a proactive message through the appropriate channel."""
        # Save to conversation history
        async with async_session() as session:
            msg = Conversation(
                character_id=char.id,
                role="assistant",
                content=message,
            )
            session.add(msg)
            await session.commit()

        # If Telegram token is set, send via Telegram
        if char.telegram_token:
            try:
                from mnemosyne.channel.telegram import TelegramChannel
                channel = TelegramChannel(token=char.telegram_token, character_id=str(char.id))
                logger.info("Would send via Telegram: %s", message[:50])
            except Exception as e:
                logger.error("Failed to send via Telegram: %s", e)

        # Store in Redis for Web UI pickup
        await redis_client.rpush(
            f"mnemosyne:proactive:{char.id}",
            message,
        )

    async def _send_dynamic_message(self, character_id: str, message: str):
        """Send a dynamically scheduled message (from LLM schedule_message tool)."""
        try:
            async with async_session() as session:
                result = await session.execute(select(Character).where(Character.id == character_id))
                char = result.scalar_one_or_none()
                if not char:
                    logger.warning("Character %s not found for dynamic message", character_id)
                    return

                msg = Conversation(
                    character_id=char.id,
                    role="assistant",
                    content=message,
                )
                session.add(msg)
                await session.commit()

            await redis_client.rpush(
                f"mnemosyne:proactive:{char.id}",
                message,
            )
            logger.info("Sent dynamic message to character %s: %s", char.name, message[:50])
        except Exception as e:
            logger.error("Failed to send dynamic message: %s", e)

    # ------------------------------------------------------------------
    # Daily counter management
    # ------------------------------------------------------------------

    async def _increment_daily_count(self, character_id: str):
        key = DAILY_COUNT_KEY.format(character_id=character_id)
        await redis_client.incr(key)
        await redis_client.expireat(key, _end_of_day())

    async def _reset_daily_counts(self):
        """Reset all daily message counters at midnight."""
        async for key in redis_client.scan_iter("mnemosyne:daily_count:*"):
            await redis_client.delete(key)
        logger.info("Daily message counts reset")


def _end_of_day() -> int:
    """Get Unix timestamp for end of today."""
    now = datetime.now(timezone.utc)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    return int(end.timestamp())


# Module-level singleton for dynamic scheduling from dialog engine
_scheduler_instance: TriggerScheduler | None = None


def set_scheduler(instance: TriggerScheduler):
    global _scheduler_instance
    _scheduler_instance = instance


def get_scheduler() -> TriggerScheduler | None:
    return _scheduler_instance
