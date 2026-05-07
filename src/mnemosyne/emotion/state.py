"""Redis-based emotion state management for characters."""

from mnemosyne.db.session import redis_client

EMOTION_KEY_PREFIX = "mnemosyne:emotion:"

# Emotion decay: drift back to default over time
EMOTION_DECAY_SECONDS = 3600 * 4  # 4 hours


class EmotionManager:
    """Manages real-time emotion state for characters in Redis."""

    async def get_emotion(self, character_id: str, default: str = "sweet") -> str:
        """Get current emotion state of a character."""
        emotion = await redis_client.get(f"{EMOTION_KEY_PREFIX}{character_id}")
        return emotion or default

    async def set_emotion(self, character_id: str, emotion: str, intensity: float = 0.5):
        """Set character's emotion with intensity."""
        await redis_client.set(
            f"{EMOTION_KEY_PREFIX}{character_id}",
            emotion,
            ex=EMOTION_DECAY_SECONDS,
        )

    async def update_from_conversation(
        self, character_id: str, user_message: str, assistant_response: str
    ):
        """Update emotion based on conversation content."""
        from mnemosyne.emotion.rules import evaluate_emotion_shift

        shift = evaluate_emotion_shift(user_message)
        if shift:
            new_emotion, intensity = shift
            await self.set_emotion(character_id, new_emotion, intensity)

    async def decay_emotion(self, character_id: str, default: str = "sweet"):
        """Decay emotion towards default. Called periodically."""
        current = await self.get_emotion(character_id, default)
        if current != default:
            # The Redis TTL handles natural decay - if key expires, emotion resets to default
            pass
