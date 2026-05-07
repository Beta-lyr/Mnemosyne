"""System settings API routes."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mnemosyne.api.auth import get_current_user
from mnemosyne.config import settings
from mnemosyne.db.models import User

router = APIRouter(prefix="/api/settings", tags=["settings"])

ENV_FILE = Path(".env")


class SettingsResponse(BaseModel):
    llm_provider: str
    llm_api_key: str
    llm_model: str
    llm_base_url: str
    embedding_provider: str
    embedding_model: str
    image_provider: str
    image_api_key: str
    image_base_url: str
    image_model: str
    replicate_api_token: str
    fal_key: str
    telegram_bot_token_1: str
    telegram_bot_token_2: str
    max_daily_messages: int
    cooldown_minutes: int
    quiet_hours_start: int
    quiet_hours_end: int
    secret_key: str


class SettingsUpdate(BaseModel):
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    image_provider: str | None = None
    image_api_key: str | None = None
    image_base_url: str | None = None
    image_model: str | None = None
    replicate_api_token: str | None = None
    fal_key: str | None = None
    telegram_bot_token_1: str | None = None
    telegram_bot_token_2: str | None = None
    max_daily_messages: int | None = None
    cooldown_minutes: int | None = None
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None


@router.get("/", response_model=SettingsResponse)
async def get_settings(current_user: User = Depends(get_current_user)):
    return SettingsResponse(
        llm_provider=settings.llm_provider,
        llm_api_key=settings.llm_api_key,
        llm_model=settings.llm_model,
        llm_base_url=settings.llm_base_url,
        embedding_provider=settings.embedding_provider,
        embedding_model=settings.embedding_model,
        image_provider=settings.image_provider,
        image_api_key=settings.image_api_key,
        image_base_url=settings.image_base_url,
        image_model=settings.image_model,
        replicate_api_token=settings.replicate_api_token,
        fal_key=settings.fal_key,
        telegram_bot_token_1=os.getenv("TELEGRAM_BOT_TOKEN_1", ""),
        telegram_bot_token_2=os.getenv("TELEGRAM_BOT_TOKEN_2", ""),
        max_daily_messages=settings.max_daily_messages,
        cooldown_minutes=settings.cooldown_minutes,
        quiet_hours_start=settings.quiet_hours_start,
        quiet_hours_end=settings.quiet_hours_end,
        secret_key=settings.secret_key,
    )


@router.put("/")
async def update_settings(
    req: SettingsUpdate,
    current_user: User = Depends(get_current_user),
):
    updates = req.model_dump(exclude_unset=True)
    if not updates:
        return {"ok": True, "message": "No changes"}

    _update_env_file(updates)
    return {
        "ok": True,
        "message": "Settings saved. Restart the server for changes to take effect.",
        "restart_required": True,
        "updated_fields": list(updates.keys()),
    }


def _update_env_file(updates: dict[str, str | int]):
    """Update .env file preserving comments and formatting."""
    if not ENV_FILE.exists():
        raise HTTPException(status_code=500, detail=".env file not found")

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    key_map = {k.upper(): v for k, v in updates.items()}
    updated_keys: set[str] = set()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in key_map:
                new_lines.append(f"{key}={key_map[key]}")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Add keys that weren't in the file yet
    for key, value in key_map.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
