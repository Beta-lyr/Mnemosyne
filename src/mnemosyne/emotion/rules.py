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


def evaluate_emotion_shift(user_message: str) -> tuple[str, float] | None:
    """Evaluate if a user message should shift the character's emotion.

    Returns:
        (new_emotion, intensity) or None if no shift
    """
    # Check positive triggers
    for trigger in POSITIVE_TRIGGERS:
        if trigger.keyword in user_message:
            return (trigger.emotion_shift, trigger.intensity)

    # Check negative triggers
    for trigger in NEGATIVE_TRIGGERS:
        if trigger.keyword in user_message:
            return (trigger.emotion_shift, trigger.intensity)

    return None
