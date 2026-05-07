"""Image generation API providers (Replicate / FAL)."""

from abc import ABC, abstractmethod

import httpx


class ImageProvider(ABC):
    """Base class for image generation providers."""

    @abstractmethod
    async def generate(self, prompt: str, reference_image_url: str, **kwargs) -> str:
        """Generate an image and return the URL."""
        raise NotImplementedError


class ReplicateProvider(ImageProvider):
    """Replicate API provider for InstantID + SDXL."""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.replicate.com/v1"

    async def generate(self, prompt: str, reference_image_url: str, **kwargs) -> str:
        import replicate

        output = await replicate.async_run(
            "zsxkib/instant-id:main",
            input={
                "image": reference_image_url,
                "prompt": prompt,
                "negative_prompt": "blurry, low quality, distorted, deformed, ugly, bad anatomy",
                "ip_adapter_scale": 0.8,
                "controlnet_conditioning_scale": 0.8,
                "num_inference_steps": 30,
                "guidance_scale": 5.0,
            },
        )
        # replicate.async_run returns the output directly
        if isinstance(output, list):
            return output[0] if output else ""
        return str(output)


class FALProvider(ImageProvider):
    """FAL.ai API provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(self, prompt: str, reference_image_url: str, **kwargs) -> str:
        import fal_client

        result = await fal_client.run_async(
            "fal-ai/flux-lora",
            arguments={
                "prompt": prompt,
                "image_url": reference_image_url,
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
            },
        )
        return result.get("images", [{}])[0].get("url", "")


def get_image_provider(provider_name: str) -> ImageProvider:
    """Factory function to get the configured image provider."""
    from mnemosyne.config import settings

    if provider_name == "replicate":
        if not settings.replicate_api_token:
            raise ValueError("REPLICATE_API_TOKEN not configured")
        return ReplicateProvider(api_token=settings.replicate_api_token)
    elif provider_name == "fal":
        if not settings.fal_key:
            raise ValueError("FAL_KEY not configured")
        return FALProvider(api_key=settings.fal_key)
    else:
        raise ValueError(f"Unknown image provider: {provider_name}")
