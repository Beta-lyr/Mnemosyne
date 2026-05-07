"""APScheduler-based proactive trigger engine."""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, func

from mnemosyne.agent.core import DialogEngine
from mnemosyne.config import settings
from mnemosyne.db.models import Character, Conversation, Memory, User
from mnemosyne.db.session import async_session, redis_client
from mnemosyne.emotion.state import EmotionManager
from mnemosyne.trigger.rules import DEFAULT_RULES, TriggerContext, TriggerRule, should_send_trigger

logger = logging.getLogger(__name__)

DAILY_COUNT_KEY = "mnemosyne:daily_count:{character_id}"


class TriggerScheduler:
    """Manages scheduled proactive messages."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.dialog_engine = DialogEngine()
        self.emotion_manager = EmotionManager()

    def start(self):
        """Start the scheduler and register all trigger rules."""
        for rule in DEFAULT_RULES:
            if not rule.enabled:
                continue
            if rule.cron_hour is not None:
                trigger = CronTrigger(
                    hour=rule.cron_hour,
                    minute=rule.cron_minute or 0,
                    day_of_week=",".join(str(d) for d in rule.cron_days) if rule.cron_days else None,
                )
                self.scheduler.add_job(
                    self._execute_rule,
                    trigger=trigger,
                    args=[rule],
                    id=f"trigger_{rule.name}",
                    replace_existing=True,
                )
            elif rule.interval_hours:
                trigger = IntervalTrigger(hours=rule.interval_hours)
                self.scheduler.add_job(
                    self._execute_rule,
                    trigger=trigger,
                    args=[rule],
                    id=f"trigger_{rule.name}",
                    replace_existing=True,
                )

        # Add daily reset job at midnight
        self.scheduler.add_job(
            self._reset_daily_counts,
            CronTrigger(hour=0, minute=0),
            id="daily_reset",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Trigger scheduler started with %d rules", len(DEFAULT_RULES))

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown(wait=False)
        logger.info("Trigger scheduler stopped")

    async def _execute_rule(self, rule: TriggerRule):
        """Execute a trigger rule for all characters."""
        try:
            async with async_session() as session:
                result = await session.execute(select(Character))
                characters = result.scalars().all()

                for char in characters:
                    ctx = await self._build_context(char)
                    if not should_send_trigger(ctx, rule):
                        continue

                    # Generate proactive message
                    message = await self._generate_proactive_message(char, rule, ctx)
                    if message:
                        await self._send_message(char, message)
                        await self._increment_daily_count(char.id)
                        logger.info(
                            "Sent '%s' to character %s", rule.name, char.name
                        )
        except Exception as e:
            logger.error("Error executing rule %s: %s", rule.name, e)

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

            # Daily message count
            count = await redis_client.get(DAILY_COUNT_KEY.format(character_id=char.id))
            daily_count = int(count) if count else 0

            # Current mood
            mood = await self.emotion_manager.get_emotion(char.id, char.mood_default)

            return TriggerContext(
                character_id=str(char.id),
                character_name=char.name,
                last_interaction_time=last_time,
                last_mood=mood,
                daily_messages_sent=daily_count,
                max_daily_messages=settings.max_daily_messages,
                quiet_hours_start=settings.quiet_hours_start,
                quiet_hours_end=settings.quiet_hours_end,
                cooldown_minutes=settings.cooldown_minutes,
            )

    async def _generate_proactive_message(
        self, char: Character, rule: TriggerRule, ctx: TriggerContext
    ) -> str | None:
        """Generate a proactive message using LLM."""
        import litellm

        context_parts = [f"你是{char.name}。"]
        context_parts.append(f"你的性格：{char.personality}")
        context_parts.append(f"你当前的心情：{ctx.last_mood}")

        if rule.name == "morning_greeting":
            context_parts.append("现在是早上，请发送一条温暖的早安消息。简短、自然、有温度。")
        elif rule.name == "night_greeting":
            context_parts.append("现在是晚上，请发送一条温馨的晚安消息。简短、关心对方。")
        elif rule.name == "event_followup":
            # Check for upcoming events
            async with async_session() as session:
                result = await session.execute(
                    select(Memory)
                    .where(Memory.character_id == char.id, Memory.type == "event")
                    .order_by(Memory.created_at.desc())
                    .limit(3)
                )
                events = result.scalars().all()
                if events:
                    event_texts = [e.content for e in events]
                    context_parts.append(f"用户最近提到的事件：{', '.join(event_texts)}")
                    context_parts.append("请根据这些事件发送一条关心的消息。")
                else:
                    return None
        elif rule.name == "mood_followup":
            if ctx.last_mood in ("sad", "anxious", "lonely"):
                context_parts.append("用户最近情绪不太好，请发送一条安慰的消息。温柔、不啰嗦。")
            else:
                return None
        elif rule.name == "random_care":
            async with async_session() as session:
                result = await session.execute(
                    select(Memory)
                    .where(Memory.character_id == char.id, Memory.type == "fact")
                    .order_by(func.random())
                    .limit(1)
                )
                fact = result.scalar_one_or_none()
                if fact:
                    context_parts.append(f"你记得用户的一个信息：{fact.content}")
                    context_parts.append("请基于这个信息发送一条轻松的关心消息。")
                else:
                    return None

        context_parts.append("只输出消息内容，不要有其他文字。保持在50字以内。")

        try:
            response = await litellm.acompletion(
                model=f"{settings.llm_provider}/{settings.llm_model}" if settings.llm_provider != "openai" else settings.llm_model,
                messages=[{"role": "user", "content": "\n".join(context_parts)}],
                api_key=settings.llm_api_key,
                api_base=settings.llm_base_url or None,
                max_tokens=100,
                temperature=0.9,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Failed to generate proactive message: %s", e)
            return None

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
                # TODO: need to know the chat_id to send to
                # This requires storing the user's telegram chat_id
                logger.info("Would send via Telegram: %s", message)
            except Exception as e:
                logger.error("Failed to send via Telegram: %s", e)

        # Store in Redis for Web UI pickup
        await redis_client.rpush(
            f"mnemosyne:proactive:{char.id}",
            message,
        )

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
