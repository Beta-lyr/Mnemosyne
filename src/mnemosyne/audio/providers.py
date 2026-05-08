"""Unified audio generation provider abstraction.

Supports multiple backends via .env configuration:
  AUDIO_PROVIDER=elevenlabs|huggingface|openai-compatible
  AUDIO_API_KEY=sk-xxx
  AUDIO_BASE_URL=https://custom-api.example.com/v1  (optional)
  AUDIO_MODEL=model-name                            (optional)
"""

import logging
import os
import uuid
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads/audio"


class AudioProvider(ABC):
    """Base class for audio generation providers."""

    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate audio and return a local URL path like /uploads/audio/gen_xxx.mp3."""
        raise NotImplementedError

    def _save_output(self, audio_bytes: bytes, ext: str = "mp3") -> str:
        """Save audio bytes to uploads/audio dir and return URL path."""
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filename = f"audio_{uuid.uuid4().hex[:12]}.{ext}"
        save_path = os.path.join(UPLOAD_DIR, filename)
        with open(save_path, "wb") as f:
            f.write(audio_bytes)
        logger.info("Audio saved to %s", save_path)
        return f"/uploads/audio/{filename}"


# ---------------------------------------------------------------------------
# ElevenLabs (TTS)
# ---------------------------------------------------------------------------
class ElevenLabsProvider(AudioProvider):
    """ElevenLabs TTS API — POST /v1/text-to-speech/{voice_id}."""

    DEFAULT_MODEL = "eleven_multilingual_v2"
    DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    async def generate(self, prompt: str, **kwargs) -> str:
        model = self.model or self.DEFAULT_MODEL
        voice_id = kwargs.get("voice_id", self.DEFAULT_VOICE)
        base = self.base_url or "https://api.elevenlabs.io/v1"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{base}/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": prompt,
                    "model_id": model,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
            )
            resp.raise_for_status()
            return self._save_output(resp.content, "mp3")


# ---------------------------------------------------------------------------
# Hugging Face Inference API (audio/music generation)
# ---------------------------------------------------------------------------
class HuggingFaceAudioProvider(AudioProvider):
    """Hugging Face Inference API for audio generation."""

    DEFAULT_MODEL = "facebook/musicgen-small"

    async def generate(self, prompt: str, **kwargs) -> str:
        model = self.model or self.DEFAULT_MODEL
        base = self.base_url or "https://router.huggingface.co/hf-inference/models"

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{base}/{model}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"inputs": prompt},
            )
            resp.raise_for_status()
            # HF returns raw audio bytes
            content_type = resp.headers.get("content-type", "")
            if "audio" in content_type or len(resp.content) > 1000:
                ext = "mp3"
                if "wav" in content_type:
                    ext = "wav"
                elif "flac" in content_type:
                    ext = "flac"
                return self._save_output(resp.content, ext)
            raise RuntimeError(f"HuggingFace returned unexpected content type: {content_type}")


# ---------------------------------------------------------------------------
# OpenAI-compatible TTS
# ---------------------------------------------------------------------------
class OpenAICompatibleAudioProvider(AudioProvider):
    """OpenAI-compatible TTS API (e.g. Azure OpenAI, local TTS servers)."""

    DEFAULT_MODEL = "tts-1"

    async def generate(self, prompt: str, **kwargs) -> str:
        model = self.model or self.DEFAULT_MODEL
        base = self.base_url or "https://api.openai.com/v1"
        voice = kwargs.get("voice", "alloy")

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{base}/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": prompt,
                    "voice": voice,
                    "response_format": "mp3",
                },
            )
            resp.raise_for_status()
            return self._save_output(resp.content, "mp3")


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
PROVIDERS: dict[str, type[AudioProvider]] = {
    "elevenlabs": ElevenLabsProvider,
    "huggingface": HuggingFaceAudioProvider,
    "openai-compatible": OpenAICompatibleAudioProvider,
}


def get_audio_provider(
    provider_name: str = "",
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> AudioProvider:
    """Factory to get an audio provider by name."""
    from mnemosyne.config import settings

    provider_name = provider_name or settings.audio_provider
    api_key = api_key or settings.audio_api_key
    base_url = base_url or settings.audio_base_url
    model = model or settings.audio_model

    cls = PROVIDERS.get(provider_name)
    if not cls:
        raise ValueError(f"Unknown audio provider: {provider_name}. Available: {list(PROVIDERS.keys())}")

    return cls(api_key=api_key, base_url=base_url, model=model)
