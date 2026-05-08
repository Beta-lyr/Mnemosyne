"""Unified video generation provider abstraction.

Supports multiple backends via .env configuration:
  VIDEO_PROVIDER=replicate|huggingface|luma
  VIDEO_API_KEY=sk-xxx
  VIDEO_BASE_URL=https://custom-api.example.com/v1  (optional)
  VIDEO_MODEL=model-name                            (optional)
"""

import asyncio
import logging
import os
import uuid
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads/video"


class VideoProvider(ABC):
    """Base class for video generation providers."""

    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a video and return a local URL path like /uploads/video/gen_xxx.mp4."""
        raise NotImplementedError

    def _save_output(self, video_bytes: bytes, ext: str = "mp4") -> str:
        """Save video bytes to uploads/video dir and return URL path."""
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filename = f"video_{uuid.uuid4().hex[:12]}.{ext}"
        save_path = os.path.join(UPLOAD_DIR, filename)
        with open(save_path, "wb") as f:
            f.write(video_bytes)
        logger.info("Video saved to %s", save_path)
        return f"/uploads/video/{filename}"


# ---------------------------------------------------------------------------
# Replicate (via REST API)
# ---------------------------------------------------------------------------
class ReplicateVideoProvider(VideoProvider):
    """Replicate API for video generation — POST /v1/predictions, poll for result."""

    DEFAULT_MODEL = "anotherjesse/zeroscope-v2-xl"

    async def generate(self, prompt: str, **kwargs) -> str:
        model = self.model or self.DEFAULT_MODEL
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        base = self.base_url or "https://api.replicate.com/v1"

        async with httpx.AsyncClient(timeout=600) as client:
            # Get latest version
            ver_resp = await client.get(f"{base}/models/{model}/versions?limit=1", headers=headers)
            ver_resp.raise_for_status()
            version = ver_resp.json()["results"][0]["id"]

            # Create prediction
            resp = await client.post(
                f"{base}/predictions",
                headers=headers,
                json={
                    "version": version,
                    "input": {"prompt": prompt},
                },
            )
            resp.raise_for_status()
            prediction = resp.json()

            # Poll until complete
            while prediction["status"] not in ("succeeded", "failed"):
                await asyncio.sleep(5)
                poll = await client.get(prediction["urls"]["get"], headers=headers)
                poll.raise_for_status()
                prediction = poll.json()

            if prediction["status"] == "failed":
                raise RuntimeError(f"Replicate video prediction failed: {prediction.get('error')}")

            # Download output
            output = prediction["output"]
            video_url = output if isinstance(output, str) else output[0]
            vid_resp = await client.get(video_url)
            vid_resp.raise_for_status()
            return self._save_output(vid_resp.content)


# ---------------------------------------------------------------------------
# Hugging Face Inference API
# ---------------------------------------------------------------------------
class HuggingFaceVideoProvider(VideoProvider):
    """Hugging Face Inference API for video generation."""

    DEFAULT_MODEL = "ali-vilab/text-to-video-ms-1.7b"

    async def generate(self, prompt: str, **kwargs) -> str:
        model = self.model or self.DEFAULT_MODEL
        base = self.base_url or "https://router.huggingface.co/hf-inference/models"

        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(
                f"{base}/{model}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"inputs": prompt},
            )
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "video" in content_type or "octet-stream" in content_type or len(resp.content) > 10000:
                return self._save_output(resp.content)
            raise RuntimeError(f"HuggingFace video returned unexpected content type: {content_type}")


# ---------------------------------------------------------------------------
# Luma AI (Dream Machine)
# ---------------------------------------------------------------------------
class LumaProvider(VideoProvider):
    """Luma AI Dream Machine API."""

    DEFAULT_MODEL = "dream-machine"

    async def generate(self, prompt: str, **kwargs) -> str:
        base = self.base_url or "https://api.lumalabs.ai/dream-machine/v1"

        async with httpx.AsyncClient(timeout=600) as client:
            # Create generation
            resp = await client.post(
                f"{base}/generations",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"prompt": prompt, "aspect_ratio": "16:9"},
            )
            resp.raise_for_status()
            generation = resp.json()
            gen_id = generation["id"]

            # Poll until complete
            while True:
                await asyncio.sleep(10)
                poll = await client.get(
                    f"{base}/generations/{gen_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                poll.raise_for_status()
                status = poll.json()
                if status["state"] == "completed":
                    video_url = status["assets"]["video"]
                    vid_resp = await client.get(video_url)
                    vid_resp.raise_for_status()
                    return self._save_output(vid_resp.content)
                elif status["state"] == "failed":
                    raise RuntimeError(f"Luma generation failed: {status.get('failure_reason')}")


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
PROVIDERS: dict[str, type[VideoProvider]] = {
    "replicate": ReplicateVideoProvider,
    "huggingface": HuggingFaceVideoProvider,
    "luma": LumaProvider,
}


def get_video_provider(
    provider_name: str = "",
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> VideoProvider:
    """Factory to get a video provider by name."""
    from mnemosyne.config import settings

    provider_name = provider_name or settings.video_provider
    api_key = api_key or settings.video_api_key
    base_url = base_url or settings.video_base_url
    model = model or settings.video_model

    cls = PROVIDERS.get(provider_name)
    if not cls:
        raise ValueError(f"Unknown video provider: {provider_name}. Available: {list(PROVIDERS.keys())}")

    return cls(api_key=api_key, base_url=base_url, model=model)
