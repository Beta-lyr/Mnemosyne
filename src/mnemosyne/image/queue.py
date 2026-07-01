"""Redis-based image generation queue to prevent concurrent overload."""

import json
import uuid

from mnemosyne.db.session import redis_client

QUEUE_KEY = "mnemosyne:image_queue"
STATUS_PREFIX = "mnemosyne:image_status:"


class ImageQueue:
    """Manages image generation requests via Redis queue."""

    async def enqueue(self, character_id: str, prompt: str, reference_image_url: str) -> str:
        """Add an image generation request to the queue. Returns request ID."""
        request_id = str(uuid.uuid4())
        request = {
            "id": request_id,
            "character_id": character_id,
            "prompt": prompt,
            "reference_image_url": reference_image_url,
        }
        await redis_client.rpush(QUEUE_KEY, json.dumps(request))
        await redis_client.set(f"{STATUS_PREFIX}{request_id}", "pending", ex=3600)
        return request_id

    async def dequeue(self) -> dict | None:
        """Get the next image generation request from the queue."""
        data = await redis_client.lpop(QUEUE_KEY)
        if data:
            request = json.loads(data)
            await redis_client.set(f"{STATUS_PREFIX}{request['id']}", "processing", ex=3600)
            return request
        return None

    async def set_result(self, request_id: str, image_url: str):
        """Mark a request as completed with the result URL."""
        await redis_client.set(
            f"{STATUS_PREFIX}{request_id}",
            json.dumps({"status": "done", "image_url": image_url}),
            ex=3600,
        )

    async def get_status(self, request_id: str) -> dict:
        """Get the status of an image generation request."""
        data = await redis_client.get(f"{STATUS_PREFIX}{request_id}")
        if not data:
            return {"status": "not_found"}
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {"status": data}
