"""Trigger rule definitions and evaluation logic.

Replaced static cron rules with an LLM-driven proactive care system.
The LLM decides when and what to send based on full context.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TriggerContext:
    """Context passed to the LLM for proactive care decisions."""
    character_id: str
    character_name: str
    character_personality: str = ""
    mood_default: str = "sweet"
    last_interaction_time: datetime | None = None
    last_mood: str = "neutral"
    daily_messages_sent: int = 0
    max_daily_messages: int = 2
    quiet_hours_start: int = 0
    quiet_hours_end: int = 7
    cooldown_minutes: int = 10
    memories: list[str] = field(default_factory=list)
    recent_summary: str = ""


def should_attempt_proactive(ctx: TriggerContext) -> bool:
    """Basic guard checks before calling the LLM for a decision."""
    now = datetime.now(timezone.utc)
    current_hour = now.hour

    # Quiet hours — don't even ask the LLM
    if ctx.quiet_hours_start <= current_hour < ctx.quiet_hours_end:
        return False

    # Daily message limit
    if ctx.daily_messages_sent >= ctx.max_daily_messages:
        return False

    # Cooldown — don't ask if we just talked
    if ctx.last_interaction_time:
        elapsed_min = (now - ctx.last_interaction_time).total_seconds() / 60
        if elapsed_min < ctx.cooldown_minutes:
            return False

    return True


def format_time_since(last_interaction: datetime | None) -> str:
    """Format how long ago the last interaction was."""
    if not last_interaction:
        return "从未对话过"

    now = datetime.now(timezone.utc)
    delta = now - last_interaction
    minutes = int(delta.total_seconds() / 60)

    if minutes < 60:
        return f"{minutes} 分钟前"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} 小时前"
    days = hours // 24
    return f"{days} 天前"
