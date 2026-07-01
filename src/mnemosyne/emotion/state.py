"""Redis-based emotion state management for characters."""

import json
import random
import time

from mnemosyne.db.session import redis_client

EMOTION_KEY_PREFIX = "mnemosyne:emotion:"
SILENCE_COUNTER_PREFIX = "mnemosyne:silence_count:"
EMOTION_HISTORY_PREFIX = "mnemosyne:emotion_history:"

# Emotion decay: drift back to default over time
EMOTION_DECAY_SECONDS = 3600 * 4  # 4 hours
MAX_CONSECUTIVE_SILENCE = 3  # Max consecutive read-only receipts
MAX_HISTORY_LENGTH = 100  # Keep last 100 emotion changes

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

# Time thresholds for intensity accumulation
RAPID_MESSAGE_SECONDS = 30  # Messages within this window accumulate
RESET_INTENSITY_SECONDS = 300  # After 5 min, reset intensity


class EmotionManager:
    """Manages real-time emotion state for characters in Redis."""

    async def get_emotion(self, character_id: str, default: str = "sweet") -> dict | str:
        """Get current emotion state of a character.

        Returns dict with {emotion, intensity, timestamp} or default string.
        """
        raw = await redis_client.get(f"{EMOTION_KEY_PREFIX}{character_id}")
        if not raw:
            return default
        try:
            data = json.loads(raw)
            return data
        except (json.JSONDecodeError, TypeError):
            return raw if isinstance(raw, str) else default

    async def get_emotion_simple(self, character_id: str, default: str = "sweet") -> str:
        """Get just the emotion string (backward compatible)."""
        result = await self.get_emotion(character_id, default)
        if isinstance(result, dict):
            return result.get("emotion", default)
        return result or default

    async def set_emotion(self, character_id: str, emotion: str, intensity: float = 0.5):
        """Set character's emotion with intensity, stored as JSON."""
        data = {
            "emotion": emotion,
            "intensity": round(intensity, 2),
            "timestamp": time.time(),
        }
        await redis_client.set(
            f"{EMOTION_KEY_PREFIX}{character_id}",
            json.dumps(data),
            ex=EMOTION_DECAY_SECONDS,
        )
        # Log to history
        await self._log_emotion_history(character_id, emotion, intensity)

    async def accumulate_emotion(
        self, character_id: str, new_emotion: str, new_intensity: float, default: str = "sweet"
    ):
        """Accumulate emotion intensity for rapid messages.

        If messages arrive within RAPID_MESSAGE_SECONDS, intensity accumulates.
        If more than RESET_INTENSITY_SECONDS have passed, intensity resets.
        """
        current = await self.get_emotion(character_id, default)
        now = time.time()

        if isinstance(current, dict):
            current_emotion = current.get("emotion", default)
            current_intensity = current.get("intensity", 0.0)
            last_time = current.get("timestamp", 0)
        else:
            current_emotion = current
            current_intensity = 0.0
            last_time = 0

        time_diff = now - last_time

        if time_diff > RESET_INTENSITY_SECONDS:
            # Too much time passed, reset intensity
            final_intensity = new_intensity
        elif time_diff < RAPID_MESSAGE_SECONDS:
            # Rapid messages - accumulate
            final_intensity = min(1.0, current_intensity + new_intensity * 0.5)
        else:
            # Normal pace, use new intensity
            final_intensity = new_intensity

        await self.set_emotion(character_id, new_emotion, final_intensity)

    async def update_from_conversation(
        self, character_id: str, user_message: str, assistant_response: str,
        memories: list[dict] | None = None,
    ):
        """Update emotion based on conversation content and memories."""
        from mnemosyne.emotion.rules import evaluate_emotion_shift, evaluate_memory_emotion

        # Get current intensity for accumulation
        current = await self.get_emotion(character_id)
        current_intensity = current.get("intensity", 0.0) if isinstance(current, dict) else 0.0

        # Check message triggers with current intensity
        shift = evaluate_emotion_shift(user_message, current_intensity)
        if shift:
            new_emotion, intensity = shift
            await self.accumulate_emotion(character_id, new_emotion, intensity)
            return

        # Check memory triggers
        if memories:
            memories_text = "\n".join(m.get("content", "") for m in memories)
            memory_shift = evaluate_memory_emotion(memories_text)
            if memory_shift:
                new_emotion, intensity = memory_shift
                await self.accumulate_emotion(character_id, new_emotion, intensity)

    async def get_reply_delay(self, character_id: str, default_mood: str = "sweet") -> float:
        """Calculate reply delay based on current emotion."""
        mood = await self.get_emotion_simple(character_id, default_mood)
        delay_range = REPLY_DELAYS.get(mood, (1.0, 3.0))
        return random.uniform(*delay_range)

    async def should_silence(self, character_id: str, default_mood: str = "sweet") -> bool:
        """Determine if the character should read-but-not-reply (cold treatment).

        Returns True if the character should stay silent this turn.
        Enforces MAX_CONSECUTIVE_SILENCE to avoid frustrating the user.
        """
        mood = await self.get_emotion_simple(character_id, default_mood)
        if mood not in NEGATIVE_EMOTIONS:
            await redis_client.delete(f"{SILENCE_COUNTER_PREFIX}{character_id}")
            return False

        count_str = await redis_client.get(f"{SILENCE_COUNTER_PREFIX}{character_id}")
        consecutive = int(count_str) if count_str else 0
        if consecutive >= MAX_CONSECUTIVE_SILENCE:
            await redis_client.delete(f"{SILENCE_COUNTER_PREFIX}{character_id}")
            return False

        prob = SILENCE_PROBABILITIES.get(mood, 0.1)
        if random.random() < prob:
            await redis_client.set(
                f"{SILENCE_COUNTER_PREFIX}{character_id}",
                str(consecutive + 1),
                ex=3600,
            )
            return True

        await redis_client.delete(f"{SILENCE_COUNTER_PREFIX}{character_id}")
        return False

    async def get_emotion_history(self, character_id: str) -> list[dict]:
        """Get recent emotion history for a character."""
        raw_list = await redis_client.lrange(f"{EMOTION_HISTORY_PREFIX}{character_id}", 0, -1)
        history = []
        for raw in raw_list:
            try:
                history.append(json.loads(raw))
            except (json.JSONDecodeError, TypeError):
                continue
        return history

    async def _log_emotion_history(self, character_id: str, emotion: str, intensity: float):
        """Append emotion change to history list in Redis."""
        key = f"{EMOTION_HISTORY_PREFIX}{character_id}"
        entry = json.dumps({
            "emotion": emotion,
            "intensity": round(intensity, 2),
            "timestamp": time.time(),
        })
        await redis_client.rpush(key, entry)
        # Trim to max length
        await redis_client.ltrim(key, -MAX_HISTORY_LENGTH, -1)

    async def decay_emotion(self, character_id: str, default: str = "sweet"):
        """Decay emotion towards default. Called periodically."""
        current = await self.get_emotion(character_id, default)
        if isinstance(current, dict) and current.get("emotion") != default:
            # The Redis TTL handles natural decay
            pass
