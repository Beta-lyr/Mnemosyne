"""Emotion change rules based on user interactions."""

from dataclasses import dataclass


@dataclass
class EmotionTrigger:
    keyword: str
    emotion_shift: str
    intensity: float


POSITIVE_TRIGGERS = [
    EmotionTrigger(keyword="喜欢", emotion_shift="happy", intensity=0.3),
    EmotionTrigger(keyword="爱", emotion_shift="sweet", intensity=0.5),
    EmotionTrigger(keyword="开心", emotion_shift="happy", intensity=0.3),
    EmotionTrigger(keyword="漂亮", emotion_shift="shy", intensity=0.4),
    EmotionTrigger(keyword="想你", emotion_shift="sweet", intensity=0.4),
    EmotionTrigger(keyword="好看", emotion_shift="happy", intensity=0.3),
    EmotionTrigger(keyword="可爱", emotion_shift="shy", intensity=0.3),
    EmotionTrigger(keyword="谢谢", emotion_shift="happy", intensity=0.2),
    EmotionTrigger(keyword="辛苦", emotion_shift="sweet", intensity=0.3),
]

NEGATIVE_TRIGGERS = [
    EmotionTrigger(keyword="讨厌", emotion_shift="sad", intensity=0.3),
    EmotionTrigger(keyword="烦", emotion_shift="anxious", intensity=0.2),
    EmotionTrigger(keyword="走开", emotion_shift="lonely", intensity=0.4),
    EmotionTrigger(keyword="无聊", emotion_shift="lonely", intensity=0.2),
    EmotionTrigger(keyword="生气", emotion_shift="anxious", intensity=0.3),
    EmotionTrigger(keyword="不想聊", emotion_shift="sad", intensity=0.3),
]

# Memory-triggered emotions: stronger intensity, sensitive topics
MEMORY_EMOTION_TRIGGERS = [
    EmotionTrigger(keyword="分手", emotion_shift="sad", intensity=0.8),
    EmotionTrigger(keyword="离婚", emotion_shift="sad", intensity=0.7),
    EmotionTrigger(keyword="去世", emotion_shift="sad", intensity=0.9),
    EmotionTrigger(keyword="考试", emotion_shift="anxious", intensity=0.5),
    EmotionTrigger(keyword="面试", emotion_shift="anxious", intensity=0.5),
    EmotionTrigger(keyword="生病", emotion_shift="anxious", intensity=0.6),
    EmotionTrigger(keyword="生日", emotion_shift="happy", intensity=0.6),
    EmotionTrigger(keyword="结婚", emotion_shift="happy", intensity=0.7),
    EmotionTrigger(keyword="升职", emotion_shift="happy", intensity=0.6),
    EmotionTrigger(keyword="旅行", emotion_shift="energetic", intensity=0.5),
    EmotionTrigger(keyword="吵架", emotion_shift="anxious", intensity=0.6),
    EmotionTrigger(keyword="失业", emotion_shift="sad", intensity=0.7),
    EmotionTrigger(keyword="搬家", emotion_shift="anxious", intensity=0.4),
    EmotionTrigger(keyword="表白", emotion_shift="sweet", intensity=0.6),
    EmotionTrigger(keyword="失恋", emotion_shift="lonely", intensity=0.8),
]


def evaluate_emotion_shift(user_message: str, current_intensity: float = 0.0) -> tuple[str, float] | None:
    """Evaluate if a user message should shift the character's emotion.

    Args:
        user_message: The user's message text.
        current_intensity: Current emotion intensity for accumulation.

    Returns:
        (new_emotion, intensity) or None if no shift
    """
    # Check positive triggers
    for trigger in POSITIVE_TRIGGERS:
        if trigger.keyword in user_message:
            # Accumulate intensity if rapid messages
            new_intensity = min(1.0, current_intensity + trigger.intensity * 0.5) if current_intensity > 0 else trigger.intensity
            return (trigger.emotion_shift, new_intensity)

    # Check negative triggers
    for trigger in NEGATIVE_TRIGGERS:
        if trigger.keyword in user_message:
            new_intensity = min(1.0, current_intensity + trigger.intensity * 0.5) if current_intensity > 0 else trigger.intensity
            return (trigger.emotion_shift, new_intensity)

    return None


def evaluate_memory_emotion(memories_text: str) -> tuple[str, float] | None:
    """Evaluate if retrieved memories should trigger an emotional response.

    Args:
        memories_text: Combined text of retrieved memories.

    Returns:
        (emotion, intensity) or None
    """
    if not memories_text:
        return None

    for trigger in MEMORY_EMOTION_TRIGGERS:
        if trigger.keyword in memories_text:
            return (trigger.emotion_shift, trigger.intensity)

    return None
