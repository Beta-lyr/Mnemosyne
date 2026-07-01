"""Unified image generation provider abstraction.

Supports multiple backends via .env configuration:
  IMAGE_PROVIDER=replicate|fal|stability|huggingface|openai-compatible
  IMAGE_API_KEY=sk-xxx
  IMAGE_BASE_URL=https://custom-api.example.com/v1  (optional, for custom endpoints)
  IMAGE_MODEL=model-name                            (optional, provider default)

Similar to how LiteLLM abstracts LLM calls, this module provides a unified
interface for image generation across different platforms.
"""

import base64
import logging
import os
import uuid
from abc import ABC, abstractmethod

import httpx

from mnemosyne.storage import storage

logger = logging.getLogger(__name__)


class ImageProvider(ABC):
    """Base class for image generation providers."""

    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @abstractmethod
    async def generate(self, prompt: str, ref_image_path: str = "", character_id: str = "", **kwargs) -> str:
        """Generate an image and return a URL path."""
        raise NotImplementedError

    async def _save_output(self, image_bytes: bytes, character_id: str = "") -> str:
        """Save image bytes via storage layer and return URL path."""
        filename = f"gen_{uuid.uuid4().hex[:12]}.png"
        if character_id:
            key = f"characters/{character_id}/images/{filename}"
        else:
            key = f"images/{filename}"
        return await storage.save(image_bytes, key)

    @staticmethod
    async def _file_to_base64_uri(path: str) -> str:
        # Support both local paths and /uploads/ URLs (via storage layer)
        data = None
        if path.startswith("/uploads/"):
            key = path[len("/uploads/"):]
            data = await storage.read(key)
        elif path.startswith("/api/storage/"):
            key = path[len("/api/storage/"):]
            data = await storage.read(key)
        else:
            with open(path, "rb") as f:
                data = f.read()
        if data is None:
            raise FileNotFoundError(f"Reference image not found: {path}")
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
        return f"data:{mime};base64,{base64.b64encode(data).decode()}"


# ---------------------------------------------------------------------------
# Replicate (via REST API, no SDK dependency)
# ---------------------------------------------------------------------------
class ReplicateProvider(ImageProvider):
    """Replicate API — POST /v1/predictions, poll for result."""

    DEFAULT_MODEL = "tencentarc/photomaker"

    async def generate(self, prompt: str, ref_image_path: str = "", character_id: str = "", **kwargs) -> str:
        model = self.model or self.DEFAULT_MODEL
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        # Build input payload
        styled_prompt = f"a photo of a person img, {prompt}"
        input_data: dict = {
            "prompt": styled_prompt,
            "negative_prompt": "nsfw, lowres, bad anatomy, bad hands, text, error, blurry",
            "num_steps": 30,
            "guidance_scale": 5.0,
            "style_strength_ratio": 20,
        }
        if ref_image_path:
            input_data["input_image"] = await self._file_to_base64_uri(ref_image_path)

        # Create prediction
        base = self.base_url or "https://api.replicate.com/v1"
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{base}/predictions",
                headers=headers,
                json={"version": await self._get_latest_version(client, base, model, headers), "input": input_data},
            )
            resp.raise_for_status()
            prediction = resp.json()

            # Poll until complete
            while prediction["status"] not in ("succeeded", "failed"):
                import asyncio
                await asyncio.sleep(2)
                poll = await client.get(prediction["urls"]["get"], headers=headers)
                poll.raise_for_status()
                prediction = poll.json()

            if prediction["status"] == "failed":
                raise RuntimeError(f"Replicate prediction failed: {prediction.get('error')}")

            # Download output
            output = prediction["output"]
            image_url = output[0] if isinstance(output, list) else output
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            return await self._save_output(img_resp.content, character_id)

    async def _get_latest_version(self, client, base, model, headers) -> str:
        resp = await client.get(f"{base}/models/{model}/versions?limit=1", headers=headers)
        resp.raise_for_status()
        return resp.json()["results"][0]["id"]


# ---------------------------------------------------------------------------
# FAL.ai (via REST API)
# ---------------------------------------------------------------------------
class FALProvider(ImageProvider):
    """FAL.ai API — POST to model endpoint."""

    DEFAULT_MODEL = "fal-ai/flux-lora"

    async def generate(self, prompt: str, ref_image_path: str = "", character_id: str = "", **kwargs) -> str:
        model = self.model or self.DEFAULT_MODEL
        base = self.base_url or "https://fal.run"
        url = f"{base}/{model}"

        payload: dict = {"prompt": prompt, "num_inference_steps": 28, "guidance_scale": 3.5}
        if ref_image_path:
            payload["image_url"] = await self._file_to_base64_uri(ref_image_path)

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Key {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            image_url = data.get("images", [{}])[0].get("url", "")
            if not image_url:
                raise RuntimeError("FAL returned no image")
            img = await client.get(image_url)
            img.raise_for_status()
            return await self._save_output(img.content, character_id)


# ---------------------------------------------------------------------------
# Stability AI (REST API)
# ---------------------------------------------------------------------------
class StabilityProvider(ImageProvider):
    """Stability AI — SDXL / SD3 via REST API."""

    DEFAULT_MODEL = "stable-diffusion-xl-1024-v1-0"

    async def generate(self, prompt: str, ref_image_path: str = "", character_id: str = "", **kwargs) -> str:
        model = self.model or self.DEFAULT_MODEL
        base = self.base_url or "https://api.stability.ai/v2beta"

        async with httpx.AsyncClient(timeout=300) as client:
            if ref_image_path:
                # Image-to-image
                with open(ref_image_path, "rb") as f:
                    files = {"image": ("ref.png", f, "image/png")}
                    data = {"prompt": prompt, "output_format": "png"}
                    resp = await client.post(
                        f"{base}/stable-image/generate/sd3",
                        headers={"Authorization": f"Bearer {self.api_key}", "Accept": "image/*"},
                        data=data,
                        files=files,
                    )
            else:
                # Text-to-image
                data = {"prompt": prompt, "output_format": "png", "model": model}
                resp = await client.post(
                    f"{base}/stable-image/generate/sd3",
                    headers={"Authorization": f"Bearer {self.api_key}", "Accept": "image/*"},
                    data=data,
                )
            resp.raise_for_status()
            return await self._save_output(resp.content, character_id)


# ---------------------------------------------------------------------------
# Hugging Face Inference API (free tier available)
# ---------------------------------------------------------------------------
class HuggingFaceProvider(ImageProvider):
    """Hugging Face Inference API — free tier for popular models."""

    DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"

    async def generate(self, prompt: str, ref_image_path: str = "", character_id: str = "", **kwargs) -> str:
        model = self.model or self.DEFAULT_MODEL
        base = self.base_url or "https://router.huggingface.co/hf-inference/models"

        async with httpx.AsyncClient(timeout=300) as client:
            payload: dict = {"inputs": prompt}

            resp = await client.post(
                f"{base}/{model}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            return await self._save_output(resp.content, character_id)


# ---------------------------------------------------------------------------
# OpenAI-compatible (DALL-E style API)
# ---------------------------------------------------------------------------
class OpenAICompatibleProvider(ImageProvider):
    """Any OpenAI-compatible image generation API (DALL-E style)."""

    DEFAULT_MODEL = "dall-e-3"

    async def generate(self, prompt: str, ref_image_path: str = "", character_id: str = "", **kwargs) -> str:
        model = self.model or self.DEFAULT_MODEL
        base = self.base_url or "https://api.openai.com/v1"

        async with httpx.AsyncClient(timeout=300) as client:
            payload: dict = {"model": model, "prompt": prompt, "n": 1, "size": "1024x1024"}
            if ref_image_path:
                payload["image"] = await self._file_to_base64_uri(ref_image_path)

            resp = await client.post(
                f"{base}/images/generations",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            image_url = data["data"][0]["url"]
            img = await client.get(image_url)
            img.raise_for_status()
            return await self._save_output(img.content, character_id)


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
PROVIDERS: dict[str, type[ImageProvider]] = {
    "replicate": ReplicateProvider,
    "fal": FALProvider,
    "stability": StabilityProvider,
    "huggingface": HuggingFaceProvider,
    "openai-compatible": OpenAICompatibleProvider,
}


def get_image_provider(
    provider_name: str = "",
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> ImageProvider:
    """Factory to get an image provider by name.

    Falls back to settings if arguments are empty.
    """
    from mnemosyne.config import settings

    provider_name = provider_name or settings.image_provider
    api_key = api_key or settings.image_api_key or settings.replicate_api_token or settings.fal_key
    base_url = base_url or settings.image_base_url
    model = model or settings.image_model

    cls = PROVIDERS.get(provider_name)
    if not cls:
        raise ValueError(f"Unknown image provider: {provider_name}. Available: {list(PROVIDERS.keys())}")

    return cls(api_key=api_key, base_url=base_url, model=model)
