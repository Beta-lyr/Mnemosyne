"""Trigger rule definitions and evaluation logic."""

from dataclasses import dataclass, field
from datetime import datetime, time, timezone


@dataclass
class TriggerRule:
    name: str
    cron_hour: int | None = None
    cron_minute: int | None = None
    cron_days: list[int] | None = None  # 0=Mon, 6=Sun
    interval_hours: int | None = None
    logic: str = ""
    enabled: bool = True


DEFAULT_RULES = [
    TriggerRule(name="morning_greeting", cron_hour=8, cron_minute=30, logic="发送早安消息"),
    TriggerRule(name="night_greeting", cron_hour=22, cron_minute=30, logic="发送晚安消息"),
    TriggerRule(name="event_followup", cron_hour=9, cron_minute=0, logic="检查未来24h事件"),
    TriggerRule(name="mood_followup", interval_hours=4, logic="检查负面情绪跟进"),
    TriggerRule(
        name="random_care",
        cron_hour=14, cron_minute=0, cron_days=[2, 5],  # Wed, Sat
        logic="随机关怀",
    ),
]


@dataclass
class TriggerContext:
    """Context passed to the trigger engine for decision making."""
    character_id: str
    character_name: str
    last_interaction_time: datetime | None = None
    last_mood: str = "neutral"
    daily_messages_sent: int = 0
    max_daily_messages: int = 2
    quiet_hours_start: int = 0
    quiet_hours_end: int = 7
    cooldown_minutes: int = 10


def should_send_trigger(ctx: TriggerContext, rule: TriggerRule) -> bool:
    """Evaluate whether a trigger should fire based on context."""
    if not rule.enabled:
        return False

    now = datetime.now(timezone.utc)
    current_hour = now.hour
    current_minute = now.minute

    # Quiet hours check
    if ctx.quiet_hours_start <= current_hour < ctx.quiet_hours_end:
        return False

    # Daily message limit
    if ctx.daily_messages_sent >= ctx.max_daily_messages:
        return False

    # Cooldown check
    if ctx.last_interaction_time:
        elapsed = (now - ctx.last_interaction_time).total_seconds() / 60
        if elapsed < ctx.cooldown_minutes:
            return False

    return True
