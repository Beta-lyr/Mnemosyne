"""Redis-based emotion state management for characters."""

import random

from mnemosyne.db.session import redis_client

EMOTION_KEY_PREFIX = "mnemosyne:emotion:"
SILENCE_COUNTER_PREFIX = "mnemosyne:silence_count:"

# Emotion decay: drift back to default over time
EMOTION_DECAY_SECONDS = 3600 * 4  # 4 hours
MAX_CONSECUTIVE_SILENCE = 3  # Max consecutive read-only receipts

# Reply delay ranges per emotion (min_seconds, max_seconds)
REPLY_DELAYS: dict[str, tuple[float, float]] = {
    "sweet": (1.0, 3.0),
    "happy": (1.0, 3.0),
    "gentle": (1.5, 3.5),
    "energetic": (0.5, 2.0),
    "shy": (3.0, 6.0),
    "cool": (5.0, 10.0),
    "sad": (8.0, 20.0),
    "anxious": (6.0, 15.0),
    "lonely": (10.0, 25.0),
}

# Emotions that might trigger read-only (no reply)
NEGATIVE_EMOTIONS = {"sad", "anxious", "lonely"}
# Probability of read-only per negative emotion
SILENCE_PROBABILITIES: dict[str, float] = {
    "sad": 0.2,
    "anxious": 0.15,
    "lonely": 0.3,
}


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

    async def get_reply_delay(self, character_id: str, default_mood: str = "sweet") -> float:
        """Calculate reply delay based on current emotion."""
        mood = await self.get_emotion(character_id, default_mood)
        delay_range = REPLY_DELAYS.get(mood, (1.0, 3.0))
        return random.uniform(*delay_range)

    async def should_silence(self, character_id: str, default_mood: str = "sweet") -> bool:
        """Determine if the character should read-but-not-reply (cold treatment).

        Returns True if the character should stay silent this turn.
        Enforces MAX_CONSECUTIVE_SILENCE to avoid frustrating the user.
        """
        mood = await self.get_emotion(character_id, default_mood)
        if mood not in NEGATIVE_EMOTIONS:
            # Reset silence counter when mood is not negative
            await redis_client.delete(f"{SILENCE_COUNTER_PREFIX}{character_id}")
            return False

        # Check consecutive silence count
        count_str = await redis_client.get(f"{SILENCE_COUNTER_PREFIX}{character_id}")
        consecutive = int(count_str) if count_str else 0
        if consecutive >= MAX_CONSECUTIVE_SILENCE:
            # Force a reply after max consecutive silences
            await redis_client.delete(f"{SILENCE_COUNTER_PREFIX}{character_id}")
            return False

        # Roll the dice
        prob = SILENCE_PROBABILITIES.get(mood, 0.1)
        if random.random() < prob:
            # Increment silence counter
            await redis_client.set(
                f"{SILENCE_COUNTER_PREFIX}{character_id}",
                str(consecutive + 1),
                ex=3600,  # Expire after 1 hour
            )
            return True

        # Not silenced, reset counter
        await redis_client.delete(f"{SILENCE_COUNTER_PREFIX}{character_id}")
        return False

    async def decay_emotion(self, character_id: str, default: str = "sweet"):
        """Decay emotion towards default. Called periodically."""
        current = await self.get_emotion(character_id, default)
        if current != default:
            # The Redis TTL handles natural decay - if key expires, emotion resets to default
            pass
