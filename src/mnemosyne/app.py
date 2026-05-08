"""FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from mnemosyne.api import auth, characters, chat, memories, settings as settings_api
from mnemosyne.config import settings

logger = logging.getLogger(__name__)

# Global instances
bot_manager = None
trigger_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_manager, trigger_scheduler

    # Startup
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("uploads/characters", exist_ok=True)
    logging.basicConfig(level=logging.INFO)

    # Log storage backend
    from mnemosyne.storage import storage, S3Storage
    if isinstance(storage, S3Storage):
        logger.info("Storage backend: S3 (bucket=%s)", storage.bucket)
    else:
        logger.info("Storage backend: Local filesystem")

    # Initialize trigger scheduler
    try:
        from mnemosyne.trigger.scheduler import TriggerScheduler, set_scheduler
        trigger_scheduler = TriggerScheduler()
        set_scheduler(trigger_scheduler)
        trigger_scheduler.start()
        logger.info("Trigger scheduler started")
    except Exception as e:
        logger.warning("Failed to start trigger scheduler: %s", e)

    # Initialize Telegram bots
    try:
        from mnemosyne.channel.bot_manager import BotManager
        bot_manager = BotManager()
        await bot_manager.start_all()
        logger.info("Bot manager started")
    except Exception as e:
        logger.warning("Failed to start bot manager: %s", e)

    yield

    # Shutdown
    if trigger_scheduler:
        trigger_scheduler.stop()
    if bot_manager:
        await bot_manager.stop_all()


app = FastAPI(
    title="Mnemosyne",
    description="Memory-driven virtual companion agent framework",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/storage/{path:path}")
async def serve_storage(path: str):
    """Proxy endpoint for S3-stored files. Only active when using S3 backend."""
    from mnemosyne.storage import storage, S3Storage
    if not isinstance(storage, S3Storage):
        return Response(status_code=404, content="Not using S3 storage")
    data = await storage.read(path)
    if data is None:
        return Response(status_code=404, content="File not found")
    # Guess content type from extension
    ext = os.path.splitext(path)[1].lower()
    mime_map = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif",
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
        ".mp4": "video/mp4", ".webm": "video/webm",
    }
    content_type = mime_map.get(ext, "application/octet-stream")
    return Response(content=data, media_type=content_type)


# Register API routers
app.include_router(auth.router)
app.include_router(characters.router)
app.include_router(chat.router)
app.include_router(memories.router)
app.include_router(settings_api.router)

# Serve uploaded files
if os.path.isdir("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Serve frontend static files (production) - must be last
if os.path.isdir("web/dist"):
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join("web/dist", full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse("web/dist/index.html")
